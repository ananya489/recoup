import asyncio
import logging
from typing import Optional

from app.recovery.razorpay_client import (
    RazorpayClientProtocol,
    get_razorpay_client,
)


logger = logging.getLogger("recoup.executor")


# These actions do not have a real execution API in our
# current system, so they are explicitly simulations.
SIMULATED_ACTIONS = {
    "retry_now",
    "retry_later",
    "send_reminder_only",
}


# This action has a real Razorpay Payment Links API behind it.
REAL_ACTIONS = {
    "send_payment_link",
}


ACTIONABLE_ACTIONS = (
    SIMULATED_ACTIONS
    | REAL_ACTIONS
)


EXTERNAL_CALL_TIMEOUT_SECONDS = 15.0


async def execute_action(
    action_type: str,
    case_id: str,
    amount_paise: int,
    customer_contact: Optional[str],
    client: Optional[RazorpayClientProtocol] = None,
) -> dict:
    """
    Execute exactly one bounded recovery action.

    Returns:

        {
            "status": "executed" | "failed",
            "provider_reference": str | None,
            "result": dict,
            "error": str | None
        }

    IMPORTANT:
    Simulated actions are explicitly marked simulated=True.

    Real Razorpay actions are only marked executed after
    a valid provider response is received.
    """

    # ---------------------------------------------------------
    # REAL ACTION: Razorpay Payment Link
    # ---------------------------------------------------------

    if action_type == "send_payment_link":

        razorpay = (
            client
            or get_razorpay_client()
        )

        try:
            response = await asyncio.wait_for(
                razorpay.create_payment_link(
                    amount_paise=amount_paise,
                    case_id=case_id,
                    contact=customer_contact,
                ),
                timeout=EXTERNAL_CALL_TIMEOUT_SECONDS,
            )

        except asyncio.TimeoutError:

            logger.warning(
                "razorpay_payment_link_timeout case_id=%s",
                case_id,
            )

            return {
                "status": "failed",
                "provider_reference": None,
                "result": {
                    "simulated": False,
                },
                "error": (
                    "razorpay payment link "
                    "request timed out"
                ),
            }

        except Exception as exc:

            logger.warning(
                "razorpay_payment_link_failed "
                "case_id=%s error_type=%s",
                case_id,
                type(exc).__name__,
            )

            return {
                "status": "failed",
                "provider_reference": None,
                "result": {
                    "simulated": False,
                },
                "error": (
                    f"{type(exc).__name__}: "
                    "razorpay payment link creation failed"
                ),
            }

        # We require both provider ID and URL before
        # calling the action successful.
        link_id = response.get("id")
        short_url = response.get("short_url")

        if not link_id or not short_url:

            return {
                "status": "failed",
                "provider_reference": None,
                "result": {
                    "simulated": False,
                    "raw_response": response,
                },
                "error": (
                    "razorpay response missing "
                    "id/short_url; treating as unconfirmed"
                ),
            }

        return {
            "status": "executed",
            "provider_reference": link_id,
            "result": {
                "simulated": False,
                "short_url": short_url,
            },
            "error": None,
        }

    # ---------------------------------------------------------
    # SIMULATED ACTIONS
    # ---------------------------------------------------------

    if action_type in SIMULATED_ACTIONS:

        return {
            "status": "executed",
            "provider_reference": None,
            "result": {
                "simulated": True,
                "note": (
                    f"'{action_type}' has no corresponding "
                    "real Razorpay API in this system; "
                    "recorded as a simulated action only."
                ),
            },
            "error": None,
        }

    # ---------------------------------------------------------
    # Unsupported action
    # ---------------------------------------------------------

    return {
        "status": "failed",
        "provider_reference": None,
        "result": {
            "simulated": False,
        },
        "error": (
            f"unsupported action_type: "
            f"{action_type}"
        ),
    }