#!/usr/bin/env python3

import os
import re
import time
import string
import random
import subprocess
from .cmd import Cmd
from lib.logger import Logger


class ModemController:
    """Class for controlling modem hardware state and communications."""

    # Define possible TTY devices for the modem
    MODEM_TTY_DEVICES = ["/dev/ttyUSB0", "/dev/ttyUSB3"]

    # Known TACs for IMEI prefixes
    KNOWN_TACS = [
        35675904, 49013920, 49502220, 35250500, 49012241, 35060680,
        44919451, 35863907, 44814551, 35649604, 35538025, 35480910
    ]

    def __init__(self, tty_device=None, verbose=False):
        """
        Initialize the modem controller.

        Args:
            tty_device (str): TTY device path to use (defaults to first available from MODEM_TTY_DEVICES)
            verbose (bool): Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = Logger()

        # Determine SIM type to help select correct TTY device if none specified
        if tty_device:
            self.tty_device = tty_device
        else:
            sim_type = self.detect_sim_type_simple()
            # Use USB0 if virtual, else USB3
            virtual = sim_type == "virtual"
            default_tty = '/dev/ttyUSB0' if virtual else '/dev/ttyUSB3'
            self.tty_device = self._find_available_tty(default_tty)

        self.logger.info(f"Using TTY device: {self.tty_device}")

        # Check the device
        if not os.path.exists(self.tty_device):
            self.logger.warning(
                f"Warning: {self.tty_device} not found. It may appear later.")

        self.cmd = Cmd(self.tty_device, verbose)

    def _find_available_tty(self, preferred_tty=None):
        """Find the first available TTY device from the list."""
        # If preferred TTY is specified and exists, use it
        if preferred_tty and os.path.exists(preferred_tty):
            return preferred_tty

        # Otherwise find first available
        for device in self.MODEM_TTY_DEVICES:
            if os.path.exists(device):
                return device

        # Default to the preferred or first one if none found
        if preferred_tty:
            return preferred_tty
        return self.MODEM_TTY_DEVICES[0]

    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            self.logger.debug(f"[ModemController] {message}")

    def run_at_command(self, command):
        """
        Run the given AT command via the Cmd class.

        Args:
            command (str): The AT command to run

        Returns:
            tuple: (output_string, exit_code) where exit_code is 0 for success
        """
        return self.cmd.run_at_command(command)

    def enable_radio(self):
        """
        Enable the modem radio (AT+CFUN=1).

        Returns:
            bool: True on success, False on failure
        """
        self.logger.info("Enabling modem radio...")
        _, code = self.run_at_command("AT+CFUN=1")
        time.sleep(2)

        if code != 0:
            self.logger.warning("Failed to enable radio.")
            return False

        self.logger.info("Radio enabled.")
        return True

    def disable_radio(self):
        """
        Disable the modem radio (AT+CFUN=4).

        Returns:
            bool: True on success, False on failure
        """
        self.logger.info("Disabling modem radio...")
        _, code = self.run_at_command("AT+CFUN=4")
        time.sleep(2)

        if code != 0:
            self.logger.warning("Failed to disable radio.")
            return False

        self.logger.info("Radio disabled.")
        return True

    def wait_for_device_state(self, should_exist, timeout=60, poll_interval=1):
        """
        Wait until device presence matches the desired state or timeout occurs.

        Args:
            should_exist (bool): True to wait for device to appear, False to wait for it to disappear
            timeout (int): Maximum seconds to wait
            poll_interval (int): Seconds between checks

        Returns:
            bool: True if desired state was reached, False if timed out
        """
        start = time.time()
        state_desc = "present" if should_exist else "gone"

        self.log(
            f"Waiting for device to be {state_desc} (timeout: {timeout}s)...")

        while time.time() - start < timeout:
            device_exists = os.path.exists(self.tty_device)

            if device_exists == should_exist:
                self.log(f"{self.tty_device} is {state_desc}.")
                return True

            time.sleep(poll_interval)

        self.log(
            f"{self.tty_device} still {'not ' if should_exist else ''}present after {timeout}s.")
        return False

    def wait_for_device_gone(self, timeout=30):
        """
        Wait until self.tty_device disappears from /dev, or until timeout.

        Args:
            timeout (int): Maximum seconds to wait

        Returns:
            bool: True if device vanished, False if still present after timeout
        """
        return self.wait_for_device_state(should_exist=False, timeout=timeout, poll_interval=1)

    def wait_for_device_present(self, timeout=60):
        """
        Wait until self.tty_device appears in /dev, or until timeout.

        Args:
            timeout (int): Maximum seconds to wait

        Returns:
            bool: True if device appeared, False if still absent after timeout
        """
        return self.wait_for_device_state(should_exist=True, timeout=timeout, poll_interval=2)

    def restart_modem(self):
        """
        Restart the modem with AT+QPOWD, wait for device to disappear and reappear.

        Returns:
            bool: True if restart was successful, False otherwise
        """
        self.logger.info("Restarting modem (AT+QPOWD)...")
        _, code = self.run_at_command("AT+QPOWD")

        if code != 0:
            self.logger.warning("Failed to run AT+QPOWD (nonzero exit code).")
            # We can continue anyway, but the modem might not power off properly.

        # Wait for device to disappear
        self.logger.info("Waiting for device to disappear after QPOWD...")
        if not self.wait_for_device_gone(timeout=30):
            self.logger.warning(
                "Modem device did not vanish. Trying to continue anyway...")

        # Wait for device to reappear
        self.logger.info("Waiting for device to reappear...")
        if not self.wait_for_device_present(timeout=60):
            self.logger.error(
                "Modem device did not reappear in time. Restart failed.")
            return False

        # Verify modem functionality by checking IMSI
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            self.logger.info(
                f"Checking modem status (attempt {attempt}/{max_attempts})...")
            imsi = self.get_imsi()

            if imsi:
                self.logger.info(
                    f"Modem is back and responded with IMSI: {imsi}")
                return True

            time.sleep(3)

        self.logger.error("Modem restart timed out or no IMSI read.")
        return False

    def generate_luhn_checksum(self, digits):
        """
        Generate Luhn algorithm checksum for IMEI validation.

        Args:
            digits (str): String of digits to calculate checksum for

        Returns:
            int: Check digit (0-9)
        """
        checksum = 0
        for i, d in enumerate(reversed(str(digits))):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            checksum += n
        return (10 - (checksum % 10)) % 10

    def generate_random_imei(self, deterministic=False):
        """
        Generate a valid 15-digit IMEI.

        Args:
            deterministic (bool): If True, use IMSI as seed for RNG

        Returns:
            str: A valid 15-digit IMEI number
        """
        # Seed the RNG if deterministic
        if deterministic:
            imsi = self.get_imsi()
            if imsi:
                random.seed(imsi)
                self.log(
                    f"Using IMSI {imsi} as RNG seed for deterministic IMEI.")
            else:
                self.log("IMSI unavailable; falling back to random seed.")

        # Pick random TAC (Type Allocation Code)
        tac = str(random.choice(self.KNOWN_TACS))
        self.log(f"Selected TAC: {tac}")

        # Fill up to 14 digits
        remain_len = 14 - len(tac)
        random_part = ''.join(random.choice(string.digits)
                              for _ in range(remain_len))

        imei_base = tac + random_part
        self.log(f"Base IMEI (no check digit): {imei_base}")

        # Add Luhn check digit
        check_digit = self.generate_luhn_checksum(imei_base)
        imei = imei_base + str(check_digit)
        self.logger.info(f"Generated final IMEI: {imei}")

        return imei

    def detect_sim_type_simple(self):
        """
        Simple detection of SIM type (virtual or physical).

        Returns:
            str: "virtual" if virtual SIM detected, otherwise "physical"
        """
        # Check for vSIM indicators
        if os.path.exists("/tmp/vsim") or os.path.exists("/etc/vsim"):
            return "virtual"

        return "physical"

    def get_imsi(self):
        """
        Get the SIM IMSI.

        Returns:
            str: IMSI or None if not available
        """
        output, _ = self.run_at_command("AT+CIMI")
        if not output:
            return None

        # Look for a IMSI (usually 15 digits) in the output
        match = re.search(r'\b([0-9]{6,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_imei(self):
        """
        Get the device IMEI.

        Returns:
            str: IMEI or None if not available
        """
        output, _ = self.run_at_command("AT+GSN")
        if not output:
            return None

        # Look for a 15-digit IMEI in the output
        match = re.search(r'\b([0-9]{14,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_iccid(self):
        """
        Get the SIM ICCID.

        Returns:
            str: ICCID or None if not available
        """
        output, _ = self.run_at_command("AT+CCID")
        if not output:
            return None

        # Look for a ICCID in the output
        match = re.search(r'\b([0-9]{18,22})\b', output)
        if match:
            return match.group(1)
        return None

    def set_imei(self, imei, reboot_after=False):
        """
        Use AT+EGMR=1,7,"IMEI" to set IMEI. Requires radio disabled first.

        Args:
            imei (str): The new IMEI to set
            reboot_after (bool): Whether to reboot the device after setting IMEI

        Returns:
            bool: True if successful, False otherwise
        """
        if not re.match(r'^\d{15}$', imei):
            self.logger.error(f"Invalid IMEI format: {imei}")
            return False

        # Ensure radio is disabled before changing IMEI
        if not self.disable_radio():
            self.logger.warning(
                "Radio could not be disabled before setting IMEI")
            # Continue anyway as a best effort

        cmd = f'AT+EGMR=1,7,"{imei}"'
        out, code = self.run_at_command(cmd)

        if code != 0:
            self.logger.error(f"Failed to set IMEI: {out.strip()}")
            return False

        self.logger.info(f"Successfully set new IMEI: {imei}")

        # Store in file
        try:
            os.makedirs('/tmp/modem.1-1.2', exist_ok=True)
            with open('/tmp/modem.1-1.2/modem-imei', 'w') as fh:
                fh.write(imei)
            self.log("Saved IMEI to /tmp/modem.1-1.2/modem-imei")
        except Exception as e:
            self.log(f"Failed to save IMEI to file: {e}")

        # Keep radio disabled
        self.logger.info("Radio will remain disabled until device is rebooted")

        # Reboot the device if requested
        if reboot_after:
            self.logger.info("Rebooting device to apply IMEI changes...")
            try:
                # Give some time for logs to be written
                time.sleep(2)
                # Execute reboot command
                subprocess.run(["/sbin/reboot"], check=False)
                # This point may not be reached if reboot is quick
                return True
            except Exception as e:
                self.logger.error(f"Failed to reboot device: {e}")
                return False
        else:
            # Create a flag file to indicate reboot is needed
            try:
                with open('/tmp/reboot_required', 'w') as f:
                    f.write("A reboot is required to apply the new IMEI")
            except Exception as e:
                self.log(f"Failed to create reboot flag file: {e}")

        return True
