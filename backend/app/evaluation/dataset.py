import random
from typing import List


_CATEGORY_WEIGHTS = {
    "insufficient_funds": 0.40,
    "bank_timeout": 0.15,
    "invalid_card_or_expired": 0.15,
    "otp_or_auth_failure": 0.10,
    "gateway_or_network_error": 0.10,
    "mandate_cancelled": 0.05,
    "suspected_fraud_block": 0.03,
    "unknown": 0.02,
}


_METHOD_WEIGHTS = {
    "upi": 0.55,
    "card": 0.30,
    "netbanking": 0.10,
    "wallet": 0.05,
}


_FAILURE_COUNT_WEIGHTS = {
    1: 0.60,
    2: 0.25,
    3: 0.10,
    4: 0.05,
}


_RECOVERABLE_BY_CATEGORY = {
    "insufficient_funds": True,
    "bank_timeout": True,
    "invalid_card_or_expired": True,
    "otp_or_auth_failure": True,
    "gateway_or_network_error": True,
    "mandate_cancelled": False,
    "suspected_fraud_block": False,
    "unknown": False,
}


_BEST_ACTION_BY_CATEGORY = {
    "insufficient_funds": "retry_later",
    "bank_timeout": "retry_now",
    "invalid_card_or_expired": "send_payment_link",
    "otp_or_auth_failure": "retry_now",
    "gateway_or_network_error": "retry_now",
    "mandate_cancelled": "escalate_to_human",
    "suspected_fraud_block": "escalate_to_human",
    "unknown": "escalate_to_human",
}


_RECOVERS_IF_NUDGED_PROB = {
    "insufficient_funds": 0.55,
    "bank_timeout": 0.75,
    "invalid_card_or_expired": 0.45,
    "otp_or_auth_failure": 0.70,
    "gateway_or_network_error": 0.65,
    "mandate_cancelled": 0.05,
    "suspected_fraud_block": 0.02,
    "unknown": 0.10,
}


_RECOVERS_IF_IGNORED_PROB = {
    "insufficient_funds": 0.10,
    "bank_timeout": 0.20,
    "invalid_card_or_expired": 0.05,
    "otp_or_auth_failure": 0.15,
    "gateway_or_network_error": 0.20,
    "mandate_cancelled": 0.01,
    "suspected_fraud_block": 0.00,
    "unknown": 0.02,
}


def _weighted_choice(
    rng: random.Random,
    weights: dict,
) -> str:
    keys = list(weights.keys())
    probabilities = list(weights.values())

    return rng.choices(
        keys,
        weights=probabilities,
        k=1,
    )[0]


def generate_dataset(
    n: int = 1000,
    seed: int = 42,
) -> List[dict]:
    """
    Generate a reproducible synthetic failed-payment dataset.

    This is synthetic data only.
    It is not derived from real Razorpay merchant data.
    """

    rng = random.Random(seed)

    records = []

    for i in range(n):

        category = _weighted_choice(
            rng,
            _CATEGORY_WEIGHTS,
        )

        method = _weighted_choice(
            rng,
            _METHOD_WEIGHTS,
        )

        failure_event_count = int(
            _weighted_choice(
                rng,
                {
                    str(k): v
                    for k, v in _FAILURE_COUNT_WEIGHTS.items()
                },
            )
        )

        # Approximate subscription/D2C amount range:
        # ₹99 to ₹49,999.
        amount_paise = int(
            max(
                9_900,
                min(
                    4_999_900,
                    rng.lognormvariate(
                        6.6,
                        0.7,
                    )
                    * 100,
                ),
            )
        )

        hours_since_failure = rng.uniform(
            0,
            90,
        )

        recovers_if_nudged = (
            rng.random()
            < _RECOVERS_IF_NUDGED_PROB[
                category
            ]
        )

        recovers_if_ignored = (
            rng.random()
            < _RECOVERS_IF_IGNORED_PROB[
                category
            ]
        )

        records.append(
            {
                "case_id": f"synthetic_case_{i:05d}",
                "payment_id": f"synthetic_pay_{i:05d}",
                "amount_paise": amount_paise,
                "payment_method": method,
                "failure_category": category,
                "failure_event_count": failure_event_count,
                "hours_since_failure": round(
                    hours_since_failure,
                    2,
                ),
                "ground_truth_recoverable": (
                    _RECOVERABLE_BY_CATEGORY[
                        category
                    ]
                ),
                "ground_truth_best_action": (
                    _BEST_ACTION_BY_CATEGORY[
                        category
                    ]
                ),
                "simulated_recovers_if_nudged": (
                    recovers_if_nudged
                ),
                "simulated_recovers_if_ignored": (
                    recovers_if_ignored
                ),
            }
        )

    return records