import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.evaluation.baseline import baseline_action
from app.evaluation.dataset import generate_dataset
from app.evaluation.engine import (
    compute_stratified_metrics,
    evaluate_case,
    is_eligible,
    simulate_ai_recommendation,
)
from app.policy.engine import (
    HIGH_VALUE_ESCALATION_PAISE,
    evaluate_policy,
)


def run(
    n_cases: int = 1000,
    seed: int = 42,
    output_dir: str = "eval_output",
) -> dict:
    """
    Run the reproducible Recoup-vs-baseline evaluation.

    The Recoup path uses the deterministic evaluation stand-in
    for the AI recommender. The real policy engine is used directly.
    """

    dataset = generate_dataset(
        n=n_cases,
        seed=seed,
    )

    now = datetime.now(timezone.utc)

    baseline_outcomes = []
    recoup_outcomes = []
    rows = []

    for record in dataset:

        # -----------------------------------------------------
        # Baseline
        # -----------------------------------------------------

        baseline_action_value = baseline_action(
            record
        )

        baseline_outcome = evaluate_case(
            record,
            baseline_action_value,
        )

        baseline_outcomes.append(
            baseline_outcome
        )

        # -----------------------------------------------------
        # Recoup
        # -----------------------------------------------------

        decision = simulate_ai_recommendation(
            record
        )

        first_failure_at = (
            now
            - timedelta(
                hours=record[
                    "hours_since_failure"
                ]
            )
        )

        verdict = evaluate_policy(
            decision=decision,
            case_id=record["case_id"],
            case_status="open",
            amount_paise=record[
                "amount_paise"
            ],
            payment_status="failed",
            failure_event_count=record[
                "failure_event_count"
            ],
            first_failure_at=first_failure_at,
            now=now,
        )

        recoup_outcome = evaluate_case(
            record,
            verdict.final_action,
        )

        recoup_outcomes.append(
            recoup_outcome
        )

        rows.append(
            {
                "case_id": record["case_id"],
                "amount_paise": record[
                    "amount_paise"
                ],
                "failure_category": record[
                    "failure_category"
                ],
                "ground_truth_recoverable": (
                    record[
                        "ground_truth_recoverable"
                    ]
                ),
                "eligible": is_eligible(
                    record
                ),
                "baseline_action": (
                    baseline_outcome[
                        "action"
                    ]
                ),
                "baseline_recovered": (
                    baseline_outcome[
                        "recovered"
                    ]
                ),
                "recoup_action": (
                    recoup_outcome[
                        "action"
                    ]
                ),
                "recoup_policy_reason_code": (
                    verdict.reason_code
                ),
                "recoup_recovered": (
                    recoup_outcome[
                        "recovered"
                    ]
                ),
            }
        )

    # ---------------------------------------------------------
    # Overall revenue at risk
    # ---------------------------------------------------------

    revenue_at_risk_paise = sum(
        record["amount_paise"]
        for record in dataset
    )

    # ---------------------------------------------------------
    # Stratified metrics
    # ---------------------------------------------------------

    baseline_metrics = compute_stratified_metrics(
        dataset,
        baseline_outcomes,
        revenue_at_risk_paise,
    )

    recoup_metrics = compute_stratified_metrics(
        dataset,
        recoup_outcomes,
        revenue_at_risk_paise,
    )

    # ---------------------------------------------------------
    # Final report
    # ---------------------------------------------------------

    report = {
        "generated_at": now.isoformat(),
        "dataset_seed": seed,
        "n_cases": n_cases,

        # IMPORTANT:
        # Read live configuration so the report tells us
        # which policy thresholds were actually active.
        "recovery_window_hours_used": (
            settings.recovery_window_hours
        ),
        "recovery_max_retries_used": (
            settings.recovery_max_retries
        ),
        "high_value_escalation_paise_used": (
            HIGH_VALUE_ESCALATION_PAISE
        ),

        "revenue_at_risk_paise": (
            revenue_at_risk_paise
        ),

        "baseline": baseline_metrics,

        "recoup": recoup_metrics,

        # Overall revenue comparison
        "total_recovery_uplift_paise": (
            recoup_metrics[
                "total_revenue_recovered_paise"
            ]
            - baseline_metrics[
                "total_revenue_recovered_paise"
            ]
        ),

        # Eligible-case recovery comparison
        "eligible_recovery_uplift_paise": (
            recoup_metrics[
                "eligible_revenue_recovered_paise"
            ]
            - baseline_metrics[
                "eligible_revenue_recovered_paise"
            ]
        ),

        # Safety improvement
        "unnecessary_intervention_reduction": (
            baseline_metrics[
                "unnecessary_interventions"
            ]
            - recoup_metrics[
                "unnecessary_interventions"
            ]
        ),

        "note": (
            "The 'recoup' numbers use a deterministic "
            "rule-based stand-in for the AI recommender "
            "(app/evaluation/engine.py::"
            "simulate_ai_recommendation), not a live "
            "LLM call. This evaluation makes zero "
            "external AI API calls and is reproducible "
            "with --seed. The policy engine itself is "
            "the real production code being measured. "
            "Eligible and risky subsets are computed "
            "independently from strategy decisions using "
            "ground truth and the active policy thresholds."
        ),
    }

    # ---------------------------------------------------------
    # Write files
    # ---------------------------------------------------------

    out_dir = Path(output_dir)

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        out_dir / "report.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    with open(
        out_dir / "cases.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)

    return report


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Run the Recoup vs baseline "
            "synthetic evaluation."
        )
    )

    parser.add_argument(
        "--n-cases",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="eval_output",
    )

    args = parser.parse_args()

    result = run(
        n_cases=args.n_cases,
        seed=args.seed,
        output_dir=args.output_dir,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )