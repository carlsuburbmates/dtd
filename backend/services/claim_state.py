from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

VALID_STATES: Sequence[str] = (
    "STATE_0",
    "STATE_1",
    "STATE_2",
    "STATE_3",
    "STATE_4",
)

VALID_ENFORCEMENT_MODES: Sequence[str] = ("report_only", "block_invalid")

_MELBOURNE_WIDE_PATTERNS: Sequence[tuple[str, re.Pattern[str]]] = (
    (
        "melbourne-wide",
        re.compile(r"\bmelbourne\s*[- ]\s*wide\b", flags=re.IGNORECASE),
    ),
    (
        "across melbourne",
        re.compile(r"\bacross\s+melbourne\b", flags=re.IGNORECASE),
    ),
    (
        "all melbourne",
        re.compile(r"\ball\s+melbourne\b", flags=re.IGNORECASE),
    ),
    (
        "throughout melbourne",
        re.compile(r"\bthroughout\s+melbourne\b", flags=re.IGNORECASE),
    ),
)


def _normalize_state(state: Any) -> str:
    state_value = str(state or "").strip().upper()
    if state_value in VALID_STATES:
        return state_value
    return "STATE_0"


def _normalize_enforcement_mode(enforcement_mode: Any) -> str:
    mode = str(enforcement_mode or "").strip().lower()
    if mode in VALID_ENFORCEMENT_MODES:
        return mode
    return "report_only"


def classify_claim_text(text: Any) -> Dict[str, Any]:
    normalized_text = str(text or "")
    matched_tokens: List[str] = []

    for token, pattern in _MELBOURNE_WIDE_PATTERNS:
        if pattern.search(normalized_text):
            matched_tokens.append(token)

    return {
        "text": normalized_text,
        "is_melbourne_wide": bool(matched_tokens),
        "matched_tokens": matched_tokens,
    }


def evaluate_claim(
    claim: Any = None,
    state: Any = None,
    enforcement_mode: Any = "report_only",
    block_melbourne_wide_below_state_2: bool = True,
    enabled: bool = False,
    text: Any = None,
) -> Dict[str, Any]:
    """Deterministically evaluate a public claim against state-gated rules.

    Returns a structured decision payload suitable for server integration/audit logs.
    """

    claim_text = claim if claim is not None else text
    normalized_state = _normalize_state(state)
    normalized_mode = _normalize_enforcement_mode(enforcement_mode)
    classification = classify_claim_text(claim_text)

    result: Dict[str, Any] = {
        "enabled": bool(enabled),
        "state": normalized_state,
        "enforcement_mode": normalized_mode,
        "normalized_state": normalized_state,
        "normalized_claim": str(claim_text or ""),
        "classification": classification,
        "violations": [],
        "allowed": True,
        "blocked": False,
        "decision": "allow",
        "reason_codes": [],
    }

    if not enabled:
        result["reason_codes"].append("CLAIM_STATE_MODEL_DISABLED")
        return result

    melbourne_wide_violation = (
        classification["is_melbourne_wide"]
        and bool(block_melbourne_wide_below_state_2)
        and normalized_state in {"STATE_0", "STATE_1"}
    )

    if melbourne_wide_violation:
        result["violations"].append(
            {
                "code": "MELBOURNE_WIDE_BELOW_STATE_2",
                "message": "Melbourne-wide claim is blocked below STATE_2.",
            }
        )
        result["reason_codes"].append("MELBOURNE_WIDE_BELOW_STATE_2")

        if normalized_mode == "block_invalid":
            result["allowed"] = False
            result["blocked"] = True
            result["decision"] = "block"
        else:
            result["reason_codes"].append("CLAIM_POLICY_REPORT_ONLY")

    return result
