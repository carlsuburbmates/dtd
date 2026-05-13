from __future__ import annotations

import pytest

from services.claim_state import evaluate_claim


@pytest.mark.parametrize("state", ["STATE_0", "STATE_1"])
def test_melbourne_wide_blocked_below_state_2_in_block_mode(state):
    result = evaluate_claim(
        text="We service Melbourne-wide",
        state=state,
        enforcement_mode="block_invalid",
        block_melbourne_wide_below_state_2=True,
        enabled=True,
    )

    assert result["enabled"] is True
    assert result["classification"]["is_melbourne_wide"] is True
    assert result["blocked"] is True
    assert result["allowed"] is False
    assert result["decision"] == "block"
    assert "MELBOURNE_WIDE_BELOW_STATE_2" in result["reason_codes"]


@pytest.mark.parametrize("state", ["STATE_2", "STATE_3", "STATE_4"])
def test_melbourne_wide_allowed_at_state_2_and_above(state):
    result = evaluate_claim(
        text="Available across Melbourne",
        state=state,
        enforcement_mode="block_invalid",
        block_melbourne_wide_below_state_2=True,
        enabled=True,
    )

    assert result["classification"]["is_melbourne_wide"] is True
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"] == []


def test_report_only_mode_never_blocks_but_flags_violation():
    result = evaluate_claim(
        text="We offer services throughout Melbourne",
        state="STATE_0",
        enforcement_mode="report_only",
        block_melbourne_wide_below_state_2=True,
        enabled=True,
    )

    assert result["classification"]["is_melbourne_wide"] is True
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"][0]["code"] == "MELBOURNE_WIDE_BELOW_STATE_2"
    assert "CLAIM_POLICY_REPORT_ONLY" in result["reason_codes"]


def test_disabled_mode_is_safe_noop_allow():
    result = evaluate_claim(
        text="We service Melbourne-wide",
        state="STATE_0",
        enforcement_mode="block_invalid",
        block_melbourne_wide_below_state_2=True,
        enabled=False,
    )

    assert result["enabled"] is False
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"] == []
    assert "CLAIM_STATE_MODEL_DISABLED" in result["reason_codes"]


def test_non_target_text_is_deterministically_allowed():
    result = evaluate_claim(
        text="Private in-home training in Carlton",
        state="STATE_0",
        enforcement_mode="block_invalid",
        block_melbourne_wide_below_state_2=True,
        enabled=True,
    )

    assert result["classification"]["is_melbourne_wide"] is False
    assert result["classification"]["matched_tokens"] == []
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["decision"] == "allow"
    assert result["violations"] == []
