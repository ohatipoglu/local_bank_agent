"""
Turkish TC Kimlik (T.C. Identification Number) validation.
Implements the official checksum algorithm used by the Turkish government.

TC Kimlik Number Format:
- 11 digits total
- First digit cannot be 0
- 10th digit = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) % 10
- 11th digit = (d1+d2+d3+d4+d5+d6+d7+d8+d9+d10) % 10
"""


def validate_tc_kimlik(tc_number: str) -> bool:
    """
    Validate a Turkish TC Kimlik number using the official algorithm.

    The algorithm checks:
    1. Must be exactly 11 digits
    2. First digit cannot be 0
    3. 10th digit checksum: ((odd_positions_sum * 7) - even_positions_sum) % 10
    4. 11th digit checksum: total_sum % 10

    Args:
        tc_number: 11-digit TC Kimlik number as string

    Returns:
        True if valid TC Kimlik number, False otherwise

    Examples:
        >>> validate_tc_kimlik("12345678901")  # Mock test number
        False  # Not a real valid number per algorithm
        >>> validate_tc_kimlik("10000000146")  # Known valid number
        True
    """
    # Check format: must be exactly 11 digits
    if not tc_number or len(tc_number) != 11 or not tc_number.isdigit():
        return False

    # Convert to list of integers
    digits = [int(d) for d in tc_number]

    # First digit cannot be 0
    if digits[0] == 0:
        return False

    # Calculate checksum for 10th digit
    # Odd positions (1st, 3rd, 5th, 7th, 9th) = indices 0, 2, 4, 6, 8
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    # Even positions (2nd, 4th, 6th, 8th) = indices 1, 3, 5, 7
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]

    expected_10th = ((odd_sum * 7) - even_sum) % 10

    if digits[9] != expected_10th:
        return False

    # Calculate checksum for 11th digit
    total_sum = sum(digits[:10])
    expected_11th = total_sum % 10

    if digits[10] != expected_11th:
        return False

    return True


def generate_valid_tc_kimlik(first_name: str = "Test", last_name: str = "User") -> str:
    """
    Generate a valid TC Kimlik number for testing purposes.

    Uses a deterministic algorithm based on name hash to generate
    consistent test numbers.

    Args:
        first_name: First name for seed
        last_name: Last name for seed

    Returns:
        A valid 11-digit TC Kimlik number
    """
    import hashlib

    # Generate a deterministic seed from names
    seed_str = f"{first_name}{last_name}"
    seed_hash = hashlib.md5(seed_str.encode()).hexdigest()
    seed = int(seed_hash[:8], 16)

    # Generate first 9 digits (ensure first digit is not 0)
    base = (seed % 900000000) + 100000000  # Range: 100000000 - 999999999
    first_9 = str(base)

    # Calculate 10th digit
    digits = [int(d) for d in first_9]
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    digit_10 = ((odd_sum * 7) - even_sum) % 10

    # Calculate 11th digit
    total_sum = sum(digits) + digit_10
    digit_11 = total_sum % 10

    return f"{first_9}{digit_10}{digit_11}"
