from typing import List

from app.models.schemas import RecoveryDecision
from app.config import settings
from app.policy.engine import HIGH_VALUE_ESCALATION_PAISE

# This is NOT a real LLM.
# It is a deterministic evaluation stand-in.
_ACTION_BY_CATEGORY = {
    "insufficient_funds": "retry_later",
    "bank_timeout": "retry_now",
    "gateway_or_network_error": "retry_now",
    "invalid_card_or_expired": "send_payment_link",
    "otp_or_auth_failure": "retry_now",
    "mandate_cancelled": "escalate_to_human",
    "suspected_fraud_block": "escalate_to_human",
    "unknown": "escalate_to_human",
}


_CONFIDENCE_BY_CATEGORY = {
    "insufficient_funds": 0.85,
    "bank_timeout": 0.80,
    "gateway_or_network_error": 0.75,
    "invalid_card_or_expired": 0.80,
    "otp_or_auth_failure": 0.70,
    "mandate_cancelled": 0.90,
    "suspected_fraud_block": 0.60,
    "unknown": 0.40,
}


_RISK_BY_CATEGORY = {
    "suspected_fraud_block": "high",
    "mandate_cancelled": "medium",
    "unknown": "medium",
}


def simulate_ai_recommendation(
    record: dict,
) -> RecoveryDecision:
    """
    Deterministic stand-in for an AI recommendation.

    This does NOT call a real LLM.
    """

    category = record[
        "failure_category"
    ]

    action = _ACTION_BY_CATEGORY.get(
        category,
        "escalate_to_human",
    )

    return RecoveryDecision(
        case_id=record["case_id"],
        failure_category=category,
        confidence=_CONFIDENCE_BY_CATEGORY.get(
            category,
            0.5,
        ),
        recommended_action=action,
        suggested_retry_window_hours=24,
        reasoning=(
            "evaluation stand-in recommendation "
            f"for category={category}"
        ),
        risk_level=_RISK_BY_CATEGORY.get(
            category,
            "low",
        ),
        requires_human_approval=(
            action == "escalate_to_human"
        ),
        model_name=(
            "eval-stand-in-not-a-real-llm"
        ),
        prompt_version="eval-v1",
    )


def evaluate_case(
    record: dict,
    action: str,
) -> dict:
    """
    Simulate whether the chosen action recovers
    the payment.
    """

    if action in (
        "stop",
        "escalate_to_human",
    ):
        recovered = record[
            "simulated_recovers_if_ignored"
        ]
    else:
        recovered = record[
            "simulated_recovers_if_nudged"
        ]

    amount_recovered_paise = (
        record["amount_paise"]
        if recovered
        else 0
    )

    unnecessary_intervention = (
        not record[
            "ground_truth_recoverable"
        ]
        and action
        not in (
            "stop",
            "escalate_to_human",
        )
    )

    return {
        "case_id": record["case_id"],
        "action": action,
        "recovered": recovered,
        "amount_recovered_paise": (
            amount_recovered_paise
        ),
        "unnecessary_intervention": (
            unnecessary_intervention
        ),
        "escalated": (
            action == "escalate_to_human"
        ),
        "stopped": (
            action == "stop"
        ),
    }


def compute_metrics(
    outcomes: List[dict],
    revenue_at_risk_paise: int,
) -> dict:
    """
    Calculate evaluation metrics.
    """

    n = len(outcomes)

    recovered_count = sum(
        1
        for outcome in outcomes
        if outcome["recovered"]
    )

    revenue_recovered_paise = sum(
        outcome["amount_recovered_paise"]
        for outcome in outcomes
    )

    unnecessary = sum(
        1
        for outcome in outcomes
        if outcome[
            "unnecessary_intervention"
        ]
    )

    escalations = sum(
        1
        for outcome in outcomes
        if outcome["escalated"]
    )

    stops = sum(
        1
        for outcome in outcomes
        if outcome["stopped"]
    )

    interventions = sum(
        1
        for outcome in outcomes
        if outcome["action"]
        not in (
            "stop",
            "escalate_to_human",
        )
    )

    revenue_per_intervention = (
        round(
            revenue_recovered_paise
            / interventions,
            2,
        )
        if interventions
        else 0.0
    )

    return {
        "cases_evaluated": n,
        "recovery_rate": (
            round(
                recovered_count / n,
                4,
            )
            if n
            else 0.0
        ),
        "revenue_recovered_paise": (
            revenue_recovered_paise
        ),
        "revenue_at_risk_paise": (
            revenue_at_risk_paise
        ),
        "unnecessary_interventions": (
            unnecessary
        ),
        "unnecessary_intervention_rate": (
            round(
                unnecessary / n,
                4,
            )
            if n
            else 0.0
        ),
        "human_escalations": escalations,
        "safe_stops": stops,
        "interventions_taken": interventions,
        "revenue_recovered_per_intervention_paise": (
            revenue_per_intervention
        ),
    }

def is_eligible(record: dict) -> bool:
    """
    Determine whether a case belongs to the eligible recovery subset.

    Eligibility is calculated independently of the strategy's decision.
    """

    return (
        record["ground_truth_recoverable"]
        and record["amount_paise"]
        <= HIGH_VALUE_ESCALATION_PAISE
        and record["hours_since_failure"]
        <= settings.recovery_window_hours
        and record["failure_event_count"]
        <= settings.recovery_max_retries
    )


def compute_stratified_metrics(
    records: List[dict],
    outcomes: List[dict],
    revenue_at_risk_paise: int,
) -> dict:
    """
    Produce both:

    1. Recovery effectiveness on eligible cases.
    2. Safety effectiveness on risky cases.

    Eligibility is independent of the strategy being evaluated.
    """

    n = len(records)

    eligible_idx = [
        i
        for i, record in enumerate(records)
        if is_eligible(record)
    ]

    risky_idx = [
        i
        for i, record in enumerate(records)
        if not is_eligible(record)
    ]

    eligible_outcomes = [
        outcomes[i]
        for i in eligible_idx
    ]

    risky_outcomes = [
        outcomes[i]
        for i in risky_idx
    ]

    eligible_revenue_at_risk = sum(
        records[i]["amount_paise"]
        for i in eligible_idx
    )

    risky_revenue_at_risk = sum(
        records[i]["amount_paise"]
        for i in risky_idx
    )

    total_revenue_recovered = sum(
        outcome["amount_recovered_paise"]
        for outcome in outcomes
    )

    eligible_revenue_recovered = sum(
        outcome["amount_recovered_paise"]
        for outcome in eligible_outcomes
    )

    total_recovered_count = sum(
        1
        for outcome in outcomes
        if outcome["recovered"]
    )

    eligible_recovered_count = sum(
        1
        for outcome in eligible_outcomes
        if outcome["recovered"]
    )

    interventions_taken = sum(
        1
        for outcome in outcomes
        if outcome["action"]
        not in (
            "stop",
            "escalate_to_human",
        )
    )

    escalations = sum(
        1
        for outcome in outcomes
        if outcome["escalated"]
    )

    unnecessary_total = sum(
        1
        for outcome in outcomes
        if outcome["unnecessary_intervention"]
    )

    unnecessary_within_risky = sum(
        1
        for outcome in risky_outcomes
        if outcome["unnecessary_intervention"]
    )

    safe_abstentions_within_risky = (
        len(risky_idx)
        - unnecessary_within_risky
    )

    def _rate(
        numerator: int,
        denominator: int,
    ) -> float:
        return (
            round(
                numerator / denominator,
                4,
            )
            if denominator
            else 0.0
        )

    return {
        # Whole population
        "total_cases": n,
        "total_revenue_at_risk_paise": (
            revenue_at_risk_paise
        ),
        "total_revenue_recovered_paise": (
            total_revenue_recovered
        ),
        "total_recovery_rate": _rate(
            total_recovered_count,
            n,
        ),
        "interventions_taken": interventions_taken,
        "revenue_recovered_per_intervention_paise": (
            round(
                total_revenue_recovered
                / interventions_taken,
                2,
            )
            if interventions_taken
            else 0.0
        ),
        "human_escalations": escalations,
        "human_escalation_rate": _rate(
            escalations,
            n,
        ),

        # Recovery effectiveness
        "eligible_cases": len(eligible_idx),
        "eligible_revenue_at_risk_paise": (
            eligible_revenue_at_risk
        ),
        "eligible_revenue_recovered_paise": (
            eligible_revenue_recovered
        ),
        "eligible_recovery_rate": _rate(
            eligible_recovered_count,
            len(eligible_idx),
        ),

        # Safety effectiveness
        "risky_cases": len(risky_idx),
        "risky_revenue_at_risk_paise": (
            risky_revenue_at_risk
        ),
        "unnecessary_interventions": (
            unnecessary_total
        ),
        "unnecessary_intervention_rate_overall": (
            _rate(
                unnecessary_total,
                n,
            )
        ),
        "unnecessary_intervention_rate_within_risky_subset": (
            _rate(
                unnecessary_within_risky,
                len(risky_idx),
            )
        ),
        "safe_abstention_rate_within_risky_subset": (
            _rate(
                safe_abstentions_within_risky,
                len(risky_idx),
            )
        ),
    }