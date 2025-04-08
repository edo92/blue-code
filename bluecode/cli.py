#!/usr/bin/env python3

import sys
import argparse
from bluecode.utils.logger import Logger, LogLevel
from bluecode.core.system import SystemCommand
from bluecode.core.network import NetworkManager
from bluecode.core.mac import MacManager
from bluecode.core.logs import LogManager
from bluecode.core.modem import ModemManager
from bluecode.core.bssid import BssidManager
from bluecode.core.sim import SimManager
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
    secure_parser.add_argument('--randomize', nargs='+', default=['all'],
                               choices=['mac', 'bssid', 'imei', 'logs', 'all'],
                               help='What to randomize (default: mac)')

    # 'info' subcommand for retrieving information
    info_parser = subparsers.add_parser(
        'info', help='Display current network identifiers')
    info_parser.add_argument('types', nargs='*', default=['all'],
                             choices=['mac', 'bssid', 'imei', 'all'],
                             help='Types of information to display (default: all)')
    info_parser.add_argument('--verbose', '-v', action='store_true',
                             help='Enable verbose logging')

    # Global arguments for default mode
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate actions without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--interfaces', nargs='+', default=NetworkManager.DEFAULT_INTERFACES,
                        choices=['wan', 'upstream', 'all'],
                        help='Interfaces to randomize (default: wan upstream)')
    parser.add_argument('--no-restart', action='store_true',
                        help='Do not restart network after changes')
    parser.add_argument('--device-index', type=int, default=None,
                        help='Specific device index to use for WAN interface')
    parser.add_argument('--randomize', nargs='+', default=['all'],
                        choices=['mac', 'bssid', 'imei', 'logs', 'all'],
                        help='What to randomize (default: all)')
    parser.add_argument('--no-reboot-imei', action='store_true',
                        help='Do not reboot after IMEI randomization')
    parser.add_argument('--info', nargs='*', default=None,
                        choices=['mac', 'bssid', 'imei', 'all'],
                        help='Display current network identifiers')

    return parser.parse_args()


def process_bssid_randomization(bssid_manager, dry_run, no_restart):
    """
    Process BSSID randomization.

    Args:
        bssid_manager (BssidManager): BSSID manager instance
        dry_run (bool): If True, only simulate actions
        no_restart (bool): If True, do not restart after changes

    Returns:
        bool: True if successful, False otherwise
    """
    logger = Logger()
    logger.info("Randomizing BSSIDs...")

    bssid_success, changes = bssid_manager.set_bssid_for_interfaces(
        dry_run=dry_run)

    if bssid_success and changes and not dry_run and not no_restart:
        bssid_manager.reset_wifi(dry_run=dry_run)

    return bssid_success


def process_mac_randomization(mac_manager, interfaces, device_index, dry_run, no_restart):
    """
    Process MAC address randomization.

    Args:
        mac_manager (MacManager): MAC manager instance
        interfaces (list): Interfaces to randomize
        device_index (int): Specific device index to use
        dry_run (bool): If True, only simulate actions
        no_restart (bool): If True, do not restart after changes

    Returns:
        bool: True if successful, False otherwise
    """
    logger = Logger()
    logger.info("Randomizing MAC addresses...")

    return mac_manager.randomize_mac_addresses(
        interfaces,
        device_index,
        dry_run,
        no_restart
    )


def process_imei_randomization(reboot_after=True):
    """
    Process IMEI randomization.

    Args:
        reboot_after (bool): If True, reboot after changing IMEI

    Returns:
        bool: True if successful, False otherwise
    """
    logger = Logger()
    logger.info("Randomizing IMEI...")

    modem = ModemManager()
    # Generate a valid IMEI
    imei = ImeiGenerator.generate_random_imei()

    # Pass reboot_after parameter
    imei_success = modem.set_imei(imei, reboot_after=reboot_after)

    if not imei_success:
        logger.error("Failed to randomize IMEI")
    elif not reboot_after:
        logger.warning(
            "IMEI has been changed. A manual reboot is required for changes to take effect.")
        logger.warning("You can reboot by running the 'reboot' command.")

    return imei_success


def process_log_wiping(logger, executor, dry_run):
    """
    Process MAC address log wiping with enhanced security.

    Args:
        logger (Logger): Logger instance
        executor (SystemCommand): Command executor instance
        dry_run (bool): If True, only simulate actions

    Returns:
        bool: True if successful, False otherwise
    """
    # Create log manager
    log_manager = LogManager(logger, executor)

    # Run comprehensive wiping
    success = log_manager.wipe_mac_logs(dry_run)

    # Check boot-time security script
    if success and not dry_run:
        init_status = log_manager.check_init_script()
        if not init_status:
            logger.warning(
                "Boot-time security will not persist across reboots. Install script needs to be properly configured.")

    return success


def get_current_bssid_info(verbose=False):
    """
    Get current BSSID information.

    Args:
        verbose (bool): If True, enable verbose logging

    Returns:
        dict: Dictionary with BSSID information
    """
    logger = Logger()
    if verbose:
        logger.logger.setLevel(LogLevel.DEBUG)
    executor = SystemCommand(verbose=verbose)

    bssid_info = {}

    # Get BSSID information using UCI commands
    try:
        # Try to get information for wifi interfaces
        for idx in range(4):  # Check interfaces 0-3
            cmd = f"uci -q get wireless.@wifi-iface[{idx}].macaddr"
            output, code = executor.run_command(cmd)

            if code == 0 and output.strip():
                iface_type_cmd = f"uci -q get wireless.@wifi-iface[{idx}].mode"
                iface_type, _ = executor.run_command(iface_type_cmd)
                iface_type = iface_type.strip() if iface_type else "unknown"

                # Get the device name if available
                dev_cmd = f"uci -q get wireless.@wifi-iface[{idx}].device"
                dev, _ = executor.run_command(dev_cmd)
                dev = dev.strip() if dev else f"wifi{idx}"

                key = f"wlan{idx} ({iface_type} mode on {dev})"
                bssid_info[key] = output.strip()
    except Exception as e:
        logger.error(f"Error getting BSSID information: {e}")

    return bssid_info


def get_current_mac_info():
    """
    Get current MAC address information.

    Returns:
        dict: Dictionary with MAC address information
    """
    executor = SystemCommand()
    network_manager = NetworkManager(executor)

    # Use existing method to get current MAC addresses
    return network_manager.get_current_mac_addresses()


def get_current_imei_info(verbose=False):
    """
    Get current IMEI information.

    Args:
        verbose (bool): If True, enable verbose logging

    Returns:
        dict: Dictionary with IMEI information
    """
    logger = Logger()
    modem = ModemManager(verbose=verbose)
    sim_manager = SimManager(modem, verbose=verbose)

    imei_info = {}

    try:
        # Get IMEI from modem
        imei = modem.get_imei()
        if imei:
            imei_info["Current IMEI"] = imei

            # Check if IMEI is valid
            is_valid = ImeiGenerator.validate_imei(imei)
            imei_info["IMEI Validity"] = "Valid" if is_valid else "Invalid format"

            # Get additional information
            sim_info = sim_manager.fetch_sim_info()
            if sim_info.get("imsi"):
                imei_info["IMSI"] = sim_info["imsi"]
            if sim_info.get("iccid"):
                imei_info["ICCID"] = sim_info["iccid"]

            # Detect SIM type
            sim_type = sim_manager.detect_sim_type()
            if sim_type and sim_type != "unknown":
                imei_info["SIM Type"] = sim_type
    except Exception as e:
        logger.error(f"Error getting IMEI information: {e}")
        imei_info["Error"] = str(e)

    return imei_info


def display_info(info_types, verbose=False):
    """
    Display current network identifiers.

    Args:
        info_types (list): Types of information to display
        verbose (bool): If True, enable verbose logging

    Returns:
        bool: True if successful, False otherwise
    """
    logger = Logger()
    logger.info("Retrieving current network information...")

    if 'all' in info_types:
        info_types = ['mac', 'bssid', 'imei']

    success = True

    # Get and display requested information
    for info_type in info_types:
        logger.info(f"\n=== {info_type.upper()} Information ===")

        if info_type == 'mac':
            mac_info = get_current_mac_info()
            if mac_info:
                for interface, mac in mac_info.items():
                    logger.info(f"{interface}: {mac}")
            else:
                logger.warning("No MAC address information available")
                success = False

        elif info_type == 'bssid':
            bssid_info = get_current_bssid_info(verbose)
            if bssid_info:
                for interface, bssid in bssid_info.items():
                    logger.info(f"{interface}: {bssid}")
            else:
                logger.warning("No BSSID information available")
                success = False

        elif info_type == 'imei':
            imei_info = get_current_imei_info(verbose)
            if imei_info:
                for key, value in imei_info.items():
                    logger.info(f"{key}: {value}")
            else:
                logger.warning("No IMEI information available")
                success = False

    return success


def main():
    """Main function to handle randomization operations."""
    args = parse_arguments()

    # Initialize logger
    logger = Logger()
    if args.verbose:
        logger.logger.setLevel(LogLevel.DEBUG)

    # Handle info command if specified as a subcommand
    if args.command == 'info':
        return 0 if display_info(args.types, args.verbose) else 1

    # Handle --info option for backwards compatibility
    if args.info is not None:
        info_types = args.info
        if not info_types:  # If --info with no arguments
            info_types = ['all']
        return 0 if display_info(info_types, args.verbose) else 1

    # Initialize components needed for randomization operations
    executor = SystemCommand()
    mac_manager = MacManager(executor)
    bssid_manager = BssidManager(verbose=args.verbose)

    # Check if running as root for non-dry-run operations
    if not mac_manager.check_running_as_root() and not args.dry_run:
        logger.error("This script must be run as root")
        return 1

    success = True

    # Process randomizations according to options
    if 'all' in args.randomize:
        args.randomize = ['mac', 'bssid', 'imei', 'logs']

    # Process BSSID randomization if requested
    if 'bssid' in args.randomize:
        bssid_success = process_bssid_randomization(
            bssid_manager, args.dry_run, args.no_restart)
        success = success and bssid_success

    # Process MAC address randomization if requested
    if 'mac' in args.randomize:
        mac_success = process_mac_randomization(
            mac_manager, args.interfaces, args.device_index,
            args.dry_run, args.no_restart)
        success = success and mac_success

    # Process IMEI randomization if requested
    if 'imei' in args.randomize:
        # Use the no_reboot_imei argument to control reboot behavior
        # This prevents automatic reboots when run from boot scripts
        imei_success = process_imei_randomization(
            reboot_after=not args.no_reboot_imei)
        success = success and imei_success

    # Always verify boot-time security is in place
    logger.info("Verifying boot-time security measures...")
    log_manager = LogManager(logger, executor)
    init_status = log_manager.check_init_script()

    if not init_status and not args.dry_run:
        logger.error(
            "SECURITY WARNING: Boot-time protection script not properly installed.")
        logger.error(
            "This is a critical security issue that must be fixed immediately.")
        logger.error(
            "Run the installation script to ensure proper security measures.")

    # Use enhanced log wiping with anti-forensic measures if requested
    if 'logs' in args.randomize:
        logs_success = process_log_wiping(logger, executor, args.dry_run)
        success = success and logs_success

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
