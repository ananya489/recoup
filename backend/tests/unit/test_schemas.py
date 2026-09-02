import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.models.schemas import (  # noqa: E402
    RecoveryDecision,
    PolicyVerdict,
    Payment,
    Customer,
    RecoveryCase,
)


def test_valid_recovery_decision():
    d = RecoveryDecision(
        case_id="case_1",
        failure_category="insufficient_funds",
        confidence=0.91,
        recommended_action="retry_later",
        suggested_retry_window_hours=30,
        reasoning="UPI insufficient-balance failures typically resolve after next inflow cycle.",
        risk_level="low",
        requires_human_approval=False,
        model_name="claude-sonnet-4-6",
        prompt_version="v1",
    )
    assert d.confidence == 0.91
    assert d.recommended_action == "retry_later"


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        RecoveryDecision(
            case_id="case_1", failure_category="insufficient_funds",
            confidence=1.4, recommended_action="retry_later",
            reasoning="bad confidence", risk_level="low",
            requires_human_approval=False, model_name="x", prompt_version="v1",
        )


def test_invalid_failure_category_rejected():
    with pytest.raises(ValidationError):
        RecoveryDecision(
            case_id="case_1", failure_category="not_a_real_category",
            confidence=0.5, recommended_action="retry_later",
            reasoning="bad category", risk_level="low",
            requires_human_approval=False, model_name="x", prompt_version="v1",
        )


def test_policy_verdict_valid():
    v = PolicyVerdict(
        case_id="case_1", decision_id="dec_1", approved=True,
        reason_code="OK", final_action="retry_later", policy_version="v1",
    )
    assert v.approved is True


def test_payment_amount_must_be_positive():
    with pytest.raises(ValidationError):
        Payment(id="pay_1", customer_id="cust_1", amount_paise=0, method="upi", status="failed")


def test_customer_valid():
    c = Customer(
        id="cust_1", name="Rohan Mehra", email="rohan@example.com",
        contact="+919900011122", account_age_days=240, ltv_paise=899100,
        prior_failures_90d=1, prior_chargebacks=0, segment="d2c_subscription",
    )
    assert c.prior_failures_90d == 1


def test_recovery_case_default_status_is_open():
    case = RecoveryCase(id="case_1", payment_id="pay_1", customer_id="cust_1", amount_paise=99900)
    assert case.status == "open"
    assert case.auto_retry_count == 0