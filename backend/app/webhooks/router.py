import json
import os

from fastapi import APIRouter, HTTPException, Request

from app.audit.logger import write_audit_log
from app.payments.processor import (
    process_payment_captured,
    process_payment_failed,
)
from app.webhooks.repository import store_webhook_event
from app.webhooks.verifier import verify_signature


router = APIRouter()

WEBHOOK_SECRET = os.environ.get(
    "RAZORPAY_WEBHOOK_SECRET",
    "",
)

SUPPORTED_EVENTS = {
    "payment.failed",
    "payment.captured",
}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    # 1. Read raw body first.
    raw_body = await request.body()

    # 2. Read Razorpay signature.
    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    # 3. Verify signature before parsing JSON.
    if not verify_signature(
        raw_body,
        signature,
        WEBHOOK_SECRET,
    ):
        raise HTTPException(
            status_code=400,
            detail="invalid or missing signature",
        )

    # 4. Parse JSON only after signature verification.
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="malformed json body",
        )

    # 5. Read event metadata.
    event_id = request.headers.get(
        "x-razorpay-event-id"
    )

    event_type = payload.get("event")

    if not event_id or not event_type:
        raise HTTPException(
            status_code=400,
            detail="missing event_id or event type",
        )

    # 6. Record receipt in audit log.
    await write_audit_log(
        event_type="webhook_received",
        actor="webhook_router",
        entity_type="webhook_event",
        entity_id=event_id,
        metadata={
            "razorpay_event_type": event_type,
        },
    )

    # 7. Store webhook event.
    is_new = await store_webhook_event(
        event_id=event_id,
        event_type=event_type,
        signature_verified=True,
    )

    # 8. Duplicate event → safe no-op.
    if not is_new:
        await write_audit_log(
            event_type="webhook_duplicate",
            actor="webhook_router",
            entity_type="webhook_event",
            entity_id=event_id,
            metadata={
                "razorpay_event_type": event_type,
            },
        )

        return {
            "status": "duplicate",
            "event_id": event_id,
            "event_type": event_type,
        }

    # 9. Process supported event types.
    if event_type == "payment.failed":
        await process_payment_failed(payload)

    elif event_type == "payment.captured":
        await process_payment_captured(payload)

    else:
        # Unsupported event is intentionally stored but not processed.
        await write_audit_log(
            event_type="webhook_skipped",
            actor="webhook_router",
            entity_type="webhook_event",
            entity_id=event_id,
            metadata={
                "razorpay_event_type": event_type,
                "reason": "unsupported_event",
            },
        )

        return {
            "status": "skipped",
            "event_id": event_id,
            "event_type": event_type,
        }

    # 10. Event processed successfully.
    return {
        "status": "received",
        "event_id": event_id,
        "event_type": event_type,
    }