#!/usr/bin/env python3

import os
import re
import tempfile
from bluecode.utils.logger import Logger


class LogManager:
    """
    Enhanced class for wiping MAC addresses from system logs with strong anti-forensic measures.
    Complete replacement for the original LogWiper with stronger security guarantees.
    """

    # Client database location
    CLIENT_DB_PATH = "/etc/oui-tertf"
    CLIENT_DB_FILE = os.path.join(CLIENT_DB_PATH, "client.db")

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

    # Services that manage client database and logs
    RELATED_SERVICES = [
        'gl-tertf',
        'gl_clients',
        'log',
        'syslog',
        'rsyslog',
        'syslog-ng'
    ]

    def __init__(self, logger, executor):
        """
        Initialize the enhanced log manager.

        Args:
            logger (Logger): Logger instance
            executor (SystemCommand): Command executor instance
        """
        self.logger = logger
        self.executor = executor

    def secure_client_database(self, dry_run=False):
        """
        Implement the original hardening approach for client database.

        This method:
        1. Creates a temporary directory
        2. Mounts a tmpfs to it
        3. Backs up the client database
        4. Securely shreds the original database
        5. Unmounts any existing tmpfs at the client database location
        6. Mounts a new tmpfs at the client database location
        7. Restores the database structure to RAM

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        if dry_run:
            self.logger.info("Would secure client database using tmpfs mount")
            return True

        try:
            # Check if client database path exists
            if not os.path.exists(self.CLIENT_DB_PATH):
                self.logger.warning(
                    f"{self.CLIENT_DB_PATH} does not exist, creating it")
                os.makedirs(self.CLIENT_DB_PATH, exist_ok=True)

            # Create temporary directory
            tmp_dir = tempfile.mkdtemp()
            self.logger.info(f"Created temporary directory: {tmp_dir}")

            # Mount tmpfs to temporary directory
            self.executor.run_command(f"mount -t tmpfs tmpfs {tmp_dir}")

            # Backup client database if it exists
            if os.path.exists(self.CLIENT_DB_FILE):
                self.executor.run_command(
                    f"cp -a {self.CLIENT_DB_FILE} {tmp_dir}/")

                # Securely shred the original database
                self.secure_delete_file(self.CLIENT_DB_FILE)

            # Unmount any existing tmpfs at client database location
            self.executor.run_command(
                f"umount -t tmpfs -l {self.CLIENT_DB_PATH}", check=False)

            # Mount tmpfs at client database location
            self.executor.run_command(
                f"mount -t tmpfs tmpfs {self.CLIENT_DB_PATH}")

            # Restore database structure if backup exists
            if os.path.exists(f"{tmp_dir}/client.db"):
                self.executor.run_command(
                    f"cp -a {tmp_dir}/client.db {self.CLIENT_DB_PATH}/")

            # Clean up temporary directory
            self.executor.run_command(f"umount -t tmpfs -l {tmp_dir}")
            os.rmdir(tmp_dir)

            self.logger.info(
                "Client database secured with tmpfs (RAM-only storage)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to secure client database: {e}")
            return False

    def secure_delete_file(self, filepath):
        """
        Securely delete a file using shred or secure overwrite methods.

        Args:
            filepath (str): Path to the file to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Securely deleting {filepath}")

            # Try using shred (preferred method)
            try:
                result = self.executor.run_command(
                    f"shred --force --zero --remove {filepath}")
                if result[1] == 0:
                    return True
            except Exception:
                self.logger.warning(
                    "Shred command failed, falling back to alternative methods")

            # Fallback to manual secure deletion
            if os.path.exists(filepath):
                # Get file size
                file_size = os.path.getsize(filepath)

                # Open file in binary mode and overwrite with zeros
                with open(filepath, 'wb') as f:
                    # Write zeros
                    f.write(b'\x00' * file_size)
                    # Ensure data is flushed to disk
                    f.flush()
                    os.fsync(f.fileno())

                # Overwrite with random data
                with open(filepath, 'wb') as f:
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

                # Final overwrite with zeros
                with open(filepath, 'wb') as f:
                    f.write(b'\x00' * file_size)
                    f.flush()
                    os.fsync(f.fileno())

                # Delete the file
                os.remove(filepath)

            return True

        except Exception as e:
            self.logger.error(f"Failed to securely delete {filepath}: {e}")
            return False

    def secure_wipe_directory(self, directory):
        """
        Securely wipe all files in a directory.

        Args:
            directory (str): Directory to wipe

        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return True

        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    self.secure_delete_file(filepath)
                elif os.path.isdir(filepath):
                    self.secure_wipe_directory(filepath)

            return True

        except Exception as e:
            self.logger.error(f"Failed to wipe directory {directory}: {e}")
            return False

    def _clean_log_file(self, log_file, dry_run=False):
        """
        Clean MAC addresses from a single log file with secure overwriting.

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

            if not os.path.exists(log_file):
                return True

            # Create a temporary file
            temp_file = f"{log_file}.new"

            # Read file content and replace MAC addresses
            with open(log_file, 'r', errors='replace') as f_in:
                with open(temp_file, 'w') as f_out:
                    for line in f_in:
                        # Replace MAC addresses with XX:XX:XX:XX:XX:XX
                        sanitized_line = re.sub(
                            mac_pattern, 'XX:XX:XX:XX:XX:XX', line)
                        f_out.write(sanitized_line)

            # Securely delete the original file
            self.secure_delete_file(log_file)

            # Rename the new file to the original name
            os.rename(temp_file, log_file)

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
        extensions = ['.log', '.txt', '.leases', '.db', '.sqlite', '.json']
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
            self.executor.run_command("dmesg -c > /dev/null")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear dmesg buffer: {e}")
            return False

    def _restart_related_services(self):
        """
        Restart services related to client database and logging.

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Restarting related services")

        for service in self.RELATED_SERVICES:
            try:
                # Check if service exists and restart it
                self.executor.run_command(
                    f"/etc/init.d/{service} restart", check=False)
            except Exception:
                pass

        return True

    def check_init_script(self):
        """
        Check if the init script is properly installed and enabled.

        Returns:
            bool: True if script is installed and enabled, False otherwise
        """
        try:
            # Check if script exists
            script_exists = os.path.exists("/etc/init.d/gl-mac-security")

            # Check if script is enabled (linked in rc.d)
            enabled = False
            if script_exists:
                result = self.executor.run_command(
                    "ls -la /etc/rc.d/S*gl-mac-security 2>/dev/null")
                enabled = result[1] == 0

            if not script_exists:
                self.logger.warning(
                    "Boot-time security script not found. Security will not persist across reboots.")
                return False

            if not enabled:
                self.logger.warning(
                    "Boot-time security script exists but is not enabled. Run 'chmod +x /etc/init.d/gl-mac-security && /etc/init.d/gl-mac-security enable' to enable it.")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to check init script status: {e}")
            return False

    def wipe_mac_logs(self, dry_run=False):
        """
        Comprehensive MAC address wiping with anti-forensic measures.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info(
            "Starting comprehensive MAC address wiping with anti-forensic measures...")
        success = True

        # 1. Secure client database with tmpfs
        if not self.secure_client_database(dry_run):
            success = False

        # 2. Clean standard log files that we know about
        for log_file in self.LOG_FILES:
            if os.path.exists(log_file) and os.path.isfile(log_file):
                if not self._clean_log_file(log_file, dry_run):
                    success = False

        # 3. Search for log files in common directories
        self._find_and_clean_log_files(dry_run)

        # 4. Clean dmesg buffer
        self._clean_dmesg(dry_run)

        # 5. Additional forensic countermeasures
        if not dry_run:
            # Flush file system buffers
            self.executor.run_command("sync")

            # Clear file system journal if possible
            self.executor.run_command(
                "echo 1 > /proc/sys/vm/drop_caches")

        # 6. Restart related services
        if not dry_run:
            self._restart_related_services()

        # 7. Check if init script is installed for boot-time protection
        if not dry_run:
            init_status = self.check_init_script()
            if not init_status:
                self.logger.error(
                    "SECURITY WARNING: Boot-time protection script not properly installed.")
                self.logger.error(
                    "This is a critical security issue that must be fixed immediately.")
                self.logger.error(
                    "Run the installation script to ensure proper security measures.")

        self.logger.info(
            "MAC address wiping with anti-forensic measures completed")
        return success
