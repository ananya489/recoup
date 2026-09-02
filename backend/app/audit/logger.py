from datetime import datetime, timezone
from typing import Optional

from app.db.mongo import get_db
from app.models.schemas import AuditLog


async def write_audit_log(
    event_type: str,
    actor: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Append one audit record to MongoDB.

    Audit records are append-only.
    This function inserts records and does not update or delete them.

    Never put secrets, API keys, or webhook secrets in metadata.
    """

    db = get_db()

    entry = AuditLog(
        event_type=event_type,
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
    )

    await db.audit_logs.insert_one(
        entry.model_dump()
    )