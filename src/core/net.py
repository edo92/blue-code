#!/usr/bin/env python3


import re
import time
import subprocess
from ..lib.logger import Logger
from .mac_gen import MacAddressGenerator


class CommandExecutor:
    """Handle command execution with proper error handling."""

    def __init__(self):
        """Initialize the command executor."""
        self.logger = Logger()

    def execute(self, command, dry_run=False, check=True, shell=True):
        """
        Execute a shell command with proper error handling.

        Args:
            command (str): Command to execute
            dry_run (bool): If True, only print the command without executing
            check (bool): If True, raise exception on command failure
            shell (bool): If True, use shell to execute command

        Returns:
            subprocess.CompletedProcess: Result of the command execution
        """
        self.logger.debug(f"Executing: {command}")

        if dry_run:
            self.logger.info(f"Would execute: {command}")
            # Create a mock CompletedProcess for dry runs
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='', stderr='')

        try:
            result = subprocess.run(
                command,
                shell=shell,
                check=check,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error output: {e.stderr}")
            if check:
                raise
            return e


class NetworkConfigurator:
    """Handle network device configuration."""

    # Constants
    DEFAULT_INTERFACES = ["wan", "upstream"]

    def __init__(self, executor):
        """
        Initialize the network configurator.

        Args:
            executor (CommandExecutor): Command executor instance
        """
        self.logger = Logger()
        self.executor = executor
        self.mac_generator = MacAddressGenerator()

    def get_network_devices(self):
        """
        Get list of network device indices from UCI configuration.

        Returns:
            list: List of network device indices
        """
        try:
            result = self.executor.execute("uci show network | grep '@device'")
            devices = re.findall(r"network\.@device\[(\d+)\]", result.stdout)
            return [int(d) for d in devices]

        except Exception as e:
            self.logger.error(f"Failed to retrieve network devices: {e}")
            return [0]  # Default to device[0] if we can't get the list

    def set_wan_mac_address(self, device_index=1, dry_run=False):
        """
        Set a random MAC address for the WAN interface.

        Args:
            device_index (int): The device index to modify
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            mac = self.mac_generator.generate_unicast_mac()
            self.logger.info(
                f"Setting WAN interface (device[{device_index}]) MAC to: {mac}")

            # First check if the device exists and has a macaddr attribute
            check_result = self.executor.execute(
                f"uci get network.@device[{device_index}] 2>/dev/null",
                check=False,
                dry_run=dry_run
            )

            if check_result.returncode != 0 and not dry_run:
                return self._set_wan_mac_alternative(mac, dry_run)

            # Standard approach
            self.executor.execute(
                f"uci set network.@device[{device_index}].macaddr={mac}",
                dry_run=dry_run
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set WAN MAC address: {e}")
            return False

    def _set_wan_mac_alternative(self, mac, dry_run=False):
        """
        Try alternative methods to set the WAN MAC address.

        Args:
            mac (str): MAC address to set
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.warning(
            "Standard device approach failed, trying alternatives")

        # First try: Set MAC address for wan interface directly
        try:
            self.executor.execute(
                f"uci set network.wan.macaddr={mac}", dry_run=dry_run)
            self.logger.info(f"Set WAN MAC address directly to {mac}")
            return True
        except Exception as e:
            self.logger.debug(f"Failed first alternative: {e}")

        # Second try: Use physical interface if available
        try:
            interfaces_result = self.executor.execute(
                "ls -1 /sys/class/net/", check=False)
            time.sleep(1)
            if "eth0" in interfaces_result.stdout:
                self.logger.info("Setting eth0 MAC address directly")

                if not dry_run:
                    self.executor.execute(f"ip link set eth0 down")
                    self.executor.execute(f"ip link set eth0 address {mac}")
                    self.executor.execute(f"ip link set eth0 up")
                else:
                    self.logger.info(f"Would set eth0 MAC to {mac}")

                return True
        except Exception as e:
            self.logger.debug(f"Failed second alternative: {e}")

        return False

    def set_macclone_address(self, dry_run=False):
        """
        Set a random MAC clone address for upstream WiFi connections.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            mac = self.mac_generator.generate_unicast_mac()
            self.logger.info(f"Setting MAC clone address to: {mac}")
            self.executor.execute(
                f"uci set glconfig.general.macclone_addr={mac}", dry_run=dry_run)
            time.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"Failed to set MAC clone address: {e}")
            return False

    def get_current_mac_addresses(self):
        """
        Get current MAC addresses for logging purposes.

        Returns:
            dict: Dictionary with current MAC addresses
        """
        addresses = {}

        try:
            # Get WAN MAC addresses
            for device_idx in self.get_network_devices():
                result = self.executor.execute(
                    f"uci get network.@device[{device_idx}].macaddr",
                    check=False
                )
                if result.returncode == 0:
                    addresses[f"wan_device_{device_idx}"] = result.stdout.strip(
                    )

            # Get MAC clone address
            result = self.executor.execute(
                "uci get glconfig.general.macclone_addr", check=False)
            if result.returncode == 0:
                addresses["macclone"] = result.stdout.strip()

            # Get physical interface MAC addresses
            for iface in ["eth0", "eth1", "wlan0", "wlan1"]:
                try:
                    result = self.executor.execute(
                        f"cat /sys/class/net/{iface}/address", check=False)
                    if result.returncode == 0:
                        addresses[iface] = result.stdout.strip()
                except:
                    pass
        except Exception as e:
            self.logger.warning(f"Error getting current MAC addresses: {e}")

        return addresses

    def commit_changes(self, dry_run=False):
        """
        Commit UCI changes.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Commit network changes
            self.executor.execute("uci commit network", dry_run=dry_run)

            # Commit glconfig changes for MAC clone
            self.executor.execute("uci commit glconfig", dry_run=dry_run)

            self.logger.info("Changes committed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
            return False

    def restart_network(self, dry_run=False):
        """
        Restart network to apply changes.

        Args:
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Restarting network to apply changes")
            self.executor.execute(
                "/etc/init.d/network restart", dry_run=dry_run)
            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart network: {e}")
            return False
