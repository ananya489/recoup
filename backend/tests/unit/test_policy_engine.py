from datetime import datetime, timedelta, timezone

from app.models.schemas import RecoveryDecision
from app.policy.engine import evaluate_policy


def make_decision(
    action="retry_later",
    confidence=0.9,
    risk="low",
):
    return RecoveryDecision(
        case_id="case_test",
        failure_category="insufficient_funds",
        confidence=confidence,
        recommended_action=action,
        suggested_retry_window_hours=24,
        reasoning="Test recommendation.",
        risk_level=risk,
        requires_human_approval=False,
        model_name="fake-model",
        prompt_version="v1",
    )


def test_normal_retry_is_approved():
    decision = make_decision(
        action="retry_later"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is True
    assert verdict.final_action == "retry_later"
    assert verdict.reason_code == "OK"


def test_missing_ai_decision_escalates():
    verdict = evaluate_policy(
        decision=None,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "LLM_OUTPUT_INVALID"


def test_low_confidence_escalates():
    decision = make_decision(
        confidence=0.3
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "LOW_CONFIDENCE"


def test_captured_payment_stops_recovery():
    decision = make_decision(
        action="retry_now"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="captured",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "stop"
    assert verdict.reason_code == "ALREADY_PAID"


def test_terminal_case_stops():
    decision = make_decision(
        action="retry_now"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="recovered",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "stop"
    assert verdict.reason_code == "CASE_ALREADY_TERMINAL"


def test_retry_limit_escalates():
    decision = make_decision(
        action="retry_now"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=4,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "MAX_RETRIES_HIT"


def test_high_value_payment_requires_human():
    decision = make_decision(
        action="retry_later"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=2_500_000,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "HIGH_VALUE_REQUIRES_HUMAN"


def test_high_risk_recommendation_requires_human():
    decision = make_decision(
        action="retry_later",
        risk="high",
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "LLM_FLAGGED_HIGH_RISK"


def test_action_in_flight_stops_new_action():
    decision = make_decision(
        action="retry_now"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
        has_action_in_flight=True,
    )

    assert verdict.approved is False
    assert verdict.final_action == "stop"
    assert verdict.reason_code == "DUPLICATE_ACTION_IN_FLIGHT"


def test_cooldown_blocks_new_action():
    decision = make_decision(
        action="retry_later"
    )

    recent_action = datetime.now(timezone.utc) - timedelta(
        hours=2
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
        last_action_at=recent_action,
    )

    assert verdict.approved is False
    assert verdict.final_action == "stop"
    assert verdict.reason_code == "COOLDOWN_ACTIVE"


def test_expired_recovery_window_stops():
    decision = make_decision(
        action="retry_later"
    )

    old_failure = datetime.now(timezone.utc) - timedelta(
        hours=100
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=old_failure,
    )

    assert verdict.approved is False
    assert verdict.final_action == "stop"
    assert verdict.reason_code == "RECOVERY_WINDOW_EXPIRED"


def test_amount_above_auto_ceiling_requires_human():
    decision = make_decision(
        action="retry_later"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=600_000,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is False
    assert verdict.final_action == "escalate_to_human"
    assert verdict.reason_code == "AMOUNT_EXCEEDS_AUTO_CEILING"


def test_valid_recommendation_passes_policy():
    decision = make_decision(
        action="send_payment_link"
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id="case_test",
        case_status="open",
        amount_paise=99900,
        payment_status="failed",
        failure_event_count=1,
        first_failure_at=datetime.now(timezone.utc),
    )

    assert verdict.approved is True
    assert verdict.final_action == "send_payment_link"
    assert verdict.reason_code == "OK"