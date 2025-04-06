#!/usr/bin/env python3

import os
import re
import time
from cmd import Cmd
from ..lib.logger import Logger


class ModemController:
    """Class for controlling modem hardware state and communications."""

    # Define possible TTY devices for the modem
    MODEM_TTY_DEVICES = ["/dev/ttyUSB0", "/dev/ttyUSB3"]

    def __init__(self, tty_device=None, verbose=False):
        """
        Initialize the modem controller.

        Args:
            tty_device (str): TTY device path to use (defaults to first available from MODEM_TTY_DEVICES)
            verbose (bool): Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = Logger()

        # Use specified tty_device or find the first available
        if tty_device:
            self.tty_device = tty_device
        else:
            self.tty_device = self._find_available_tty()

        self.cmd = Cmd(tty_device=self.tty_device, verbose=verbose)

    def _find_available_tty(self):
        """Find the first available TTY device from the list."""
        for device in self.MODEM_TTY_DEVICES:
            if os.path.exists(device):
                return device
        # Default to the first one if none found
        self.logger.warning(
            f"No TTY device found, defaulting to {self.MODEM_TTY_DEVICES[0]}")
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
        return self.control_radio(enable=True)

    def disable_radio(self):
        """
        Disable the modem radio (AT+CFUN=4).

        Returns:
            bool: True on success, False on failure
        """
        return self.control_radio(enable=False)

    def control_radio(self, enable=True):
        """
        Enable or disable the modem radio TX/RX.

        Args:
            enable (bool): True to enable radio (AT+CFUN=1), False to disable (AT+CFUN=4)

        Returns:
            bool: True on success, False on failure
        """
        mode = 1 if enable else 4
        status = "Enabling" if enable else "Disabling"

        self.logger.info(f"{status} modem radio...")
        _, code = self.run_at_command(f"AT+CFUN={mode}")

        if code != 0:
            self.logger.warning(f"Failed to {status.lower()} radio.")
            return False

        self.logger.info(f"Radio {'enabled' if enable else 'disabled'}.")
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
        if not self.wait_for_device_gone(timeout=30):
            self.logger.warning(
                "Modem device did not vanish. Trying to continue anyway...")

        # Wait for device to reappear
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

    def get_imsi(self):
        """Get the SIM IMSI"""
        output, _ = self.run_at_command("AT+CIMI")
        if not output:
            return None

        # Look for a IMSI (usually 15 digits) in the output
        match = re.search(r'\b([0-9]{6,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_imei(self):
        """Get the device IMEI"""
        output, _ = self.run_at_command("AT+GSN")
        if not output:
            return None

        # Look for a 15-digit IMEI in the output
        match = re.search(r'\b([0-9]{14,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_iccid(self):
        """Get the SIM ICCID"""
        output, _ = self.run_at_command("AT+CCID")
        if not output:
            return None

        # Look for a ICCID in the output
        match = re.search(r'\b([0-9]{18,22})\b', output)
        if match:
            return match.group(1)
        return None

    def set_imei(self, imei):
        """
        Use AT+EGMR=1,7,"IMEI" to set IMEI. Requires radio disabled first.

        Args:
            imei (str): The new IMEI to set

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

        return True
