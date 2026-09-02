from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db


async def ensure_indexes() -> None:
    """
    Create indexes needed by the recovery action system.
    """

    db = get_db()

    await db.recovery_actions.create_index(
        "case_id"
    )


async def has_action_in_flight(
    case_id: str,
) -> bool:
    """
    Return True when this case already has
    an action in requested state.
    """

    db = get_db()

    document = await db.recovery_actions.find_one(
        {
            "case_id": case_id,
            "status": "requested",
        }
    )

    return document is not None


async def create_requested_action(
    idempotency_key: str,
    case_id: str,
    action_type: str,
    amount_paise: int,
    approved_by: str,
) -> Optional[dict]:
    """
    Create a new recovery action.

    The idempotency key is also used as MongoDB _id.
    Therefore a duplicate key is safely rejected.
    """

    db = get_db()

    now = datetime.now(timezone.utc)

    document = {
        "_id": idempotency_key,
        "idempotency_key": idempotency_key,
        "case_id": case_id,
        "action_type": action_type,
        "amount_paise": amount_paise,
        "status": "requested",
        "requested_by": "policy_engine",
        "approved_by": approved_by,
        "requested_at": now,
        "executed_at": None,
        "provider_reference": None,
        "result": None,
        "error": None,
    }

    try:
        await db.recovery_actions.insert_one(
            document
        )

        return document

    except DuplicateKeyError:
        return None


async def finalize_action(
    idempotency_key: str,
    status: str,
    provider_reference: Optional[str],
    result: dict,
    error: Optional[str],
) -> None:
    """
    Finalize an action after the executor returns.

    status should normally be:
        executed
        failed
    """

    db = get_db()

    await db.recovery_actions.update_one(
        {
            "_id": idempotency_key
        },
        {
            "$set": {
                "status": status,
                "executed_at": datetime.now(
                    timezone.utc
                ),
                "provider_reference": (
                    provider_reference
                ),
                "result": result,
                "error": error,
            }
        },
    )


async def get_action(
    idempotency_key: str,
) -> Optional[dict]:
    """
    Retrieve a recovery action by idempotency key.
    """

    db = get_db()

    return await db.recovery_actions.find_one(
        {
            "_id": idempotency_key
        }
    )