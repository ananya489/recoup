import pytest
from mongomock_motor import AsyncMongoMockClient

import app.db.mongo as mongo_module
from app.payments.processor import (
    process_payment_captured,
    process_payment_failed,
)


@pytest.fixture(autouse=True)
def use_mock_mongo():
    mongo_module._client = AsyncMongoMockClient(
        tz_aware=True
    )

    yield

    mongo_module._client = None


def _failed_payload(
    payment_id="pay_A1",
    amount=99900,
    contact="+919900011122",
):
    return {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi",
                    "order_id": "order_1",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Insufficient balance.",
                    "contact": contact,
                    "email": "rohan@example.com",
                }
            }
        },
    }


def _captured_payload(
    payment_id="pay_A1",
    amount=99900,
    contact="+919900011122",
):
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "order_id": "order_1",
                    "contact": contact,
                    "email": "rohan@example.com",
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_payment_failed_creates_payment_and_open_case():
    await process_payment_failed(
        _failed_payload()
    )

    db = mongo_module.get_db()

    payment = await db.payments.find_one(
        {"_id": "pay_A1"}
    )

    assert payment["status"] == "failed"
    assert payment["amount_paise"] == 99900

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_A1"}
    )

    assert case["status"] == "open"
    assert case["payment_id"] == "pay_A1"
    assert case["recovered_at"] is None


@pytest.mark.asyncio
async def test_payment_captured_after_failed_marks_case_recovered():
    await process_payment_failed(
        _failed_payload()
    )

    await process_payment_captured(
        _captured_payload()
    )

    db = mongo_module.get_db()

    payment = await db.payments.find_one(
        {"_id": "pay_A1"}
    )

    assert payment["status"] == "captured"
    assert payment["captured_amount_paise"] == 99900

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_A1"}
    )

    assert case["status"] == "recovered"
    assert case["recovered_amount_paise"] == 99900
    assert case["recovered_at"] is not None


@pytest.mark.asyncio
async def test_payment_captured_without_prior_failure_creates_no_case():
    await process_payment_captured(
        _captured_payload(
            payment_id="pay_B2"
        )
    )

    db = mongo_module.get_db()

    payment = await db.payments.find_one(
        {"_id": "pay_B2"}
    )

    assert payment["status"] == "captured"

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_B2"}
    )

    assert case is None


@pytest.mark.asyncio
async def test_out_of_order_failed_after_captured_does_not_reopen_case():
    await process_payment_captured(
        _captured_payload(
            payment_id="pay_C3"
        )
    )

    await process_payment_failed(
        _failed_payload(
            payment_id="pay_C3"
        )
    )

    db = mongo_module.get_db()

    payment = await db.payments.find_one(
        {"_id": "pay_C3"}
    )

    assert payment["status"] == "captured"

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_C3"}
    )

    assert case is None


@pytest.mark.asyncio
async def test_duplicate_captured_event_does_not_double_count_revenue():
    await process_payment_failed(
        _failed_payload(
            payment_id="pay_D4"
        )
    )

    await process_payment_captured(
        _captured_payload(
            payment_id="pay_D4",
            amount=50000,
        )
    )

    await process_payment_captured(
        _captured_payload(
            payment_id="pay_D4",
            amount=50000,
        )
    )

    db = mongo_module.get_db()

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_D4"}
    )

    assert case["status"] == "recovered"
    assert case["recovered_amount_paise"] == 50000


@pytest.mark.asyncio
async def test_multiple_failures_increment_failure_event_count():
    await process_payment_failed(
        _failed_payload(
            payment_id="pay_E5"
        )
    )

    await process_payment_failed(
        _failed_payload(
            payment_id="pay_E5"
        )
    )

    db = mongo_module.get_db()

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_E5"}
    )

    assert case["failure_event_count"] == 2
    assert case["status"] == "open"


@pytest.mark.asyncio
async def test_audit_log_entries_are_written_for_recovery():
    await process_payment_failed(
        _failed_payload(
            payment_id="pay_F6"
        )
    )

    await process_payment_captured(
        _captured_payload(
            payment_id="pay_F6"
        )
    )

    db = mongo_module.get_db()

    events = [
        doc["event_type"]
        async for doc in db.audit_logs.find(
            {
                "entity_id": {
                    "$in": [
                        "pay_F6",
                        "case_pay_F6",
                    ]
                }
            }
        )
    ]

    assert "payment_updated" in events
    assert "recovery_case_created" in events
    assert "payment_recovered" in events


@pytest.mark.asyncio
async def test_payment_link_execution_then_capture_marks_case_recovered():
    """
    Payment Link recovery scenario:

    Original failed payment:
        pay_original

    Recovery case:
        case_pay_original

    Payment Link is then paid, but Razorpay gives the
    captured payment a NEW payment ID:
        pay_from_payment_link

    The captured webhook contains:
        notes.recovery_case_id = case_pay_original

    The original recovery case must be marked recovered.
    """

    # 1. Original payment fails.
    await process_payment_failed(
        {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_original",
                        "amount": 99900,
                        "currency": "INR",
                        "status": "failed",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": (
                            "Insufficient balance."
                        ),
                        "contact": "+919900011122",
                        "email": "rohan@example.com",
                    }
                }
            },
        }
    )

    db = mongo_module.get_db()

    case = await db.recovery_cases.find_one(
        {"_id": "case_pay_original"}
    )

    assert case is not None
    assert case["status"] == "open"

    # 2. Payment Link is paid.
    #
    # Important:
    # this payment has a NEW payment ID.
    await process_payment_captured(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_from_payment_link",
                        "amount": 99900,
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "contact": "+919900011122",
                        "email": "rohan@example.com",
                        "notes": {
                            "recovery_case_id": (
                                "case_pay_original"
                            )
                        },
                    }
                }
            },
        }
    )

    # 3. Original recovery case must now be recovered.
    recovered_case = await db.recovery_cases.find_one(
        {"_id": "case_pay_original"}
    )

    assert recovered_case is not None
    assert recovered_case["status"] == "recovered"
    assert (
        recovered_case["recovered_amount_paise"]
        == 99900
    )
    assert recovered_case["recovered_at"] is not None

    # 4. New captured payment must also exist.
    captured_payment = await db.payments.find_one(
        {"_id": "pay_from_payment_link"}
    )

    assert captured_payment is not None
    assert captured_payment["status"] == "captured"