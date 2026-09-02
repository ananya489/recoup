import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2]),
)

import app.db.mongo as mongo_module
from app.main import app


NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient(
        tz_aware=True
    )

    yield

    mongo_module._client = None


async def seed_case(
    case_id="case_a1",
    payment_id="pay_a1",
    status="escalated",
    updated_at=None,
):
    db = mongo_module.get_db()

    await db.payments.insert_one(
        {
            "_id": payment_id,
            "amount_paise": 99900,
            "status": "failed",
            "method": "upi",
        }
    )

    await db.recovery_cases.insert_one(
        {
            "_id": case_id,
            "payment_id": payment_id,
            "amount_paise": 99900,
            "status": status,
            "updated_at": updated_at or NOW,
            "last_ai_decision": {
                "recommended_action": "retry_later",
                "confidence": 0.9,
            },
            "last_policy_verdict": {
                "approved": True,
                "reason_code": "OK",
                "final_action": "retry_later",
            },
        }
    )

    await db.recovery_actions.insert_one(
        {
            "_id": f"{case_id}:action1",
            "case_id": case_id,
            "action_type": "send_payment_link",
            "status": "executed",
            "requested_at": NOW,
        }
    )

    await db.audit_logs.insert_one(
        {
            "_id": f"{case_id}:audit1",
            "event_type": "ai_decision_created",
            "actor": "ai_analyzer",
            "entity_type": "recovery_case",
            "entity_id": case_id,
            "metadata": {},
            "timestamp": NOW,
        }
    )

    await db.audit_logs.insert_one(
        {
            "_id": f"{case_id}:audit2",
            "event_type": "policy_evaluated",
            "actor": "policy_engine",
            "entity_type": "recovery_case",
            "entity_id": case_id,
            "metadata": {},
            "timestamp": NOW + timedelta(seconds=1),
        }
    )


def test_list_cases_returns_seeded_case():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["cases"][0]["_id"] == "case_a1"


def test_list_cases_filters_by_status():
    asyncio.run(
        seed_case(
            case_id="case_a2",
            payment_id="pay_a2",
            status="recovered",
        )
    )

    asyncio.run(
        seed_case(
            case_id="case_a3",
            payment_id="pay_a3",
            status="escalated",
        )
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases?status=escalated"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["cases"][0]["status"] == "escalated"


def test_list_cases_respects_limit():
    for i in range(5):
        asyncio.run(
            seed_case(
                case_id=f"case_lim_{i}",
                payment_id=f"pay_lim_{i}",
                status="open",
                updated_at=(
                    NOW + timedelta(seconds=i)
                ),
            )
        )

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases?limit=3"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 3
    assert len(data["cases"]) == 3


def test_case_detail_includes_related_data():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/case_a1"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["case"]["_id"] == "case_a1"
    assert data["payment"]["_id"] == "pay_a1"
    assert data["customer"] is None

    assert len(data["actions"]) == 1

    assert len(data["audit_logs"]) == 2

    assert (
        data["audit_logs"][0]["event_type"]
        == "ai_decision_created"
    )

    assert (
        data["audit_logs"][1]["event_type"]
        == "policy_evaluated"
    )


def test_case_detail_404_for_missing_case():
    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/does_not_exist"
        )

    assert response.status_code == 404


def test_case_actions_endpoint():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/case_a1/actions"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == "case_a1"
    assert data["count"] == 1
    assert (
        data["actions"][0]["action_type"]
        == "send_payment_link"
    )


def test_case_actions_404_for_missing_case():
    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/does_not_exist/actions"
        )

    assert response.status_code == 404


def test_single_action_lookup():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-actions/"
            "case_a1:action1"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == "case_a1"
    assert (
        data["action_type"]
        == "send_payment_link"
    )


def test_single_action_404_for_missing_action():
    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-actions/does_not_exist"
        )

    assert response.status_code == 404


def test_case_audit_endpoint():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/case_a1/audit"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == "case_a1"
    assert data["count"] == 2
    assert (
        data["audit_logs"][0]["event_type"]
        == "ai_decision_created"
    )

def test_case_detail_includes_policy_and_ai_data():
    asyncio.run(seed_case())

    with TestClient(app) as client:
        response = client.get(
            "/api/recovery-cases/case_a1"
        )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["case"]["last_ai_decision"][
            "recommended_action"
        ]
        == "retry_later"
    )

    assert (
        data["case"]["last_policy_verdict"][
            "final_action"
        ]
        == "retry_later"
    )