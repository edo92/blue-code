#!/usr/bin/env python3

import argparse
import sys

from core.bssid import BSSIDManager
from core.net import  NetworkConfigurator


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Randomize MAC addresses for network interfaces'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate actions without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--interfaces', nargs='+', default=NetworkConfigurator.DEFAULT_INTERFACES,
                        choices=['wan', 'upstream', 'all'],
                        help='Interfaces to randomize (default: wan upstream)')
    parser.add_argument('--no-restart', action='store_true',
                        help='Do not restart network after changes')
    parser.add_argument('--device-index', type=int, default=None,
                        help='Specific device index to use for WAN interface')

    return parser.parse_args()


def main():
    manager = BSSIDManager()

    # # Check if running as root
    # if not randomizer.check_running_as_root() and not args.dry_run:
    #     return 1

    # # Randomize MAC addresses
    # success = randomizer.randomize_mac_addresses(
    #     args.interfaces,
    #     args.device_index,
    #     args.dry_run,
    #     args.no_restart
    # )

    # return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
