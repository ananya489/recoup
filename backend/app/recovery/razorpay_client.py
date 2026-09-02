from typing import Optional, Protocol

import httpx

from app.config import settings


class RazorpayClientProtocol(Protocol):
    async def create_payment_link(
        self,
        amount_paise: int,
        case_id: str,
        contact: Optional[str],
    ) -> dict:
        ...


class RazorpayHTTPClient:
    """
    Real Razorpay Test Mode Payment Links client.

    This uses the Razorpay API credentials:
        RAZORPAY_KEY_ID
        RAZORPAY_KEY_SECRET

    It does NOT use the webhook secret.
    """

    BASE_URL = "https://api.razorpay.com/v1/payment_links"

    def __init__(
        self,
        key_id: str,
        key_secret: str,
    ):
        self.key_id = key_id
        self.key_secret = key_secret

    async def create_payment_link(
        self,
        amount_paise: int,
        case_id: str,
        contact: Optional[str],
    ) -> dict:

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": (
                f"Recoup recovery link for case {case_id}"
            ),
            "notes": {
                "recovery_case_id": case_id
            },
            "notify": {
                "sms": bool(contact),
                "email": False,
            },
        }

        if contact:
            payload["customer"] = {
                "contact": contact
            }

        async with httpx.AsyncClient(
            timeout=15.0,
            auth=(self.key_id, self.key_secret),
        ) as client:

            response = await client.post(
                self.BASE_URL,
                json=payload,
            )

            response.raise_for_status()

            return response.json()


class MockRazorpayClient:
    """
    Local fake Razorpay client for testing.

    Never calls the real Razorpay API.
    """

    def __init__(
        self,
        should_fail: bool = False,
    ):
        self.should_fail = should_fail
        self._counter = 0

    async def create_payment_link(
        self,
        amount_paise: int,
        case_id: str,
        contact: Optional[str],
    ) -> dict:

        if self.should_fail:
            raise ConnectionError(
                "simulated razorpay outage"
            )

        self._counter += 1

        return {
            "id": f"plink_mock_{self._counter}",
            "short_url": (
                f"https://rzp.io/mock/{case_id}"
            ),
            "amount": amount_paise,
            "status": "created",
        }


def get_razorpay_client() -> RazorpayClientProtocol:
    return RazorpayHTTPClient(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
    )