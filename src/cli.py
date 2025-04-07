
import sys
import argparse
from core.bssid import BSSID
from core.imei_gen import ImeiGenerator
from core.log_wiper import LogWiper
from core.mac import MacRandomizer
from core.modem import ModemController
from core.net import CommandExecutor, NetworkConfigurator
from lib.logger import Logger, LogLevel


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Randomize network identifiers for GL-iNet devices'
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
    parser.add_argument('--randomize', nargs='+', default=['mac'],
                        choices=['mac', 'bssid', 'imei', 'logs', 'all'],
                        help='What to randomize (default: mac)')

    return parser.parse_args()


def process_bssid_randomization(bssid_manager, dry_run, no_restart):
    """
    Process BSSID randomization.

    Args:
        bssid_manager (BSSIDManager): BSSID manager instance
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


def process_mac_randomization(mac_randomizer, interfaces, device_index, dry_run, no_restart):
    """
    Process MAC address randomization.

    Args:
        mac_randomizer (MacRandomizer): MAC randomizer instance
        interfaces (list): Interfaces to randomize
        device_index (int): Specific device index to use
        dry_run (bool): If True, only simulate actions
        no_restart (bool): If True, do not restart after changes

    Returns:
        bool: True if successful, False otherwise
    """
    logger = Logger()
    logger.info("Randomizing MAC addresses...")

    return mac_randomizer.randomize_mac_addresses(
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

    modem = ModemController()
    # Generate a valid IMEI
    imei = ImeiGenerator.generate_random_imei()

    # Pass reboot_after parameter
    imei_success = modem.set_imei(imei, reboot_after=reboot_after)

    if not imei_success:
        logger.error("Failed to randomize IMEI")

    return imei_success


def process_log_wiping(logger, executor, dry_run):
    """
    Process MAC address log wiping.

    Args:
        logger (Logger): Logger instance
        executor (CommandExecutor): Command executor instance
        dry_run (bool): If True, only simulate actions

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Wiping MAC address logs...")
    wiper = LogWiper(logger, executor)
    return wiper.wipe_mac_logs(dry_run)


def main():
    """Main function to handle randomization operations."""
    args = parse_arguments()

    # Initialize required components
    logger = Logger()
    if args.verbose:
        logger.logger.setLevel(LogLevel.DEBUG)

    executor = CommandExecutor()
    mac_randomizer = MacRandomizer(executor)
    bssid_manager = BSSID(verbose=args.verbose)

    # Check if running as root for non-dry-run operations
    if not mac_randomizer.check_running_as_root() and not args.dry_run:
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
            mac_randomizer, args.interfaces, args.device_index,
            args.dry_run, args.no_restart)
        success = success and mac_success

    # Process IMEI randomization if requested
    if 'imei' in args.randomize:
        imei_success = process_imei_randomization(reboot_after=True)
        success = success and imei_success

    # Wipe MAC address logs if requested
    if 'logs' in args.randomize:
        logs_success = process_log_wiping(logger, executor, args.dry_run)
        success = success and logs_success

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
