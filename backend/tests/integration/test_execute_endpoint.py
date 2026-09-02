import json
from datetime import datetime, timezone

import pytest
from mongomock_motor import AsyncMongoMockClient
from fastapi.testclient import TestClient

import app.ai.analyzer as analyzer_module
import app.db.mongo as mongo_module
import app.recovery.executor as executor_module
from app.main import app
from app.recovery.razorpay_client import MockRazorpayClient


VALID_AI_RESPONSE = json.dumps(
    {
        "failure_category": "insufficient_funds",
        "confidence": 0.9,
        "recommended_action": "send_payment_link",
        "suggested_retry_window_hours": 24,
        "reasoning": "Payment link is an appropriate recovery action.",
        "risk_level": "low",
        "requires_human_approval": False,
    }
)


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient(
        tz_aware=True
    )

    yield

    mongo_module._client = None


async def seed_case(
    case_id: str = "case_execute_1",
    payment_id: str = "pay_execute_1",
    amount_paise: int = 99900,
):
    db = mongo_module.get_db()

    await db.payments.insert_one(
        {
            "_id": payment_id,
            "amount_paise": amount_paise,
            "currency": "INR",
            "status": "failed",
            "method": "upi",
            "error_code": "BAD_REQUEST_ERROR",
            "error_description": "Insufficient balance.",
            "contact": "+919900011122",
        }
    )

    await db.recovery_cases.insert_one(
        {
            "_id": case_id,
            "payment_id": payment_id,
            "amount_paise": amount_paise,
            "status": "open",
            "failure_event_count": 1,
            "first_failure_at": datetime.now(
                timezone.utc
            ),
            "recovered_at": None,
            "recovered_amount_paise": None,
        }
    )


async def evaluate_case_with_mock_ai(case_id: str):
    analyzer_client = type(
        "FakeLLM",
        (),
        {
            "model": "fake-model",
        },
    )()

    async def fake_complete(
        system_prompt,
        user_prompt,
    ):
        return VALID_AI_RESPONSE

    analyzer_client.complete = fake_complete

    # Patch the client factory used by analyzer.py
    original_get_client = analyzer_module.get_llm_client

    analyzer_module.get_llm_client = (
        lambda: analyzer_client
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recovery-cases/{case_id}/evaluate"
            )

        return response

    finally:
        analyzer_module.get_llm_client = original_get_client


@pytest.mark.asyncio
async def test_execute_payment_link_action():
    await seed_case()

    evaluate_response = await evaluate_case_with_mock_ai(
        "case_execute_1"
    )

    assert evaluate_response.status_code == 200

    # Use mock Razorpay client so no real API call occurs.
    mock_client = MockRazorpayClient()

    original_get_client = executor_module.get_razorpay_client

    executor_module.get_razorpay_client = (
        lambda: mock_client
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/recovery-cases/case_execute_1/execute"
            )
    finally:
        executor_module.get_razorpay_client = (
            original_get_client
        )

    assert response.status_code == 200

    data = response.json()

    assert data["duplicate_request"] is False
    assert data["case_status"] == "action_executed"

    action = data["action"]

    assert action["status"] == "executed"
    assert action["action_type"] == "send_payment_link"
    assert action["provider_reference"] == "plink_mock_1"
    assert action["result"]["simulated"] is False


@pytest.mark.asyncio
async def test_execute_same_case_twice_is_idempotent():
    await seed_case(
        case_id="case_execute_2",
        payment_id="pay_execute_2",
    )

    evaluate_response = await evaluate_case_with_mock_ai(
        "case_execute_2"
    )

    assert evaluate_response.status_code == 200

    mock_client = MockRazorpayClient()

    original_get_client = executor_module.get_razorpay_client

    executor_module.get_razorpay_client = (
        lambda: mock_client
    )

    try:
        with TestClient(app) as client:
            first = client.post(
                "/api/recovery-cases/case_execute_2/execute"
            )

            second = client.post(
                "/api/recovery-cases/case_execute_2/execute"
            )
    finally:
        executor_module.get_razorpay_client = (
            original_get_client
        )

    assert first.status_code == 200
    assert second.status_code == 200

    first_data = first.json()
    second_data = second.json()

    assert first_data["duplicate_request"] is False

    assert (
        second_data["duplicate_request"]
        is True
    )

    db = mongo_module.get_db()

    count = await db.recovery_actions.count_documents(
        {"case_id": "case_execute_2"}
    )

    assert count == 1


@pytest.mark.asyncio
async def test_execute_without_evaluation_returns_400():
    await seed_case(
        case_id="case_execute_3",
        payment_id="pay_execute_3",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_execute_3/execute"
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_execute_nonexistent_case_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/does_not_exist/execute"
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_non_actionable_policy_result_is_blocked():
    await seed_case(
        case_id="case_execute_4",
        payment_id="pay_execute_4",
    )

    db = mongo_module.get_db()

    await db.recovery_cases.update_one(
        {
            "_id": "case_execute_4"
        },
        {
            "$set": {
                "last_policy_verdict": {
                    "case_id": "case_execute_4",
                    "decision_id": "test",
                    "approved": False,
                    "reason_code": "CASE_ALREADY_TERMINAL",
                    "final_action": "stop",
                    "policy_version": "v1",
                },
                "last_evaluated_at": datetime.now(
                    timezone.utc
                ),
            }
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_execute_4/execute"
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_executor_failure_is_recorded():
    await seed_case(
        case_id="case_execute_5",
        payment_id="pay_execute_5",
    )

    await evaluate_case_with_mock_ai(
        "case_execute_5"
    )

    failing_client = MockRazorpayClient(
        should_fail=True
    )

    original_get_client = executor_module.get_razorpay_client

    executor_module.get_razorpay_client = (
        lambda: failing_client
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/recovery-cases/case_execute_5/execute"
            )
    finally:
        executor_module.get_razorpay_client = (
            original_get_client
        )

    assert response.status_code == 200

    data = response.json()

    assert data["case_status"] == "action_failed"

    assert (
        data["action"]["status"]
        == "failed"
    )

    assert (
        data["action"]["error"]
        is not None
    )


@pytest.mark.asyncio
async def test_execute_writes_audit_logs():
    await seed_case(
        case_id="case_execute_6",
        payment_id="pay_execute_6",
    )

    await evaluate_case_with_mock_ai(
        "case_execute_6"
    )

    mock_client = MockRazorpayClient()

    original_get_client = executor_module.get_razorpay_client

    executor_module.get_razorpay_client = (
        lambda: mock_client
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/recovery-cases/case_execute_6/execute"
            )
    finally:
        executor_module.get_razorpay_client = (
            original_get_client
        )

    assert response.status_code == 200

    db = mongo_module.get_db()

    events = await db.audit_logs.find(
        {"entity_id": "case_execute_6"}
    ).to_list(length=None)

    event_types = [
        event["event_type"]
        for event in events
    ]

    assert "action_requested" in event_types
    assert "action_executed" in event_types