#!/usr/bin/env python3

import os
import re
import subprocess
from lib.logger import Logger


class Cmd:

    """Class for executing commands including AT commands for modems."""

    def __init__(self, tty_device=None, verbose=False):
        """
        Initialize the command execution class.

        Args:
            tty_device (str): Path to the TTY device for direct serial communication
            verbose (bool): Whether to output detailed logging information
        """
        self.tty_device = tty_device
        self.verbose = verbose
        self.logger = Logger()

    def run_command(self, command):
        """
        Run a shell command.

        Args:
            command (str): The shell command to execute

        Returns:
            tuple: (output_string, exit_code) where exit_code is 0 for success
        """
        if self.verbose:
            self.logger.debug(f"Running shell command: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr

            if self.verbose:
                self.logger.debug(
                    f"Command returned exit code {result.returncode}")
                self.logger.debug(f"Command output:\n{output.strip()}")

            return output, result.returncode

        except Exception as e:
            err_msg = f"Error executing command: {e}"
            self.logger.error(err_msg)
            return str(e), 1

    def run_at_command(self, command):
        """
        Execute an AT command using the best available method.
        First tries gl_modem if available, then falls back to serial communication.

        Args:
            command (str): The AT command to execute

        Returns:
            tuple: (output_string, exit_code) where exit_code is 0 for success
        """
        # Check if gl_modem is available
        if self.is_gl_modem_available():
            return self.run_gl_modem(command)
        else:
            if not self.tty_device:
                err_msg = "No TTY device specified and gl_modem not available"
                self.logger.error(err_msg)
                return err_msg, 1
            return self.run_serial_command(command)

    def run_gl_modem(self, command):
        """
        Run an AT command using the gl_modem utility.

        Args:
            command (str): The AT command to execute

        Returns:
            tuple: (output_string, exit_code) where exit_code is 0 for success
        """
        if self.verbose:
            self.logger.debug(f"Running via gl_modem: {command}")

        cmd = ["gl_modem", "AT", command]

        # Add tty device if specified and not the default
        if self.tty_device and self.tty_device != '/dev/ttyUSB3':
            cmd.extend(["--tty", self.tty_device])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            out = result.stdout

            if self.verbose:
                self.logger.debug(f"gl_modem returned:\n{out.strip()}")

            # Check for success indication
            if re.search(r"\bOK\b", out, re.IGNORECASE):
                return out, 0
            else:
                return out, 1

        except Exception as e:
            err_msg = f"Error executing gl_modem command: {e}"
            self.logger.error(err_msg)
            return str(e), 1

    def run_serial_command(self, command):
        """
        Run an AT command via direct serial communication.

        Args:
            command (str): The AT command to execute

        Returns:
            tuple: (output_string, exit_code) where exit_code is 0 for success
        """
        if not self.tty_device:
            err_msg = "No TTY device specified for serial communication"
            self.logger.error(err_msg)
            return err_msg, 1

        if self.verbose:
            self.logger.debug(f"Running direct serial command: {command}")

        try:
            import serial

            with serial.Serial(self.tty_device, 9600, timeout=3) as ser:
                full_cmd = f"{command}\r"
                ser.flushInput()
                ser.flushOutput()
                ser.write(full_cmd.encode())

                # Read up to 1024 bytes
                resp = ser.read(1024).decode(errors='ignore')
                if self.verbose:
                    self.logger.debug(f"Serial read:\n{resp.strip()}")

                if re.search(r"\bOK\b", resp, re.IGNORECASE):
                    return resp, 0
                else:
                    return resp, 1

        except Exception as e:
            err_msg = f"Error executing serial command: {e}"
            self.logger.error(err_msg)
            return str(e), 1

    @staticmethod
    def is_gl_modem_available():
        """
        Check if the gl_modem utility is available on the system.

        Returns:
            bool: True if gl_modem is available, False otherwise
        """
        return os.path.exists("/usr/bin/gl_modem")
