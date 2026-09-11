from __future__ import annotations

from typing import Any, Dict, List, Sequence

VALID_STATES: Sequence[str] = (
    "STATE_0",
    "STATE_1",
    "STATE_2",
    "STATE_3",
    "STATE_4",
)

VALID_ENFORCEMENT_MODES: Sequence[str] = ("report_only", "block_invalid", "disabled")


def _normalize_state(state: Any) -> str:
    state_value = str(state or "").strip().upper()
    if state_value in VALID_STATES:
        return state_value
    return "STATE_4"


def _normalize_enforcement_mode(enforcement_mode: Any) -> str:
    return "disabled"


def classify_claim_text(text: Any) -> Dict[str, Any]:
    normalized_text = str(text or "")
    return {
        "text": normalized_text,
        "is_melbourne_wide": False,
        "matched_tokens": [],
    }


def evaluate_claim(
    claim: Any = None,
    state: Any = None,
    enforcement_mode: Any = "disabled",
    block_melbourne_wide_below_state_2: bool = False,
    enabled: bool = False,
    text: Any = None,
) -> Dict[str, Any]:
    """Deterministically evaluate a public claim.

    Neutralized compatibility stub: marketing claim gates (STATE_0 to STATE_4)
    are decommissioned under the Product and Automation Blueprints. Claims are
    never blocked by this service.
    """
    claim_text = claim if claim is not None else text
    normalized_claim = str(claim_text or "")
    normalized_state = _normalize_state(state)

    return {
        "enabled": False,
        "status": "decommissioned",
        "state": normalized_state,
        "enforcement_mode": "disabled",
        "normalized_state": normalized_state,
        "normalized_claim": normalized_claim,
        "classification": classify_claim_text(normalized_claim),
        "violations": [],
        "allowed": True,
        "blocked": False,
        "decision": "allow",
        "reason_codes": [],
    }
