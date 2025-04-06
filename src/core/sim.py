#!/usr/bin/env python3


import json
import os
import subprocess
from ..lib.logger import Logger
from .modem import ModemController


class SIM:
    """Class for detecting and managing SIM card information."""

    def __init__(self, modem_controller=None, verbose=False):
        """
        Initialize the SIM detector.

        Args:
            modem_controller (ModemController): An existing ModemController instance or None to create a new one
            verbose (bool): Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = Logger()

        # Use the provided ModemController or create a new one
        if modem_controller:
            self.modem = modem_controller
        else:
            self.modem = ModemController(verbose=verbose)

        # Initialize SIM information properties
        self.imsi = None
        self.imei = None
        self.iccid = None

    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            self.logger.debug(f"[SIM] {message}")

    def check_modem_status(self):
        """Check modem status info"""
        try:
            result = subprocess.run(['cat', '/tmp/run/modem_status'],
                                    capture_output=True,
                                    text=True)
            return result.stdout
        except subprocess.SubprocessError:
            return ""

    def check_sim_detection(self):
        """Check SIM detection in system logs"""
        try:
            result = subprocess.run(['logread', '|', 'grep', '-i', 'sim'],
                                    shell=True,
                                    capture_output=True,
                                    text=True)
            return result.stdout
        except subprocess.SubprocessError:
            return ""

    def _check_profile_status(self, profile_type):
        """
        Check the status of a profile type (vsim or esim).

        Args:
            profile_type (str): Either 'vsim' or 'esim'

        Returns:
            bool: True if the profile is active, False otherwise
        """
        try:
            # Try to access profile-specific API
            result = subprocess.run(['ubus', 'call', profile_type, 'status'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data.get('active') or data.get('status') == 'active':
                        return True
                except json.JSONDecodeError:
                    pass

                # If we got output but couldn't parse it, check if it contains profile indicators
                if profile_type in result.stdout.lower() and ('active' in result.stdout.lower() or
                                                              'enabled' in result.stdout.lower()):
                    return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check for process running
        try:
            result = subprocess.run(['ps', '|', 'grep', profile_type],
                                    shell=True,
                                    capture_output=True,
                                    text=True)
            if profile_type in result.stdout and not f'grep {profile_type}' in result.stdout:
                return True
        except subprocess.SubprocessError:
            pass

        # For eSIM, also check for application
        if profile_type == 'esim':
            try:
                result = subprocess.run(['ls', '/usr/share/applications/esim'],
                                        capture_output=True,
                                        text=True)
                if result.returncode == 0 and 'esim' in result.stdout:
                    return True
            except subprocess.SubprocessError:
                pass

        return False

    def check_vsim_profile(self):
        """Check if vSIM profiles exist and are active"""
        return self._check_profile_status('vsim')

    def check_esim_profile(self):
        """Check if eSIM profiles exist and are active"""
        return self._check_profile_status('esim')

    def fetch_sim_info(self):
        """
        Fetch all available SIM information (IMSI, IMEI, ICCID)

        Returns:
            dict: Dictionary with SIM information
        """
        self.imsi = self.modem.get_imsi()
        self.imei = self.modem.get_imei()
        self.iccid = self.modem.get_iccid()

        return {
            'imsi': self.imsi,
            'imei': self.imei,
            'iccid': self.iccid
        }

    def detect_sim_type(self):
        """
        Detect what type of SIM is being used in the device

        Returns:
            str: 'physical', 'virtual', 'esim', or 'unknown'
        """
        # Check if tty device exists
        if not os.path.exists(self.modem.tty_device):
            self.logger.error(
                "TTY device not found. Make sure the modem is properly connected.")
            return "unknown"

        # Get IMSI first - if we can't get this, SIM might not be present
        self.imsi = self.modem.get_imsi()
        if not self.imsi:
            self.logger.warn(
                "No IMSI detected. SIM card may not be present or modem may be off.")

            # If we can't get IMSI, check if vSIM or eSIM is active
            if self.check_vsim_profile():
                self.logger.info("vSIM profile detected but not active.")
                return "virtual"
            if self.check_esim_profile():
                self.logger.info("eSIM profile detected but not active.")
                return "esim"

            return "unknown"

        # Check for vSIM indicators
        if self.check_vsim_profile():
            self.logger.info(f"IMSI: {self.imsi}")
            self.logger.info("vSIM is active")
            return "virtual"

        # Check for eSIM indicators
        if self.check_esim_profile():
            self.logger.info(f"IMSI: {self.imsi}")
            self.logger.info("eSIM is active")
            return "esim"

        # Check modem status and logs for additional clues
        sim_logs = self.check_sim_detection()

        # If vSIM indicators in logs
        if 'vsim' in sim_logs.lower():
            return "virtual"

        # If eSIM indicators in logs
        if 'esim' in sim_logs.lower():
            return "esim"

        # If we have an IMSI but no specific indicators of vSIM or eSIM,
        # assume it's a physical SIM
        if self.imsi:
            self.logger.info(f"IMSI: {self.imsi}")
            self.iccid = self.modem.get_iccid()
            if self.iccid:
                self.logger.info(f"ICCID: {self.iccid}")
            self.logger.info("Physical SIM detected")
            return "physical"

        return "unknown"
