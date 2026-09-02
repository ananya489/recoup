from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.models.schemas import (
    PolicyVerdict,
    RecommendedAction,
    RecoveryDecision,
)


POLICY_VERSION = "v1"

# Above this amount, autonomous recovery is never allowed.
# ₹20,000 = 2,000,000 paise.
HIGH_VALUE_ESCALATION_PAISE = 2_000_000

# These states mean the case is already finished.
TERMINAL_CASE_STATUSES = {
    "recovered",
    "stopped",
    "escalated",
    "expired",
}

# Prevent repeated actions too close together.
COOLDOWN_HOURS_BETWEEN_ACTIONS = 6


def evaluate_policy(
    decision: Optional[RecoveryDecision],
    case_id: str,
    case_status: str,
    amount_paise: int,
    payment_status: str,
    failure_event_count: int,
    first_failure_at: Optional[datetime],
    last_action_at: Optional[datetime] = None,
    has_action_in_flight: bool = False,
    now: Optional[datetime] = None,
) -> PolicyVerdict:
    """
    Deterministic policy engine.

    This function:
    - does NOT call the database
    - does NOT call an LLM
    - does NOT make network requests

    It only evaluates explicit inputs and decides whether
    the proposed recovery action is allowed.
    """

    now = now or datetime.now(timezone.utc)

    decision_id = "none"

    if decision is not None:
        decision_id = (
            f"{decision.case_id}:"
            f"{decision.model_name}:"
            f"{decision.prompt_version}"
        )

    def verdict(
        reason_code: str,
        final_action: RecommendedAction,
    ) -> PolicyVerdict:

        approved = (
            decision is not None
            and final_action == decision.recommended_action
        )

        return PolicyVerdict(
            case_id=case_id,
            decision_id=decision_id,
            approved=approved,
            reason_code=reason_code,
            final_action=final_action,
            policy_version=POLICY_VERSION,
        )

    # 1. Terminal case.
    if case_status in TERMINAL_CASE_STATUSES:
        return verdict(
            "CASE_ALREADY_TERMINAL",
            RecommendedAction.stop,
        )

    # 2. Payment already succeeded.
    if payment_status == "captured":
        return verdict(
            "ALREADY_PAID",
            RecommendedAction.stop,
        )

    # 3. Recovery window expired.
    if first_failure_at is not None:

        hours_since_failure = (
            now - first_failure_at
        ).total_seconds() / 3600

        if hours_since_failure > settings.recovery_window_hours:
            return verdict(
                "RECOVERY_WINDOW_EXPIRED",
                RecommendedAction.stop,
            )

    # 4. Maximum failure/retry count.
    if failure_event_count > settings.recovery_max_retries:
        return verdict(
            "MAX_RETRIES_HIT",
            RecommendedAction.escalate_to_human,
        )

    # 5. Action already running.
    if has_action_in_flight:
        return verdict(
            "DUPLICATE_ACTION_IN_FLIGHT",
            RecommendedAction.stop,
        )

    # 6. Cooldown between actions.
    if last_action_at is not None:

        hours_since_action = (
            now - last_action_at
        ).total_seconds() / 3600

        if hours_since_action < COOLDOWN_HOURS_BETWEEN_ACTIONS:
            return verdict(
                "COOLDOWN_ACTIVE",
                RecommendedAction.stop,
            )

    # 7. Missing or invalid AI decision.
    if decision is None:
        return verdict(
            "LLM_OUTPUT_INVALID",
            RecommendedAction.escalate_to_human,
        )

    # 8. Low confidence.
    if decision.confidence < 0.5:
        return verdict(
            "LOW_CONFIDENCE",
            RecommendedAction.escalate_to_human,
        )

    # 9. Absolute high-value protection.
    if amount_paise > HIGH_VALUE_ESCALATION_PAISE:
        return verdict(
            "HIGH_VALUE_REQUIRES_HUMAN",
            RecommendedAction.escalate_to_human,
        )

    # 10. Configured autonomous approval ceiling.
    if (
        amount_paise
        > settings.recovery_auto_approval_limit_paise
        and decision.recommended_action
        != RecommendedAction.escalate_to_human
    ):
        return verdict(
            "AMOUNT_EXCEEDS_AUTO_CEILING",
            RecommendedAction.escalate_to_human,
        )

    # 11. AI itself says the case is high risk.
    if decision.risk_level == "high":
        return verdict(
            "LLM_FLAGGED_HIGH_RISK",
            RecommendedAction.escalate_to_human,
        )

    # 12. Nothing blocked the recommendation.
    return verdict(
        "OK",
        decision.recommended_action,
    )