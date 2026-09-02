import pytest
from mongomock_motor import AsyncMongoMockClient

import app.db.mongo as mongo_module
from app.recovery.actions_repository import (
    create_requested_action,
    ensure_indexes,
    finalize_action,
    get_action,
    has_action_in_flight,
)


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient(
        tz_aware=True
    )

    yield

    mongo_module._client = None


@pytest.mark.asyncio
async def test_create_requested_action():
    await ensure_indexes()

    action = await create_requested_action(
        idempotency_key="action_test_001",
        case_id="case_test_001",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    assert action is not None
    assert action["idempotency_key"] == "action_test_001"
    assert action["case_id"] == "case_test_001"
    assert action["status"] == "requested"


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_is_rejected():
    await ensure_indexes()

    first = await create_requested_action(
        idempotency_key="action_test_002",
        case_id="case_test_002",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    second = await create_requested_action(
        idempotency_key="action_test_002",
        case_id="case_test_002",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_has_action_in_flight():
    await ensure_indexes()

    await create_requested_action(
        idempotency_key="action_test_003",
        case_id="case_test_003",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    assert (
        await has_action_in_flight("case_test_003")
        is True
    )

    assert (
        await has_action_in_flight("case_not_found")
        is False
    )


@pytest.mark.asyncio
async def test_finalize_action():
    await ensure_indexes()

    await create_requested_action(
        idempotency_key="action_test_004",
        case_id="case_test_004",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    await finalize_action(
        idempotency_key="action_test_004",
        status="executed",
        provider_reference="plink_mock_1",
        result={
            "simulated": True,
            "short_url": "https://rzp.io/mock/case_test_004",
        },
        error=None,
    )

    action = await get_action(
        "action_test_004"
    )

    assert action is not None
    assert action["status"] == "executed"
    assert action["provider_reference"] == "plink_mock_1"
    assert action["error"] is None
    assert action["executed_at"] is not None


@pytest.mark.asyncio
async def test_get_action_returns_none_for_missing_action():
    await ensure_indexes()

    action = await get_action(
        "does_not_exist"
    )

    assert action is None