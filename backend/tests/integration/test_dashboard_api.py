import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

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


def test_dashboard_summary_empty_system_returns_zeros():
    with TestClient(app) as client:
        response = client.get(
            "/api/dashboard/summary"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["cases"]["total"] == 0
    assert data["revenue"]["at_risk_paise"] == 0
    assert data["revenue"]["recovered_paise"] == 0
    assert data["revenue"]["recovery_rate"] == 0.0
    assert data["actions"]["total"] == 0
    assert data["recent_actions"] == []


def test_dashboard_aggregation_correctness_from_live_data():
    async def seed():
        db = mongo_module.get_db()

        await db.recovery_cases.insert_many(
            [
                {
                    "_id": "c1",
                    "payment_id": "p1",
                    "amount_paise": 100000,
                    "status": "recovered",
                    "recovered_amount_paise": 100000,
                    "updated_at": NOW,
                },
                {
                    "_id": "c2",
                    "payment_id": "p2",
                    "amount_paise": 50000,
                    "status": "recovered",
                    "recovered_amount_paise": 50000,
                    "updated_at": NOW,
                },
                {
                    "_id": "c3",
                    "payment_id": "p3",
                    "amount_paise": 75000,
                    "status": "open",
                    "updated_at": NOW,
                },
                {
                    "_id": "c4",
                    "payment_id": "p4",
                    "amount_paise": 25000,
                    "status": "escalated",
                    "updated_at": NOW,
                },
                {
                    "_id": "c5",
                    "payment_id": "p5",
                    "amount_paise": 10000,
                    "status": "stopped",
                    "updated_at": NOW,
                },
                {
                    "_id": "c6",
                    "payment_id": "p6",
                    "amount_paise": 15000,
                    "status": "action_failed",
                    "updated_at": NOW,
                },
            ]
        )

        await db.recovery_actions.insert_one(
            {
                "_id": "act1",
                "case_id": "c1",
                "action_type": "send_payment_link",
                "status": "executed",
                "requested_at": NOW,
            }
        )

    asyncio.run(seed())

    with TestClient(app) as client:
        response = client.get(
            "/api/dashboard/summary"
        )

    assert response.status_code == 200

    data = response.json()

    # ---------------------------------------------------------
    # Case counts
    # ---------------------------------------------------------

    assert data["cases"]["total"] == 6
    assert data["cases"]["recovered"] == 2
    assert data["cases"]["escalated"] == 1
    assert data["cases"]["stopped"] == 1
    assert data["cases"]["action_failed"] == 1
    assert data["cases"]["open"] == 1

    # ---------------------------------------------------------
    # Recovered revenue
    #
    # c1 + c2
    # = 100000 + 50000
    # = 150000 paise
    # ---------------------------------------------------------

    assert (
        data["revenue"]["recovered_paise"]
        == 150000
    )

    # ---------------------------------------------------------
    # Revenue at risk
    #
    # open       = 75000
    # escalated  = 25000
    # action_failed = 15000
    #
    # recovered and stopped are excluded.
    #
    # Total = 115000 paise
    # ---------------------------------------------------------

    assert (
        data["revenue"]["at_risk_paise"]
        == 115000
    )

    # ---------------------------------------------------------
    # Recovery rate
    #
    # API rounds to 4 decimal places:
    #
    # 2 / 6 = 0.333333...
    # rounded = 0.3333
    # ---------------------------------------------------------

    assert (
        data["revenue"]["recovery_rate"]
        == round(2 / 6, 4)
    )

    # ---------------------------------------------------------
    # Action counts
    # ---------------------------------------------------------

    assert data["actions"]["total"] == 1
    assert data["actions"]["executed"] == 1
    assert data["actions"]["failed"] == 0
    assert data["actions"]["requested"] == 0

    # ---------------------------------------------------------
    # Recent actions
    # ---------------------------------------------------------

    assert len(
        data["recent_actions"]
    ) == 1

    assert (
        data["recent_actions"][0]["case_id"]
        == "c1"
    )