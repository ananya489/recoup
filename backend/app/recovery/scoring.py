from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.policy.engine import (
    HIGH_VALUE_ESCALATION_PAISE,
    TERMINAL_CASE_STATUSES,
)


class RecoveryScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    priority: str
    eligible_for_auto_recovery: bool
    rationale: List[str]


def compute_recovery_score(
    amount_paise: int,
    payment_method: Optional[str],
    failure_event_count: int,
    first_failure_at: Optional[datetime],
    case_status: str,
    now: Optional[datetime] = None,
) -> RecoveryScore:
    """
    Deterministic and explainable recovery score.

    This is NOT machine learning.
    """

    now = now or datetime.now(timezone.utc)

    score = 0.5
    rationale: List[str] = []

    # UPI and netbanking are treated as relatively recoverable
    # in this heuristic.
    if payment_method in ("upi", "netbanking"):
        score += 0.1
        rationale.append(
            f"+0.10 payment_method={payment_method}"
        )

    # First failure gets a positive score.
    if failure_event_count <= 1:
        score += 0.2
        rationale.append(
            "+0.20 first failure, no prior retry history"
        )

    # Repeated failures reduce the score.
    elif failure_event_count >= 3:
        score -= 0.3
        rationale.append(
            f"-0.30 failure_event_count={failure_event_count}"
        )

    # Reduce score if most of the recovery window has elapsed.
    if (
        first_failure_at is not None
        and settings.recovery_window_hours
    ):
        hours_elapsed = (
            now - first_failure_at
        ).total_seconds() / 3600

        window_fraction_used = (
            hours_elapsed / settings.recovery_window_hours
        )

        if window_fraction_used > 0.75:
            score -= 0.15
            rationale.append(
                f"-0.15 {window_fraction_used:.0%} "
                "of recovery window elapsed"
            )

    # High-value transactions are more restricted.
    if amount_paise > HIGH_VALUE_ESCALATION_PAISE:
        score -= 0.2
        rationale.append(
            "-0.20 amount exceeds high-value threshold"
        )

    # Keep score inside [0, 1].
    score = max(0.0, min(1.0, score))

    # Convert score to priority.
    if score >= 0.7:
        priority = "high"
    elif score >= 0.4:
        priority = "medium"
    else:
        priority = "low"

    # Determine whether automatic recovery is allowed to proceed
    # to later policy evaluation.
    eligible = (
        score >= 0.4
        and case_status not in TERMINAL_CASE_STATUSES
        and failure_event_count <= settings.recovery_max_retries
    )

    if not eligible:
        rationale.append(
            "not eligible for auto-recovery "
            "given current score/state"
        )

    return RecoveryScore(
        score=round(score, 3),
        priority=priority,
        eligible_for_auto_recovery=eligible,
        rationale=rationale,
    )