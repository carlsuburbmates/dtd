"""ATO Modulus 89 ABN (Australian Business Number) Checksum Validator.

Mathematical Specification:
1. An ABN is an 11-digit string.
2. Subtract 1 from the first digit.
3. Multiply each of the 11 digits by its designated ATO weighting factor:
   Weights: [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
4. Sum all 11 products.
5. If sum modulo 89 == 0, the ABN is mathematically valid.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

# Official ATO weighting factors for the 11 digits
ATO_WEIGHTS = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]


def normalize_abn(raw_abn: Optional[str]) -> str:
    """Strip all non-digit characters from an input string."""
    if not raw_abn:
        return ""
    return re.sub(r"\D", "", str(raw_abn).strip())


def format_abn(abn_digits: str) -> str:
    """Format an 11-digit ABN into standard Australian display format: XX XXX XXX XXX."""
    norm = normalize_abn(abn_digits)
    if len(norm) != 11:
        return norm
    return f"{norm[0:2]} {norm[2:5]} {norm[5:8]} {norm[8:11]}"


def validate_abn_checksum(raw_abn: Optional[str]) -> bool:
    """Perform fast boolean ATO Modulus 89 checksum validation."""
    digits_str = normalize_abn(raw_abn)
    if len(digits_str) != 11:
        return False

    digits = [int(c) for c in digits_str]
    # Step 1: Subtract 1 from the first digit
    digits[0] -= 1

    # Step 2: Multiply by weights and sum
    total_sum = sum(d * w for d, w in zip(digits, ATO_WEIGHTS))

    # Step 3: Modulus 89 check
    return (total_sum % 89) == 0


def validate_abn_detailed(raw_abn: Optional[str]) -> Dict[str, Any]:
    """Perform detailed ABN validation with error codes and formatted output."""
    raw_str = str(raw_abn or "").strip()
    if not raw_str:
        return {
            "valid": False,
            "error_code": "EMPTY_INPUT",
            "message": "ABN cannot be empty.",
            "normalized": "",
            "formatted": "",
        }

    norm = normalize_abn(raw_str)

    if len(norm) == 0:
        return {
            "valid": False,
            "error_code": "NO_DIGITS",
            "message": "ABN contains no numeric digits.",
            "normalized": "",
            "formatted": "",
        }

    if len(norm) != 11:
        return {
            "valid": False,
            "error_code": "INVALID_LENGTH",
            "message": f"ABN must be exactly 11 digits (received {len(norm)} digits).",
            "normalized": norm,
            "formatted": norm,
        }

    digits = [int(c) for c in norm]
    digits[0] -= 1
    total_sum = sum(d * w for d, w in zip(digits, ATO_WEIGHTS))
    checksum_ok = (total_sum % 89) == 0

    if not checksum_ok:
        return {
            "valid": False,
            "error_code": "CHECKSUM_FAILED",
            "message": "ABN failed the ATO Modulus 89 checksum algorithm.",
            "normalized": norm,
            "formatted": format_abn(norm),
        }

    return {
        "valid": True,
        "error_code": "OK",
        "message": "ABN passed mathematical checksum validation.",
        "normalized": norm,
        "formatted": format_abn(norm),
    }
