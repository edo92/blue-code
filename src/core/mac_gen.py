#!/usr/bin/env python3

import random


class MacAddressGenerator:
    """Generate random MAC addresses with appropriate properties."""

    @staticmethod
    def generate_unicast_mac():
        """
        Generate a random unicast MAC address with the locally administered bit set.

        Returns:
            str: A properly formatted unicast MAC address with colons
        """
        # Generate a random 48-bit number (6 bytes) for the MAC address
        mac_int = random.randint(0, 2**48 - 1)

        # Ensure it's a unicast address by clearing the multicast bit (least significant bit of first byte)
        mac_int &= 0xFEFFFFFFFFFF

        # Set the locally administered bit (bit 1) to 1
        mac_int |= 0x020000000000

        # Convert to hexadecimal and format with colons
        mac_hex = format(mac_int, '012x')
        mac_formatted = ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))

        return mac_formatted
