#!/usr/bin/env python3

import os
from bluecode.utils.logger import Logger
from bluecode.core.network import NetworkManager
from bluecode.utils.generators import MacGenerator


class MacManager:
    """Main class for MAC address randomization and management."""

    def __init__(self, executor):
        """
        Initialize the MAC manager.

        Args:
            executor (SystemCommand): Command executor instance
        """
        self.logger = Logger()
        self.executor = executor
        self.network = NetworkManager(executor)

    def check_running_as_root(self):
        """
        Check if the script is running with root privileges.

        Returns:
            bool: True if running as root, False otherwise
        """
        return os.geteuid() == 0

    def randomize_mac_addresses(self, interfaces, device_index=None, dry_run=False, no_restart=False):
        """
        Randomize MAC addresses for specified interfaces.

        Args:
            interfaces (list): List of interfaces to randomize ('wan', 'upstream', 'all')
            device_index (int, optional): Specific device index to use for WAN interface
            dry_run (bool): If True, only simulate actions
            no_restart (bool): If True, do not restart network after changes

        Returns:
            bool: True if successful, False otherwise
        """
        # Log current MAC addresses
        self.logger.info("Current MAC addresses:")
        current_macs = self.network.get_current_mac_addresses()
        for iface, mac in current_macs.items():
            self.logger.info(f"  {iface}: {mac}")

        # Expand 'all' to include both interfaces
        if 'all' in interfaces:
            interfaces = ['wan', 'upstream']

        changes_made = False

        # Randomize interfaces as requested
        if 'wan' in interfaces:
            changes_made = self._randomize_wan_interface(
                device_index, dry_run) or changes_made

        if 'upstream' in interfaces:
            if self.network.set_macclone_address(dry_run):
                changes_made = True

        # Apply changes if needed
        if changes_made:
            if not self.network.commit_changes(dry_run):
                self.logger.error("Failed to apply changes")
                return False

            # Restart network if not skipped
            if not no_restart and not dry_run:
                self.network.restart_network(dry_run)

                # Log new MAC addresses
                self.logger.info("New MAC addresses:")
                new_macs = self.network.get_current_mac_addresses()
                for iface, mac in new_macs.items():
                    self.logger.info(f"  {iface}: {mac}")
        else:
            self.logger.info("No changes were made")

        self.logger.info("MAC address randomization complete")
        return True

    def _randomize_wan_interface(self, device_index, dry_run):
        """
        Handle WAN MAC address randomization.

        Args:
            device_index (int, optional): Specific device index to use
            dry_run (bool): If True, only simulate actions

        Returns:
            bool: True if changes were made, False otherwise
        """
        if device_index is not None:
            # Use specified device index
            return self.network.set_wan_mac_address(device_index, dry_run)

        # Try each device index until one succeeds
        for device_idx in self.network.get_network_devices():
            if self.network.set_wan_mac_address(device_idx, dry_run):
                return True

        # All devices failed, try direct approach
        self.logger.info("Trying direct MAC change approach")
        mac = MacGenerator.generate_unicast_mac()

        try:
            if not dry_run:
                self.executor.run_command(f"uci set network.wan.macaddr={mac}")
            else:
                self.logger.info(f"Would set network.wan.macaddr to {mac}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed direct MAC set approach: {e}")

        return False
