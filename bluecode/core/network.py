#!/usr/bin/env python3

import re
import time
from bluecode.utils.logger import Logger
from bluecode.utils.generators import MacGenerator


class NetworkManager:
    """Handle network device configuration and management."""

    # Constants
    DEFAULT_INTERFACES = ["wan", "upstream"]

    def __init__(self, executor):
        """
        Initialize the network manager.

        Args:
            executor (SystemCommand): Command executor instance
        """
        self.logger = Logger()
        self.executor = executor
        self.mac_generator = MacGenerator()

    def get_network_devices(self):
        """
        Get list of network device indices from UCI configuration.

        Returns:
            list: List of network device indices
        """
        try:
            result = self.executor.run_command(
                "uci show network | grep '@device'")
            devices = re.findall(r"network\.@device\[(\d+)\]", result[0])
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
            check_result = self.executor.run_command(
                f"uci get network.@device[{device_index}] 2>/dev/null"
            )

            if check_result[1] != 0 and not dry_run:
                return self._set_wan_mac_alternative(mac, dry_run)

            # Standard approach
            if not dry_run:
                self.executor.run_command(
                    f"uci set network.@device[{device_index}].macaddr={mac}"
                )
            else:
                self.logger.info(
                    f"Would set device[{device_index}] MAC to {mac}")
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
            if not dry_run:
                self.executor.run_command(f"uci set network.wan.macaddr={mac}")
            else:
                self.logger.info(f"Would set network.wan.macaddr to {mac}")
            self.logger.info(f"Set WAN MAC address directly to {mac}")
            return True
        except Exception as e:
            self.logger.debug(f"Failed first alternative: {e}")

        # Second try: Use physical interface if available
        try:
            interfaces_result = self.executor.run_command(
                "ls -1 /sys/class/net/")
            time.sleep(1)
            if "eth0" in interfaces_result[0]:
                self.logger.info("Setting eth0 MAC address directly")

                if not dry_run:
                    self.executor.run_command(f"ip link set eth0 down")
                    self.executor.run_command(
                        f"ip link set eth0 address {mac}")
                    self.executor.run_command(f"ip link set eth0 up")
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

            if not dry_run:
                self.executor.run_command(
                    f"uci set glconfig.general.macclone_addr={mac}")
            else:
                self.logger.info(f"Would set macclone_addr to {mac}")

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
                result = self.executor.run_command(
                    f"uci get network.@device[{device_idx}].macaddr"
                )
                if result[1] == 0:
                    addresses[f"wan_device_{device_idx}"] = result[0].strip()

            # Get MAC clone address
            result = self.executor.run_command(
                "uci get glconfig.general.macclone_addr"
            )
            if result[1] == 0:
                addresses["macclone"] = result[0].strip()

            # Get physical interface MAC addresses
            for iface in ["eth0", "eth1", "wlan0", "wlan1"]:
                try:
                    result = self.executor.run_command(
                        f"cat /sys/class/net/{iface}/address"
                    )
                    if result[1] == 0:
                        addresses[iface] = result[0].strip()
                except Exception:
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
            if not dry_run:
                self.executor.run_command("uci commit network")
                self.executor.run_command("uci commit glconfig")
            else:
                self.logger.info("Would commit network and glconfig changes")

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
            if not dry_run:
                self.executor.run_command("/etc/init.d/network restart")
            else:
                self.logger.info("Would restart network service")

            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart network: {e}")
            return False
