#!/usr/bin/env python3

import os
import re


class LogWiper:
    """Class for wiping MAC addresses from system logs."""

    # Common log files that might contain MAC addresses
    LOG_FILES = [
        '/var/log/messages',
        '/var/log/syslog',
        '/var/log/daemon.log',
        '/var/log/wifi.log',
        '/var/log/firewall.log',
        '/tmp/dhcp.leases',
        '/tmp/dhcp.log',
        '/tmp/dnsmasq.log',
        '/tmp/state/dhcp.leases',
    ]

    # Special directories to check for log files
    LOG_DIRS = [
        '/var/log/',
        '/tmp/log/',
        '/tmp/run/',
    ]

    def __init__(self, logger, executor):
        """
        Initialize the log wiper.

        Args:
            logger (logging.Logger): Logger instance
            executor (CommandExecutor): Command executor instance
        """
        self.logger = logger
        self.executor = executor

    def wipe_mac_logs(self, dry_run=False):
        """
        Wipe MAC addresses from common log files.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Wiping MAC addresses from logs...")
        success = True

        # 1. Clean standard log files that we know about
        for log_file in self.LOG_FILES:
            if os.path.exists(log_file) and os.path.isfile(log_file):
                if not self._clean_log_file(log_file, dry_run):
                    success = False

        # 2. Search for log files in common directories
        self._find_and_clean_log_files(dry_run)

        # 3. Clean dmesg buffer
        self._clean_dmesg(dry_run)

        # 4. Restart logging services if needed
        if not dry_run:
            self._restart_logging_services()

        self.logger.info("Log wiping completed")
        return success

    def _clean_log_file(self, log_file, dry_run=False):
        """
        Clean MAC addresses from a single log file.

        Args:
            log_file (str): Path to log file
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        # MAC address regex pattern
        mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'

        try:
            self.logger.info(f"Cleaning MAC addresses from {log_file}")

            if dry_run:
                # In dry run mode, just report the file would be cleaned
                self.logger.info(f"Would clean MAC addresses from {log_file}")
                return True

            # Read file content
            with open(log_file, 'r', errors='replace') as f:
                content = f.read()

            # Replace MAC addresses with XX:XX:XX:XX:XX:XX
            new_content = re.sub(mac_pattern, 'XX:XX:XX:XX:XX:XX', content)

            # Write back to file
            with open(log_file, 'w') as f:
                f.write(new_content)

            return True
        except Exception as e:
            self.logger.error(f"Failed to clean log file {log_file}: {e}")
            return False

    def _find_and_clean_log_files(self, dry_run=False):
        """
        Find and clean log files in common log directories.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        for log_dir in self.LOG_DIRS:
            if not os.path.exists(log_dir) or not os.path.isdir(log_dir):
                continue

            try:
                # Find log files in directory
                for filename in os.listdir(log_dir):
                    filepath = os.path.join(log_dir, filename)
                    if os.path.isfile(filepath) and self._is_log_file(filepath):
                        self._clean_log_file(filepath, dry_run)
            except Exception as e:
                self.logger.error(f"Error processing directory {log_dir}: {e}")

        return True

    def _is_log_file(self, filepath):
        """
        Check if a file is likely a log file that might contain MAC addresses.

        Args:
            filepath (str): Path to file

        Returns:
            bool: True if file is likely a log, False otherwise
        """
        # Check file extension
        extensions = ['.log', '.txt', '.leases']
        if any(filepath.endswith(ext) for ext in extensions):
            return True

        # Check file size (don't process files over 10MB to avoid memory issues)
        try:
            if os.path.getsize(filepath) > 10 * 1024 * 1024:
                return False
        except Exception:
            return False

        # Check if file contains MAC address patterns
        try:
            with open(filepath, 'r', errors='ignore') as f:
                # Read up to 100 lines to check for MAC addresses
                for _ in range(100):
                    line = f.readline()
                    if not line:
                        break
                    if re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line):
                        return True
        except Exception:
            pass

        return False

    def _clean_dmesg(self, dry_run=False):
        """
        Clean MAC addresses from dmesg buffer.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Cleaning MAC addresses from dmesg buffer")

        if dry_run:
            self.logger.info("Would clean dmesg buffer")
            return True

        try:
            # Clear dmesg buffer (requires root)
            self.executor.execute("dmesg -c > /dev/null", check=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear dmesg buffer: {e}")
            return False

    def _restart_logging_services(self):
        """
        Restart logging services to ensure clean logs going forward.

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Restarting logging services")

        # Try to restart common logging services used on OpenWrt
        services = ['log', 'syslog', 'rsyslog', 'syslog-ng']

        for service in services:
            try:
                # Check if service exists and restart it
                self.executor.execute(
                    f"/etc/init.d/{service} restart", check=False)
            except Exception:
                pass

        return True
