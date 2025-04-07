#!/usr/bin/env python3

import sys
import argparse
from bluecode.utils.logger import Logger, LogLevel
from bluecode.core.system import SystemCommand
from bluecode.core.network import NetworkManager
from bluecode.core.mac import MacManager
from bluecode.core.logs import LogManager  # We'll create this later
from bluecode.core.modem import ModemManager  # We'll create this later
from bluecode.core.bssid import BssidManager  # We'll create this later
from bluecode.utils.generators import ImeiGenerator


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='BlueCode Security Tools for network identifier randomization'
    )

    # Command handling
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # 'secure' subcommand for backward compatibility
    secure_parser = subparsers.add_parser(
        'secure', help='Run with options (for backward compatibility)')
    secure_parser.add_argument('--dry-run', action='store_true',
                               help='Simulate actions without making changes')
    secure_parser.add_argument('--verbose', '-v', action='store_true',
                               help='Enable verbose logging')
    secure_parser.add_argument('--interfaces', nargs='+', default=NetworkManager.DEFAULT_INTERFACES,
                               choices=['wan', 'upstream', 'all'],
                               help='Interfaces to randomize (default: wan upstream)')
    secure_parser.add_argument('--no-restart', action='store_true',
                               help='Do not restart network after changes')
    secure_parser.add_argument('--device-index', type=int, default=None,
                               help='Specific device index to use for WAN interface')
    secure_parser.add_argument('--randomize', nargs='+', default=['mac'],
                               choices=['mac', 'bssid', 'imei', 'logs', 'all'],
                               help='What to randomize (default: mac)')

    # Global arguments for default mode
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate actions without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
