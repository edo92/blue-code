#!/usr/bin/env python3

import os
from .net import NetworkConfigurator


class MacRandomizer:
    """Main class for MAC address randomization."""

    def __init__(self, logger, executor):
        """
        Initialize the MAC randomizer.

        Args:
            logger (logging.Logger): Logger instance for output
            executor (CommandExecutor): Command executor instance
        """
        self.logger = logger
        self.executor = executor
        self.network = NetworkConfigurator(logger, executor)

    def check_running_as_root(self):
        """
        Check if the script is running with root privileges.

        Returns:
            bool: True if running as root, False otherwise
        """
        if os.geteuid() != 0:
            self.logger.error("This script must be run as root")
            return False
        return True

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

        if 'all' in interfaces:
            interfaces = ['wan', 'upstream']

        changes_made = False

        # Randomize WAN MAC address if requested
        if 'wan' in interfaces:
            changes_made = self._handle_wan_randomization(
                device_index, dry_run) or changes_made

        # Randomize upstream MAC address if requested
        if 'upstream' in interfaces:
            if self.network.set_macclone_address(dry_run):
                changes_made = True

        # Commit changes if any were made
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

    def _handle_wan_randomization(self, device_index, dry_run):
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
        else:
            # Try all device indices
            success = False
            for device_idx in self.network.get_network_devices():
                if self.network.set_wan_mac_address(device_idx, dry_run):
                    success = True
                    break

            # If no device worked, try a direct approach
            if not success:
                self.logger.info("Trying direct MAC change approach")
                # Generate a MAC address
                mac = MacAddressGenerator.generate_unicast_mac()
                try:
                    # Try setting MAC for wan interface directly
                    self.executor.execute(
                        f"uci set network.wan.macaddr={mac}", dry_run=dry_run)
                    return True
                except Exception as e:
                    self.logger.warning(f"Failed direct MAC set approach: {e}")

            return success
