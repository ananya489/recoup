import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.recovery.executor import execute_action
from app.recovery.razorpay_client import MockRazorpayClient


@pytest.mark.asyncio
async def test_send_payment_link_success_is_never_labeled_simulated():
    client = MockRazorpayClient(should_fail=False)

    result = await execute_action(
        action_type="send_payment_link",
        case_id="case_1",
        amount_paise=99900,
        customer_contact="+919900011122",
        client=client,
    )

    assert result["status"] == "executed"
    assert result["provider_reference"].startswith(
        "plink_mock_"
    )
    assert result["result"]["simulated"] is False
    assert result["error"] is None


@pytest.mark.asyncio
async def test_send_payment_link_provider_failure_never_claims_success():
    client = MockRazorpayClient(
        should_fail=True
    )

    result = await execute_action(
        action_type="send_payment_link",
        case_id="case_1",
        amount_paise=99900,
        customer_contact="+919900011122",
        client=client,
    )

    assert result["status"] == "failed"
    assert result["provider_reference"] is None
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_send_payment_link_missing_confirmation_is_treated_as_failure():

    class IncompleteResponseClient:
        async def create_payment_link(
            self,
            amount_paise,
            case_id,
            contact,
        ):
            return {
                "status": "created"
            }

    result = await execute_action(
        action_type="send_payment_link",
        case_id="case_1",
        amount_paise=99900,
        customer_contact=None,
        client=IncompleteResponseClient(),
    )

    assert result["status"] == "failed"
    assert result["provider_reference"] is None
    assert "unconfirmed" in result["error"]


@pytest.mark.asyncio
async def test_send_payment_link_timeout_never_claims_success():
    import asyncio

    class SlowClient:
        async def create_payment_link(
            self,
            amount_paise,
            case_id,
            contact,
        ):
            await asyncio.sleep(1.0)

            return {
                "id": "plink_x",
                "short_url": "https://rzp.io/x",
            }

    import app.recovery.executor as executor_module

    original_timeout = (
        executor_module.EXTERNAL_CALL_TIMEOUT_SECONDS
    )

    executor_module.EXTERNAL_CALL_TIMEOUT_SECONDS = 0.05

    try:
        result = await execute_action(
            action_type="send_payment_link",
            case_id="case_1",
            amount_paise=99900,
            customer_contact=None,
            client=SlowClient(),
        )
    finally:
        executor_module.EXTERNAL_CALL_TIMEOUT_SECONDS = (
            original_timeout
        )

    assert result["status"] == "failed"
    assert "timed out" in result["error"]


@pytest.mark.asyncio
async def test_retry_later_is_explicitly_labeled_simulated():
    result = await execute_action(
        action_type="retry_later",
        case_id="case_1",
        amount_paise=99900,
        customer_contact=None,
    )

    assert result["status"] == "executed"
    assert result["result"]["simulated"] is True
    assert result["provider_reference"] is None


@pytest.mark.asyncio
async def test_send_reminder_only_is_explicitly_labeled_simulated():
    result = await execute_action(
        action_type="send_reminder_only",
        case_id="case_1",
        amount_paise=99900,
        customer_contact="+91900",
    )

    assert result["status"] == "executed"
    assert result["result"]["simulated"] is True


@pytest.mark.asyncio
async def test_unsupported_action_type_fails_cleanly():
    result = await execute_action(
        action_type="teleport_the_money",
        case_id="case_1",
        amount_paise=99900,
        customer_contact=None,
    )

    assert result["status"] == "failed"
    assert "unsupported" in result["error"]