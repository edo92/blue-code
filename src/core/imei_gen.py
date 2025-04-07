#!/usr/bin/env python3

import random


class ImeiGenerator:
    """Generate random valid IMEI numbers."""

    @staticmethod
    def generate_random_imei():
        """
        Generate a random valid IMEI number.

        IMEI numbers are 15 digits long and follow a specific format:
        - First 8 digits: Type Allocation Code (TAC)
        - Next 6 digits: Serial number
        - Last digit: Check digit (calculated using Luhn algorithm)

        Returns:
            str: A valid 15-digit IMEI number
        """
        # Common TACs for popular manufacturers (first 8 digits)
        common_tacs = [
            '35709505',  # Samsung
            '35332910',  # Apple
            '35881505',  # Huawei
            '35925407',  # Xiaomi
            '35411402',  # LG
            '35312706',  # Nokia
            '35844206',  # Motorola
            '35850905',  # Sony
            '35929005',  # Google
        ]

        # Randomly select a TAC or generate a completely random one
        if random.random() < 0.7:  # 70% chance to use common TAC
            tac = random.choice(common_tacs)
        else:
            tac = ''.join(random.choices('0123456789', k=8))

        # Generate serial number (6 digits)
        serial = ''.join(random.choices('0123456789', k=6))

        # Combine TAC and serial
        partial_imei = tac + serial

        # Calculate check digit using Luhn algorithm
        check_digit = ImeiGenerator._calculate_luhn_check_digit(partial_imei)

        # Return complete IMEI
        return partial_imei + str(check_digit)

    @staticmethod
    def _calculate_luhn_check_digit(digits):
        """
        Calculate the Luhn algorithm check digit for a given string of digits.

        Args:
            digits (str): String of digits

        Returns:
            int: Check digit (0-9)
        """
        # Reverse digits and convert to integers
        digits = [int(d) for d in reversed(digits)]

        # Double every second digit
        doubled = [(d * 2) if i % 2 else d for i, d in enumerate(digits)]

        # Sum all digits (if a doubled digit is > 9, sum its individual digits)
        total = sum(d if d < 10 else (d - 9) for d in doubled)

        # Calculate check digit
        check_digit = (10 - (total % 10)) % 10

        return check_digit

    @staticmethod
    def validate_imei(imei):
        """
        Validate if an IMEI is properly formatted and passes the Luhn check.

        Args:
            imei (str): The IMEI to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Check if IMEI is a string of 15 digits
        if not isinstance(imei, str) or not imei.isdigit() or len(imei) != 15:
            return False

        # Check if the check digit is correct
        partial_imei = imei[:-1]
        check_digit = int(imei[-1])
        calculated_check_digit = ImeiGenerator._calculate_luhn_check_digit(
            partial_imei)

        return check_digit == calculated_check_digit
