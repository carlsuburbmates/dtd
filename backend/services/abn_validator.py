"""Australian Business Number validation helpers.

The checksum is a local guard only.  A valid checksum does not assert that an
entity exists or is active; that decision belongs to the ABR lookup client.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


ATO_WEIGHTS = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)


def normalize_abn(raw_abn: Optional[str]) -> str:
    return re.sub(r"\D", "", str(raw_abn or "").strip())


def format_abn(raw_abn: Optional[str]) -> str:
    abn = normalize_abn(raw_abn)
    if len(abn) != 11:
        return abn
    return f"{abn[:2]} {abn[2:5]} {abn[5:8]} {abn[8:]}"


def validate_abn_checksum(raw_abn: Optional[str]) -> bool:
    abn = normalize_abn(raw_abn)
    if len(abn) != 11:
        return False
    digits = [int(digit) for digit in abn]
    digits[0] -= 1
    return sum(digit * weight for digit, weight in zip(digits, ATO_WEIGHTS)) % 89 == 0


def validate_abn_detailed(raw_abn: Optional[str]) -> Dict[str, Any]:
    abn = normalize_abn(raw_abn)
    if not str(raw_abn or "").strip():
        code, message = "empty", "ABN is required."
    elif not abn:
        code, message = "no_digits", "ABN must contain digits."
    elif len(abn) != 11:
        code, message = "invalid_length", "ABN must contain exactly 11 digits."
    elif not validate_abn_checksum(abn):
        code, message = "checksum_failed", "ABN did not pass the ATO Modulus 89 check."
    else:
        return {"valid": True, "code": "valid", "abn": abn, "formatted": format_abn(abn), "message": "ABN checksum passed."}
    return {"valid": False, "code": code, "abn": abn, "formatted": format_abn(abn), "message": message}
