#!/usr/bin/env python3

"""
Boot-time security script called by the init script.
Performs MAC and BSSID randomization at system startup.
"""

import sys
import os
import subprocess

# Try running the blue-code command directly if available
try:
    # First check if blue-code is available in PATH
    if subprocess.run(['which', 'blue-code'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE).returncode == 0:
        print("Using installed blue-code command")
        sys.exit(subprocess.run(['blue-code']).returncode)
except Exception as e:
    print(f"Could not run blue-code command: {e}")
    print("Falling back to direct module execution")

# If blue-code command is not available, fall back to direct module execution
# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.bssid import BSSID
from src.core.mac import MacRandomizer
from src.core.log_wiper import LogWiper
from src.core.net import CommandExecutor
from src.lib.logger import Logger


def main():
    """
    Main function to perform boot-time security operations.
    """
    logger = Logger()
    logger.info("Starting boot-time security operations")
    
    # Create executor for commands
    executor = CommandExecutor()
    
    # Randomize MAC addresses
    logger.info("Randomizing MAC addresses")
    mac_randomizer = MacRandomizer(executor)
    mac_success = mac_randomizer.randomize_mac_addresses(
        interfaces=["all"],
        dry_run=False,
        no_restart=True  # Don't restart now, will restart after all changes
    )
    
    # Randomize BSSID
    logger.info("Randomizing BSSIDs")
    bssid_manager = BSSID(verbose=False)
    bssid_success, _ = bssid_manager.set_bssid_for_interfaces(dry_run=False)
    
    # Clean MAC logs
    logger.info("Securing log files and client database")
    log_wiper = LogWiper(logger, executor)
    log_success = log_wiper.wipe_mac_logs(dry_run=False)
    
    # Restart network if any changes were made
    if mac_success or bssid_success:
        logger.info("Restarting network to apply all changes")
        mac_randomizer.network.restart_network(dry_run=False)
        
        # Reset WiFi as well
        if bssid_success:
            bssid_manager.reset_wifi(dry_run=False)
    
    overall_success = mac_success and bssid_success and log_success
    if overall_success:
        logger.info("Boot-time security operations completed successfully")
    else:
        logger.error("Some boot-time security operations failed")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())