import re
from typing import Optional

def calculate_check_digit(digits: str) -> int:
    """
    Calculates the standard GS1/EAN/UPC modulo 10 check digit.
    Weights alternate 3 and 1 from right to left (excluding check digit position).
    """
    total = 0
    # From right to left of the payload (excluding check digit)
    reverse_digits = digits[::-1]
    for i, char in enumerate(reverse_digits):
        weight = 3 if i % 2 == 0 else 1
        total += int(char) * weight
    return (10 - (total % 10)) % 10


def validate_check_digit(digits: str) -> bool:
    """Validates the check digit of a numeric UPC/EAN code."""
    if not digits.isdigit():
        return False
    payload = digits[:-1]
    expected_check = calculate_check_digit(payload)
    return int(digits[-1]) == expected_check


def normalize_upc(code: Optional[str]) -> str:
    """
    Normalizes and validates a UPC/EAN/GTIN code:
    1. Strips spaces, dashes, dots.
    2. Validates that it is strictly numeric.
    3. Validates length (must be 8, 12, 13, or 14 digits).
    4. Validates the GS1 modulo 10 check digit.
    5. Normalizes UPC-A (12 digits) and EAN-13 (13 digits starting with '0')
       equivalents into the same canonical 13-digit EAN representation
       (e.g., '012345678905' -> '0012345678905').

    Raises ValueError with a clear explanation if malformed or invalid check digit.
    """
    if not code:
        raise ValueError("UPC code cannot be empty")

    cleaned = re.sub(r"[\s\-\.]+", "", str(code).strip())

    if not cleaned.isdigit():
        raise ValueError(f"Malformed UPC/EAN '{code}': code must contain only numeric digits")

    length = len(cleaned)
    if length not in (8, 12, 13, 14):
        raise ValueError(
            f"Malformed UPC/EAN '{code}': invalid length {length} (must be 8, 12, 13, or 14 digits)"
        )

    if not validate_check_digit(cleaned):
        expected = calculate_check_digit(cleaned[:-1])
        raise ValueError(
            f"Malformed UPC/EAN '{code}': invalid check digit (provided {cleaned[-1]}, expected {expected})"
        )

    # Treat UPC-A (12 digits) and EAN-13 equivalents (13 digits starting with 0) as the same code:
    # Standardize to 13 digits (EAN-13 canonical form)
    if length == 12:
        return "0" + cleaned
    elif length == 14 and cleaned.startswith("0"):
        # If 14-digit GTIN starting with 0, check if 13-digit equivalent
        return cleaned[1:]

    return cleaned
