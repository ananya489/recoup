def baseline_action(record: dict) -> str:
    """
    Naive baseline strategy.

    Retry failed payments up to three times without
    considering failure category or risk.
    """

    if record["failure_event_count"] <= 3:
        return "retry_later"

    return "stop"