from fastapi import APIRouter, HTTPException, Query

from app.db.mongo import get_db


router = APIRouter(
    prefix="/api",
    tags=["cases"],
)


@router.get("/recovery-cases")
async def list_recovery_cases(
    status: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):
    """
    Return recovery cases.

    Optional:
        ?status=open
        ?status=recovered
        ?limit=20
    """

    db = get_db()

    query = {}

    if status:
        query["status"] = status

    cursor = (
        db.recovery_cases
        .find(query)
        .sort("updated_at", -1)
        .limit(limit)
    )

    cases = await cursor.to_list(
        length=limit
    )

    return {
        "count": len(cases),
        "cases": cases,
    }


@router.get(
    "/recovery-cases/{case_id}"
)
async def get_recovery_case(
    case_id: str,
):
    """
    Return a complete recovery-case view.

    Includes:
    - recovery case
    - payment
    - customer, when available
    - recovery actions
    - audit trail
    """

    db = get_db()

    # ---------------------------------------------------------
    # 1. Recovery case
    # ---------------------------------------------------------

    case = await db.recovery_cases.find_one(
        {"_id": case_id}
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="recovery case not found",
        )

    # ---------------------------------------------------------
    # 2. Payment
    # ---------------------------------------------------------

    payment = await db.payments.find_one(
        {"_id": case["payment_id"]}
    )

    # ---------------------------------------------------------
    # 3. Customer
    #
    # Some demo/test records may not have customer_id.
    # Therefore this lookup is optional.
    # ---------------------------------------------------------

    customer = None

    customer_id = case.get(
        "customer_id"
    )

    if customer_id:
        customer = await db.customers.find_one(
            {"_id": customer_id}
        )

    # ---------------------------------------------------------
    # 4. Recovery actions
    # ---------------------------------------------------------

    actions_cursor = (
        db.recovery_actions
        .find(
            {
                "case_id": case_id
            }
        )
        .sort(
            "requested_at",
            1,
        )
    )

    actions = await actions_cursor.to_list(
        length=100
    )

    # ---------------------------------------------------------
    # 5. Audit trail
    # ---------------------------------------------------------

    audit_cursor = (
        db.audit_logs
        .find(
            {
                "entity_id": case_id
            }
        )
        .sort(
            "timestamp",
            1,
        )
    )

    audit_logs = await audit_cursor.to_list(
        length=200
    )

    return {
        "case": case,
        "payment": payment,
        "customer": customer,
        "actions": actions,
        "audit_logs": audit_logs,
    }


@router.get(
    "/recovery-cases/{case_id}/actions"
)
async def get_case_actions(
    case_id: str,
):
    """
    Return all recovery actions for a case.
    """

    db = get_db()

    case = await db.recovery_cases.find_one(
        {
            "_id": case_id
        }
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="recovery case not found",
        )

    cursor = (
        db.recovery_actions
        .find(
            {
                "case_id": case_id
            }
        )
        .sort(
            "requested_at",
            1,
        )
    )

    actions = await cursor.to_list(
        length=100
    )

    return {
        "case_id": case_id,
        "count": len(actions),
        "actions": actions,
    }


@router.get(
    "/recovery-actions/{idempotency_key}"
)
async def get_recovery_action(
    idempotency_key: str,
):
    """
    Return one recovery action using its idempotency key.
    """

    db = get_db()

    action = await db.recovery_actions.find_one(
        {
            "_id": idempotency_key
        }
    )

    if action is None:
        raise HTTPException(
            status_code=404,
            detail="recovery action not found",
        )

    return action


@router.get(
    "/recovery-cases/{case_id}/audit"
)
async def get_case_audit(
    case_id: str,
):
    """
    Return the audit trail for a recovery case,
    ordered chronologically.
    """

    db = get_db()

    case = await db.recovery_cases.find_one(
        {
            "_id": case_id
        }
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="recovery case not found",
        )

    cursor = (
        db.audit_logs
        .find(
            {
                "entity_id": case_id
            }
        )
        .sort(
            "timestamp",
            1,
        )
    )

    logs = await cursor.to_list(
        length=200
    )

    return {
        "case_id": case_id,
        "count": len(logs),
        "audit_logs": logs,
    }