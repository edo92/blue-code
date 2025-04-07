#!/usr/bin/env python3

import sys
import time
import random
import argparse
from .cmd import Cmd
from ..lib.logger import Logger


class BSSID:

    """Class for managing BSSID randomization on wireless interfaces."""

    def __init__(self, verbose=False):
        """Initialize the BSSID manager with logging configuration."""
        # Set up logging
        self.logger = Logger("BSSID", None, verbose)

        # Initialize the Cmd class for command execution
        self.cmd = Cmd(None, verbose=verbose)

    def generate_unicast_mac(self):
        """
        Generate a random unicast MAC address (BSSID) with the locally administered bit set.

        Returns:
            str: A properly formatted unicast MAC address with colons
        """
        mac_int = random.randint(0, 2**48 - 1)

        # Set locally administered bit (bit 1)
        mac_int |= 0x020000000000

        # Clear multicast bit (bit 0)
        mac_int &= 0xFEFFFFFFFFFF

        mac_hex = format(mac_int, '012x')
        mac_formatted = ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))

        self.logger.debug(f"Generated MAC address: {mac_formatted}")
        return mac_formatted

    def run_uci_command(self, command, dry_run=False):
        """
        Execute a UCI command safely.

        Args:
            command (str): The UCI command to execute
            dry_run (bool): If True, only print command without executing

        Returns:
            bool: Success status
            str: Output or error message
        """
        if dry_run:
            self.logger.info(f"Would execute: {command}")
            return True, "Dry run"

        # Use Cmd class to run shell commands
        out, code = self.cmd.run_command(command)

        if code == 0:
            return True, out
        else:
            return False, f"Error: {out}"

    def set_bssid_for_interfaces(self, interfaces=None, dry_run=False):
        """
        Set randomized BSSIDs for the specified wireless interfaces using UCI.

        Args:
            interfaces (list): List of interface indices to update (default: [0, 1])
            dry_run (bool): If True, only print commands without executing

        Returns:
            bool: Success status
            list: List of (interface_index, new_mac) tuples for changes made
        """
        if interfaces is None:
            interfaces = [0, 1]  # Default to set both wlan0 and wlan1

        self.logger.info(f"Setting BSSIDs for interfaces: {interfaces}")
        success = True
        changes = []

        for idx in interfaces:
            new_mac = self.generate_unicast_mac()
            command = f"uci set wireless.@wifi-iface[{idx}].macaddr={new_mac}"

            cmd_success, message = self.run_uci_command(command, dry_run)
            if cmd_success:
                self.logger.info(f"Set interface {idx} BSSID to {new_mac}")
                changes.append((idx, new_mac))
            else:
                self.logger.error(
                    f"Failed to set BSSID for interface {idx}: {message}")
                success = False

        if not dry_run and success and changes:
            self.logger.info("Committing changes to UCI configuration")
            cmd_success, message = self.run_uci_command(
                "uci commit wireless", dry_run)
            if not cmd_success:
                self.logger.error(f"Failed to commit changes: {message}")
                success = False

        return success, changes

    def reset_wifi(self, dry_run=False):
        """
        Reset the WiFi to apply the changes.

        Args:
            dry_run (bool): If True, only print command without executing

        Returns:
            bool: Success status
        """
        self.logger.info("Resetting WiFi to apply changes")
        self.logger.info("Rebooting the device. Please wait...")

        success, message = self.run_uci_command("wifi", dry_run)
        time.sleep(1)

        if success:
            self.logger.info("WiFi reset successful")
        else:
            self.logger.error(f"WiFi reset failed: {message}")

        return success


def main():
    """Main function to parse arguments and execute BSSID randomization."""
    parser = argparse.ArgumentParser(
        description="Randomize BSSIDs for OpenWrt wireless interfaces"
    )
    parser.add_argument(
        "-i", "--interfaces",
        nargs="+", type=int,
        help="Interface indices to update (default: 0 and 1)"
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Print commands without executing them"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Don't reset WiFi after changing BSSIDs"
    )

    args = parser.parse_args()

    # Create BSSID manager
    manager = BSSID(verbose=args.verbose)

    # Set BSSIDs for interfaces
    success, changes = manager.set_bssid_for_interfaces(
        interfaces=args.interfaces,
        dry_run=args.dry_run
    )

    # Reset WiFi if requested and changes were made
    if success and changes and not args.dry_run and not args.no_reset:
        reset_success = manager.reset_wifi(dry_run=args.dry_run)
        if not reset_success:
            return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
