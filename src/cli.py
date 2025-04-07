import sys
import argparse
from core.bssid import BSSIDManager
from core.imei_gen import ImeiGenerator
from core.log_wiper import LogWiper
from core.mac import MacRandomizer
from core.modem import ModemController
from core.net import CommandExecutor, NetworkConfigurator
from lib.logger import Logger


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


def main():
    args = parse_arguments()

    logger = Logger()
    executor = CommandExecutor()

    # Initialize managers for different components
    mac_randomizer = MacRandomizer(executor)
    bssid_manager = BSSIDManager()

    # Check if running as root for non-dry-run operations
    if not mac_randomizer.check_running_as_root() and not args.dry_run:
        logger.error("This script must be run as root")
        return 1

    success = True

    # Process BSSID randomization if requested
    if 'bssid' in args.randomize:
        logger.info("Randomizing BSSIDs...")
        bssid_success, changes = bssid_manager.set_bssid_for_interfaces(
            dry_run=args.dry_run)

        if bssid_success and changes and not args.dry_run and not args.no_restart:
            bssid_manager.reset_wifi(dry_run=args.dry_run)

        success = success and bssid_success

    # Process MAC address randomization if requested
    if any(iface in args.randomize for iface in ['mac', 'all']):
        logger.info("Randomizing MAC addresses...")
        mac_success = mac_randomizer.randomize_mac_addresses(
            args.interfaces,
            args.device_index,
            args.dry_run,
            args.no_restart
        )
        success = success and mac_success

    # Process IMEI randomization if requested
    if 'imei' in args.randomize:
        logger.info("Randomizing IMEI...")
        modem = ModemController()
        # Generate a valid IMEI
        imei = ImeiGenerator.generate_random_imei()

        imei_success = modem.set_imei(imei)
        if imei_success:
            logger.info(f"IMEI successfully randomized to: {imei}")
        else:
            logger.error("Failed to randomize IMEI")
            success = False

    # Wipe MAC address logs if requested
    if 'logs' in args.randomize:
        logger.info("Wiping MAC address logs...")
        wiper = LogWiper(logger, executor)
        logs_success = wiper.wipe_mac_logs(args.dry_run)
        success = success and logs_success

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
