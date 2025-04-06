#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
from util.cmd import Cmd
from lib.logger import Logger

# Define possible TTY devices for the modem
MODEM_TTY_DEVICES = ["/dev/ttyUSB0", "/dev/ttyUSB3"]


class SIM:

    def __init__(self):
        self.imsi = None
        self.imei = None
        self.iccid = None
        self.tty_available = self.check_tty_exists()
        self.logger = Logger()

    def get_imei(self):
        """Get the device IMEI"""
        output = Cmd.run_at_command("AT+GSN")
        if not output:
            return None

        # Look for a 15-digit IMEI in the output
        match = re.search(r'\b([0-9]{14,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_imsi(self):
        """Get the SIM IMSI"""
        output = Cmd.run_at_command("AT+CIMI")
        if not output:
            return None

        # Look for a IMSI (usually 15 digits) in the output
        match = re.search(r'\b([0-9]{6,15})\b', output)
        if match:
            return match.group(1)
        return None

    def get_iccid(self):
        """Get the SIM ICCID"""
        output = Cmd.run_at_command("AT+CCID")
        if not output:
            return None

        # Look for a ICCID in the output
        match = re.search(r'\b([0-9]{18,22})\b', output)
        if match:
            return match.group(1)
        return None

    def check_modem_status(self):
        """Check modem status info"""
        try:
            result = subprocess.run(['cat', '/tmp/run/modem_status'],
                                    capture_output=True,
                                    text=True)
            return result.stdout
        except subprocess.SubprocessError:
            return ""

    def check_tty_exists(self):
        """Check if the required tty device exists"""
        return os.path.exists("/dev/ttyUSB3")

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

    def check_vsim_profile(self):
        """Check if vSIM profiles exist"""
        try:
            # Try to access vSIM-specific files or API
            result = subprocess.run(['ubus', 'call', 'vsim', 'status'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data.get('active') or data.get('status') == 'active':
                        return True
                except json.JSONDecodeError:
                    pass

                # If we got output but couldn't parse it, check if it contains vsim indicators
                if 'vsim' in result.stdout.lower() and ('active' in result.stdout.lower() or
                                                        'enabled' in result.stdout.lower()):
                    return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check for vSIM process running
        try:
            result = subprocess.run(['ps', '|', 'grep', 'vsim'],
                                    shell=True,
                                    capture_output=True,
                                    text=True)
            if 'vsim' in result.stdout and not 'grep vsim' in result.stdout:
                return True
        except subprocess.SubprocessError:
            pass

        return False

    def check_esim_profile(self):
        """Check if eSIM profiles exist"""
        try:
            # Try to access eSIM-specific API
            result = subprocess.run(['ubus', 'call', 'esim', 'status'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data.get('active') or data.get('status') == 'active':
                        return True
                except json.JSONDecodeError:
                    pass

                # If we got output but couldn't parse it, check if it contains esim indicators
                if 'esim' in result.stdout.lower() and ('active' in result.stdout.lower() or
                                                        'enabled' in result.stdout.lower()):
                    return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check for eSIM process running
        try:
            result = subprocess.run(['ps', '|', 'grep', 'esim'],
                                    shell=True,
                                    capture_output=True,
                                    text=True)
            if 'esim' in result.stdout and not 'grep esim' in result.stdout:
                return True
        except subprocess.SubprocessError:
            pass

        # Check for eSIM application
        try:
            result = subprocess.run(['ls', '/usr/share/applications/esim'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0 and 'esim' in result.stdout:
                return True
        except subprocess.SubprocessError:
            pass

        return False

    def detect_sim_type(self):
        """
        Detect what type of SIM is being used in the GL-iNet Mudi v2

        Returns:
            str: 'physical', 'virtual', 'esim', or 'unknown'
        """
        if not self.check_tty_exists():
            self.logger.error(
                "TTY device not found. Make sure the modem is properly connected.")
            return "unknown"

        # Get IMSI first - if we can't get this, SIM might not be present
        imsi = self.get_imsi()
        if not imsi:
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
            self.logger.info(f"IMSI: {imsi}")
            self.logger.info("vSIM is active")
            return "virtual"

        # Check for eSIM indicators
        if self.check_esim_profile():
            self.logger.info(f"IMSI: {imsi}")
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
        if imsi:
            self.logger.info(f"IMSI: {imsi}")
            iccid = self.get_iccid()
            if iccid:
                self.logger.info(f"ICCID: {iccid}")
            self.logger.info("Physical SIM detected")
            return "physical"

        return "unknown"
