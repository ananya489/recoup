from fastapi import APIRouter

from app.db.mongo import get_db


router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


@router.get("/summary")
async def dashboard_summary():
    """
    Return live dashboard metrics from MongoDB.

    These are LIVE application metrics.
    They are intentionally separate from the offline
    1000-case synthetic evaluation report.
    """

    db = get_db()

    # ---------------------------------------------------------
    # Recovery cases
    # ---------------------------------------------------------

    total_cases = await db.recovery_cases.count_documents({})

    open_cases = await db.recovery_cases.count_documents(
        {
            "status": "open"
        }
    )

    action_pending_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "action_pending"
            }
        )
    )

    action_executed_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "action_executed"
            }
        )
    )

    recovered_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "recovered"
            }
        )
    )

    escalated_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "escalated"
            }
        )
    )

    stopped_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "stopped"
            }
        )
    )

    expired_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "expired"
            }
        )
    )

    action_failed_cases = (
        await db.recovery_cases.count_documents(
            {
                "status": "action_failed"
            }
        )
    )

    # ---------------------------------------------------------
    # Revenue at risk
    # ---------------------------------------------------------

    revenue_at_risk_result = (
        await db.recovery_cases.aggregate(
            [
                {
                    "$match": {
                        "status": {
                            "$nin": [
                                "recovered",
                                "stopped",
                                "expired",
                            ]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {
                            "$sum": "$amount_paise"
                        },
                    }
                },
            ]
        ).to_list(length=1)
    )

    revenue_at_risk_paise = (
        revenue_at_risk_result[0]["total"]
        if revenue_at_risk_result
        else 0
    )

    # ---------------------------------------------------------
    # Recovered revenue
    # ---------------------------------------------------------

    recovered_revenue_result = (
        await db.recovery_cases.aggregate(
            [
                {
                    "$match": {
                        "status": "recovered"
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {
                            "$sum": (
                                "$recovered_amount_paise"
                            )
                        },
                    }
                },
            ]
        ).to_list(length=1)
    )

    recovered_revenue_paise = (
        recovered_revenue_result[0]["total"]
        if recovered_revenue_result
        else 0
    )

    # ---------------------------------------------------------
    # Recovery rate
    # ---------------------------------------------------------

    recovery_rate = (
        round(
            recovered_cases / total_cases,
            4,
        )
        if total_cases
        else 0.0
    )

    # ---------------------------------------------------------
    # Recovery actions
    # ---------------------------------------------------------

    total_actions = (
        await db.recovery_actions.count_documents({})
    )

    executed_actions = (
        await db.recovery_actions.count_documents(
            {
                "status": "executed"
            }
        )
    )

    failed_actions = (
        await db.recovery_actions.count_documents(
            {
                "status": "failed"
            }
        )
    )

    requested_actions = (
        await db.recovery_actions.count_documents(
            {
                "status": "requested"
            }
        )
    )

    # ---------------------------------------------------------
    # Recent actions
    # ---------------------------------------------------------

    recent_actions_cursor = (
        db.recovery_actions
        .find({})
        .sort("requested_at", -1)
        .limit(10)
    )

    recent_actions = (
        await recent_actions_cursor.to_list(
            length=10
        )
    )

    # ---------------------------------------------------------
    # Return live dashboard data
    # ---------------------------------------------------------

    return {
        "cases": {
            "total": total_cases,
            "open": open_cases,
            "action_pending": action_pending_cases,
            "action_executed": action_executed_cases,
            "recovered": recovered_cases,
            "escalated": escalated_cases,
            "stopped": stopped_cases,
            "expired": expired_cases,
            "action_failed": action_failed_cases,
        },
        "revenue": {
            "at_risk_paise": revenue_at_risk_paise,
            "recovered_paise": recovered_revenue_paise,
            "recovery_rate": recovery_rate,
        },
        "actions": {
            "total": total_actions,
            "executed": executed_actions,
            "failed": failed_actions,
            "requested": requested_actions,
        },
        "recent_actions": recent_actions,
    }