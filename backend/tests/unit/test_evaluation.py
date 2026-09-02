import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2]),
)

from app.evaluation.baseline import baseline_action
from app.evaluation.dataset import generate_dataset
from app.evaluation.engine import (
    compute_metrics,
    evaluate_case,
    simulate_ai_recommendation,
)
from app.policy.engine import evaluate_policy


def test_dataset_generation_is_deterministic_given_same_seed():
    d1 = generate_dataset(
        n=200,
        seed=42,
    )

    d2 = generate_dataset(
        n=200,
        seed=42,
    )

    assert d1 == d2


def test_dataset_different_seeds_produce_different_data():
    d1 = generate_dataset(
        n=200,
        seed=42,
    )

    d2 = generate_dataset(
        n=200,
        seed=7,
    )

    assert d1 != d2


def test_dataset_meets_minimum_size_and_field_completeness():
    dataset = generate_dataset(
        n=1000,
        seed=42,
    )

    assert len(dataset) == 1000

    required_fields = {
        "case_id",
        "payment_id",
        "amount_paise",
        "payment_method",
        "failure_category",
        "failure_event_count",
        "hours_since_failure",
        "ground_truth_recoverable",
        "ground_truth_best_action",
        "simulated_recovers_if_nudged",
        "simulated_recovers_if_ignored",
    }

    assert required_fields.issubset(
        dataset[0].keys()
    )

    assert all(
        r["amount_paise"] > 0
        for r in dataset
    )


def test_dataset_category_distribution_is_not_uniform():
    dataset = generate_dataset(
        n=1000,
        seed=42,
    )

    from collections import Counter

    counts = Counter(
        r["failure_category"]
        for r in dataset
    )

    assert (
        counts["insufficient_funds"]
        > counts["suspected_fraud_block"] * 3
    )


def test_baseline_retries_everything_including_unsafe_categories():
    fraud_case = {
        "failure_event_count": 1
    }

    assert (
        baseline_action(fraud_case)
        == "retry_later"
    )


def test_baseline_stops_above_its_retry_cap():
    case = {
        "failure_event_count": 5
    }

    assert baseline_action(case) == "stop"


def test_simulate_ai_recommendation_recommends_escalation_for_fraud():
    record = {
        "case_id": "c1",
        "failure_category": "suspected_fraud_block",
    }

    decision = simulate_ai_recommendation(
        record
    )

    assert (
        decision.recommended_action
        == "escalate_to_human"
    )

    assert decision.risk_level == "high"


def test_evaluate_case_uses_ignored_probability_for_stopped_cases():
    record = {
        "case_id": "c1",
        "amount_paise": 1000,
        "ground_truth_recoverable": True,
        "simulated_recovers_if_nudged": True,
        "simulated_recovers_if_ignored": False,
    }

    outcome = evaluate_case(
        record,
        "stop",
    )

    assert outcome["recovered"] is False
    assert (
        outcome["amount_recovered_paise"]
        == 0
    )


def test_evaluate_case_flags_unnecessary_intervention_on_unrecoverable_category():
    record = {
        "case_id": "c1",
        "amount_paise": 1000,
        "ground_truth_recoverable": False,
        "simulated_recovers_if_nudged": False,
        "simulated_recovers_if_ignored": False,
    }

    outcome = evaluate_case(
        record,
        "retry_later",
    )

    assert (
        outcome["unnecessary_intervention"]
        is True
    )


def test_compute_metrics_totals_are_internally_consistent():
    dataset = generate_dataset(
        n=300,
        seed=42,
    )

    outcomes = [
        evaluate_case(
            r,
            baseline_action(r),
        )
        for r in dataset
    ]

    revenue_at_risk = sum(
        r["amount_paise"]
        for r in dataset
    )

    metrics = compute_metrics(
        outcomes,
        revenue_at_risk,
    )

    assert (
        metrics["cases_evaluated"]
        == 300
    )

    assert (
        0.0
        <= metrics["recovery_rate"]
        <= 1.0
    )

    assert (
        0
        <= metrics["revenue_recovered_paise"]
        <= revenue_at_risk
    )

    assert (
        metrics["unnecessary_interventions"]
        <= metrics["interventions_taken"]
    )


def test_recoup_policy_path_never_recommends_action_for_high_value_without_escalation():
    from datetime import (
        datetime,
        timedelta,
        timezone,
    )

    from app.policy.engine import (
        HIGH_VALUE_ESCALATION_PAISE,
    )

    record = {
        "case_id": "high_value_test_case",
        "amount_paise": (
            HIGH_VALUE_ESCALATION_PAISE + 1
        ),
        "payment_method": "card",
        "failure_category": "insufficient_funds",
        "failure_event_count": 1,
        "hours_since_failure": 1.0,
        "ground_truth_recoverable": True,
        "ground_truth_best_action": "retry_later",
        "simulated_recovers_if_nudged": True,
        "simulated_recovers_if_ignored": False,
    }

    now = datetime.now(
        timezone.utc
    )

    decision = simulate_ai_recommendation(
        record
    )

    verdict = evaluate_policy(
        decision=decision,
        case_id=record["case_id"],
        case_status="open",
        amount_paise=record["amount_paise"],
        payment_status="failed",
        failure_event_count=record[
            "failure_event_count"
        ],
        first_failure_at=(
            now
            - timedelta(
                hours=record[
                    "hours_since_failure"
                ]
            )
        ),
        now=now,
    )

    assert (
        verdict.final_action
        == "escalate_to_human"
    )

    assert (
        verdict.reason_code
        == "HIGH_VALUE_REQUIRES_HUMAN"
    )


def test_is_eligible_true_for_normal_low_value_case():
    from app.evaluation.engine import is_eligible

    record = {
        "ground_truth_recoverable": True,
        "amount_paise": 99900,
        "hours_since_failure": 10.0,
        "failure_event_count": 1,
    }

    assert is_eligible(record) is True


def test_is_eligible_false_for_unrecoverable_category():
    from app.evaluation.engine import is_eligible

    record = {
        "ground_truth_recoverable": False,
        "amount_paise": 99900,
        "hours_since_failure": 10.0,
        "failure_event_count": 1,
    }

    assert is_eligible(record) is False


def test_is_eligible_false_above_high_value_ceiling():
    from app.evaluation.engine import is_eligible
    from app.policy.engine import HIGH_VALUE_ESCALATION_PAISE

    record = {
        "ground_truth_recoverable": True,
        "amount_paise": HIGH_VALUE_ESCALATION_PAISE + 1,
        "hours_since_failure": 10.0,
        "failure_event_count": 1,
    }

    assert is_eligible(record) is False


def test_stratified_metrics_partition_covers_every_case_exactly_once():
    from app.evaluation.engine import (
        compute_stratified_metrics,
    )

    dataset = generate_dataset(
        n=300,
        seed=42,
    )

    outcomes = [
        evaluate_case(
            record,
            baseline_action(record),
        )
        for record in dataset
    ]

    metrics = compute_stratified_metrics(
        dataset,
        outcomes,
        sum(
            record["amount_paise"]
            for record in dataset
        ),
    )

    assert (
        metrics["eligible_cases"]
        + metrics["risky_cases"]
        == metrics["total_cases"]
    )


def test_stratified_metrics_eligible_revenue_never_exceeds_eligible_at_risk():
    from app.evaluation.engine import (
        compute_stratified_metrics,
    )

    dataset = generate_dataset(
        n=300,
        seed=42,
    )

    outcomes = [
        evaluate_case(
            record,
            baseline_action(record),
        )
        for record in dataset
    ]

    metrics = compute_stratified_metrics(
        dataset,
        outcomes,
        sum(
            record["amount_paise"]
            for record in dataset
        ),
    )

    assert (
        metrics["eligible_revenue_recovered_paise"]
        <= metrics["eligible_revenue_at_risk_paise"]
    )


def test_stratified_metrics_unnecessary_interventions_only_come_from_risky_subset():
    from app.evaluation.engine import (
        compute_stratified_metrics,
    )

    dataset = generate_dataset(
        n=300,
        seed=42,
    )

    outcomes = [
        evaluate_case(
            record,
            baseline_action(record),
        )
        for record in dataset
    ]

    metrics = compute_stratified_metrics(
        dataset,
        outcomes,
        sum(
            record["amount_paise"]
            for record in dataset
        ),
    )

    assert (
        metrics["unnecessary_interventions"]
        <= metrics["risky_cases"]
    )