import json
from datetime import datetime, timedelta, timezone

import pytest
from mongomock_motor import AsyncMongoMockClient
from fastapi.testclient import TestClient

import app.ai.analyzer as analyzer_module
import app.db.mongo as mongo_module
from app.main import app


NOW = datetime.now(timezone.utc)


class FakeLLMClient:
    def __init__(
        self,
        response_text=None,
        raise_exc=None,
        model="fake-model",
    ):
        self.response_text = response_text
        self.raise_exc = raise_exc
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if self.raise_exc:
            raise self.raise_exc

        return self.response_text


VALID_LOW_VALUE_RESPONSE = json.dumps(
    {
        "failure_category": "insufficient_funds",
        "confidence": 0.9,
        "recommended_action": "retry_later",
        "suggested_retry_window_hours": 24,
        "reasoning": "Should recover after next inflow.",
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


async def _seed_open_case(
    case_id: str,
    payment_id: str,
    amount_paise: int,
    failure_event_count: int = 1,
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
        }
    )

    await db.recovery_cases.insert_one(
        {
            "_id": case_id,
            "payment_id": payment_id,
            "amount_paise": amount_paise,
            "status": "open",
            "failure_event_count": failure_event_count,
            "first_failure_at": NOW - timedelta(hours=1),
            "recovered_at": None,
            "recovered_amount_paise": None,
        }
    )


@pytest.mark.asyncio
async def test_evaluate_low_value_case_is_approved_and_marked_action_pending(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer_module,
        "get_llm_client",
        lambda: FakeLLMClient(
            response_text=VALID_LOW_VALUE_RESPONSE
        ),
    )

    await _seed_open_case(
        "case_eval_1",
        "pay_eval_1",
        amount_paise=99900,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_eval_1/evaluate"
        )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["ai_decision"]["recommended_action"]
        == "retry_later"
    )

    assert data["policy_verdict"]["approved"] is True

    assert (
        data["policy_verdict"]["reason_code"]
        == "OK"
    )

    assert data["case_status"] == "action_pending"


@pytest.mark.asyncio
async def test_evaluate_high_value_case_is_escalated_regardless_of_ai(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer_module,
        "get_llm_client",
        lambda: FakeLLMClient(
            response_text=VALID_LOW_VALUE_RESPONSE
        ),
    )

    await _seed_open_case(
        "case_eval_2",
        "pay_eval_2",
        amount_paise=2_500_000,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_eval_2/evaluate"
        )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["policy_verdict"]["reason_code"]
        == "HIGH_VALUE_REQUIRES_HUMAN"
    )

    assert (
        data["policy_verdict"]["final_action"]
        == "escalate_to_human"
    )

    assert data["case_status"] == "escalated"


@pytest.mark.asyncio
async def test_evaluate_when_llm_unavailable_safely_escalates_no_execution(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer_module,
        "get_llm_client",
        lambda: FakeLLMClient(
            raise_exc=ConnectionError("down")
        ),
    )

    await _seed_open_case(
        "case_eval_3",
        "pay_eval_3",
        amount_paise=99900,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_eval_3/evaluate"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["ai_decision"] is None

    assert (
        data["policy_verdict"]["reason_code"]
        == "LLM_OUTPUT_INVALID"
    )

    assert (
        data["policy_verdict"]["final_action"]
        == "escalate_to_human"
    )

    assert data["case_status"] == "escalated"


@pytest.mark.asyncio
async def test_evaluate_unsafe_recommendation_after_retry_limit_is_blocked(
    monkeypatch,
):
    unsafe_response = json.dumps(
        {
            "failure_category": "insufficient_funds",
            "confidence": 0.9,
            "recommended_action": "retry_now",
            "suggested_retry_window_hours": 1,
            "reasoning": "Retry requested.",
            "risk_level": "low",
            "requires_human_approval": False,
        }
    )

    monkeypatch.setattr(
        analyzer_module,
        "get_llm_client",
        lambda: FakeLLMClient(
            response_text=unsafe_response
        ),
    )

    await _seed_open_case(
        "case_eval_4",
        "pay_eval_4",
        amount_paise=99900,
        failure_event_count=5,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_eval_4/evaluate"
        )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["policy_verdict"]["approved"]
        is False
    )

    assert (
        data["policy_verdict"]["reason_code"]
        == "MAX_RETRIES_HIT"
    )

    assert data["case_status"] == "escalated"


def test_evaluate_nonexistent_case_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/does_not_exist/evaluate"
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_writes_audit_trail(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer_module,
        "get_llm_client",
        lambda: FakeLLMClient(
            response_text=VALID_LOW_VALUE_RESPONSE
        ),
    )

    await _seed_open_case(
        "case_eval_5",
        "pay_eval_5",
        amount_paise=99900,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/recovery-cases/case_eval_5/evaluate"
        )

        assert response.status_code == 200

        db = mongo_module.get_db()

        events = await db.audit_logs.find(
            {"entity_id": "case_eval_5"}
        ).to_list(length=None)

    event_types = [
        event["event_type"]
        for event in events
    ]

    assert "ai_decision_created" in event_types
    assert "policy_evaluated" in event_types