import pytest
from mongomock_motor import AsyncMongoMockClient

import app.db.mongo as mongo_module
from app.webhooks.repository import (
    ensure_indexes,
    store_webhook_event,
)


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient()

    yield

    mongo_module._client = None


@pytest.mark.asyncio
async def test_store_new_event_succeeds():
    await ensure_indexes()

    is_new = await store_webhook_event(
        event_id="evt_repo_001",
        event_type="payment.failed",
        signature_verified=True,
    )

    assert is_new is True

    db = mongo_module.get_db()

    doc = await db.webhook_events.find_one(
        {"event_id": "evt_repo_001"}
    )

    assert doc is not None
    assert doc["event_type"] == "payment.failed"
    assert doc["signature_verified"] is True
    assert doc["processing_status"] == "stored"
    assert doc["attempts"] == 1
    assert doc["error"] is None
    assert doc["processed_at"] is None


@pytest.mark.asyncio
async def test_duplicate_event_id_is_rejected():
    await ensure_indexes()

    first = await store_webhook_event(
        event_id="evt_repo_002",
        event_type="payment.failed",
        signature_verified=True,
    )

    second = await store_webhook_event(
        event_id="evt_repo_002",
        event_type="payment.failed",
        signature_verified=True,
    )

    assert first is True
    assert second is False

    db = mongo_module.get_db()

    count = await db.webhook_events.count_documents(
        {"event_id": "evt_repo_002"}
    )

    assert count == 1


@pytest.mark.asyncio
async def test_no_secret_fields_are_ever_stored():
    await ensure_indexes()

    await store_webhook_event(
        event_id="evt_repo_003",
        event_type="payment.captured",
        signature_verified=True,
    )

    db = mongo_module.get_db()

    doc = await db.webhook_events.find_one(
        {"event_id": "evt_repo_003"}
    )

    stored_keys = set(doc.keys())

    forbidden_substrings = (
        "secret",
        "key_secret",
        "webhook_secret",
    )

    for key in stored_keys:
        for forbidden in forbidden_substrings:
            assert forbidden not in key.lower()