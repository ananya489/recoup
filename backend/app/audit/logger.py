from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import get_db


async def write_audit_log(
    event_type: str,
    actor: str,
    entity_type: str,
    entity_id: str,
    metadata: dict | None = None,
) -> None:
    """
    Write one audit event to MongoDB.

    Every audit record gets an explicit UUID string _id.
    This prevents MongoDB from generating a BSON ObjectId,
    which cannot be returned directly by FastAPI's JSON encoder.
    """

    db = get_db()

    document = {
        "_id": str(uuid4()),
        "event_type": event_type,
        "actor": actor,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc),
    }

    await db.audit_logs.insert_one(document)