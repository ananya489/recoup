import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2]),
)

from app.recovery.scoring import compute_recovery_score


NOW = datetime(
    2026,
    8,
    21,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def test_low_value_first_failure_upi_scores_high_priority():
    result = compute_recovery_score(
        amount_paise=99900,
        payment_method="upi",
        failure_event_count=1,
        first_failure_at=NOW - timedelta(hours=1),
        case_status="open",
        now=NOW,
    )

    assert result.score >= 0.7
    assert result.priority == "high"
    assert result.eligible_for_auto_recovery is True
    assert len(result.rationale) >= 2


def test_high_value_transaction_scores_lower():
    result = compute_recovery_score(
        amount_paise=25_00_000,
        payment_method="card",
        failure_event_count=1,
        first_failure_at=NOW - timedelta(hours=1),
        case_status="open",
        now=NOW,
    )

    assert result.score < 0.7

    assert any(
        "high-value" in r
        for r in result.rationale
    )


def test_repeated_failures_reduce_score_and_eligibility():
    result = compute_recovery_score(
        amount_paise=99900,
        payment_method="upi",
        failure_event_count=4,
        first_failure_at=NOW - timedelta(hours=1),
        case_status="open",
        now=NOW,
    )

    assert result.priority == "low"
    assert result.eligible_for_auto_recovery is False


def test_recovery_window_nearly_expired_reduces_score():
    # Current recovery window = 96 hours.
    # 73 hours = ~76% of the window, which crosses
    # the scoring function's >75% threshold.
    result = compute_recovery_score(
        amount_paise=99900,
        payment_method="upi",
        failure_event_count=1,
        first_failure_at=NOW - timedelta(hours=73),
        case_status="open",
        now=NOW,
    )

    assert any(
        "window elapsed" in r
        for r in result.rationale
    )


def test_terminal_case_is_never_eligible_regardless_of_score():
    result = compute_recovery_score(
        amount_paise=99900,
        payment_method="upi",
        failure_event_count=1,
        first_failure_at=NOW - timedelta(hours=1),
        case_status="recovered",
        now=NOW,
    )

    assert result.eligible_for_auto_recovery is False


def test_score_is_always_within_bounds():
    result = compute_recovery_score(
        amount_paise=1,
        payment_method="unknown_method",
        failure_event_count=99,
        first_failure_at=NOW - timedelta(hours=1000),
        case_status="open",
        now=NOW,
    )

    assert 0.0 <= result.score <= 1.0