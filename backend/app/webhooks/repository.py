from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db
from app.models.schemas import WebhookEvent


async def ensure_indexes() -> None:
    db = get_db()
    await db.webhook_events.create_index(
        "event_id",
        unique=True,
    )


async def store_webhook_event(
    event_id: str,
    event_type: str,
    signature_verified: bool,
) -> bool:
    db = get_db()

    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        received_at=datetime.now(timezone.utc),
        signature_verified=signature_verified,
    )

    try:
        await db.webhook_events.insert_one(
            event.model_dump()
        )
        return True

    except DuplicateKeyError:
        return False