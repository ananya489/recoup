import hashlib
import hmac
import json
import os

import pytest
from mongomock_motor import AsyncMongoMockClient

from fastapi.testclient import TestClient

os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test_local_secret_123"

import app.db.mongo as mongo_module
from app.main import app


WEBHOOK_SECRET = "test_local_secret_123"


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient()

    yield

    mongo_module._client = None


def _sample_payload_bytes() -> bytes:
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_QaBc12345",
                    "amount": 99900,
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": (
                        "Your payment could not be completed "
                        "due to insufficient balance."
                    ),
                }
            }
        },
        "created_at": 1734567890,
    }

    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def _sign(raw_body: bytes, secret: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()


def test_valid_signed_webhook_is_stored():
    body = _sample_payload_bytes()
    signature = _sign(body, WEBHOOK_SECRET)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "X-Razorpay-Signature": signature,
                "x-razorpay-event-id": "evt_int_001",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "received"
    assert data["event_id"] == "evt_int_001"
    assert data["event_type"] == "payment.failed"


def test_duplicate_webhook_is_not_stored_twice():
    body = _sample_payload_bytes()
    signature = _sign(body, WEBHOOK_SECRET)

    headers = {
        "X-Razorpay-Signature": signature,
        "x-razorpay-event-id": "evt_int_002",
        "Content-Type": "application/json",
    }

    with TestClient(app) as client:
        first = client.post(
            "/webhooks/razorpay",
            content=body,
            headers=headers,
        )

        second = client.post(
            "/webhooks/razorpay",
            content=body,
            headers=headers,
        )

    assert first.status_code == 200
    assert first.json()["status"] == "received"

    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_invalid_signature_is_rejected():
    body = _sample_payload_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "X-Razorpay-Signature": "not_a_real_signature",
                "x-razorpay-event-id": "evt_int_003",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 400


def test_missing_signature_is_rejected():
    body = _sample_payload_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "x-razorpay-event-id": "evt_int_004",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 400


def test_malformed_json_is_rejected():
    body = b"{not valid json at all"
    signature = _sign(body, WEBHOOK_SECRET)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "X-Razorpay-Signature": signature,
                "x-razorpay-event-id": "evt_int_005",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 400


def test_missing_event_id_header_is_rejected():
    body = _sample_payload_bytes()
    signature = _sign(body, WEBHOOK_SECRET)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "X-Razorpay-Signature": signature,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 400