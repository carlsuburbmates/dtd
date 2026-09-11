from __future__ import annotations

import pytest

from services.claim_state import evaluate_claim, classify_claim_text


@pytest.mark.parametrize("state", ["STATE_0", "STATE_1", "STATE_2", "STATE_3", "STATE_4"])
@pytest.mark.parametrize("mode", ["block_invalid", "report_only", "disabled"])
def test_evaluate_claim_never_blocks_regardless_of_state_or_mode(state, mode):
    result = evaluate_claim(
        text="We service Melbourne-wide",
        state=state,
        enforcement_mode=mode,
        block_melbourne_wide_below_state_2=True,
        enabled=True,
    )

    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"] == []
    assert result["status"] == "decommissioned"


def test_classify_claim_text_is_neutral():
    classification = classify_claim_text("Available Melbourne-wide and across Melbourne")
    assert classification["is_melbourne_wide"] is False
    assert classification["matched_tokens"] == []


def test_evaluate_claim_defaults_safe_allow():
    result = evaluate_claim(claim="Dog training in Carlton")
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"] == []
