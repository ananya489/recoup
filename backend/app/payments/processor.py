from datetime import datetime, timezone

from app.audit.logger import write_audit_log
from app.db.mongo import get_db


def _case_id_for(payment_id: str) -> str:
    """
    Create a deterministic recovery-case ID from the payment ID.

    One payment gets exactly one recovery case.
    """
    return f"case_{payment_id}"


async def process_payment_failed(payload: dict) -> None:
    """
    Process a verified payment.failed webhook.

    Behavior:
    - Store/update the payment as failed.
    - Create a recovery case if one does not exist.
    - Do not reopen a payment that is already captured.
    - Record audit events.
    """

    entity = payload["payload"]["payment"]["entity"]

    payment_id = entity["id"]
    db = get_db()
    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # 1. Check whether this payment was already captured.
    # ---------------------------------------------------------

    existing_payment = await db.payments.find_one(
        {"_id": payment_id}
    )

    if (
        existing_payment is not None
        and existing_payment.get("status") == "captured"
    ):
        await write_audit_log(
            event_type="stale_failure_ignored",
            actor="payment_processor",
            entity_type="payment",
            entity_id=payment_id,
            metadata={
                "reason": (
                    "payment already captured; "
                    "out-of-order payment.failed ignored"
                )
            },
        )
        return

    # ---------------------------------------------------------
    # 2. Update/create payment as failed.
    # ---------------------------------------------------------

    await db.payments.update_one(
        {"_id": payment_id},
        {
            "$set": {
                "amount_paise": entity.get("amount"),
                "currency": entity.get(
                    "currency",
                    "INR",
                ),
                "status": "failed",
                "method": entity.get("method"),
                "order_id": entity.get("order_id"),
                "error_code": entity.get(
                    "error_code"
                ),
                "error_description": entity.get(
                    "error_description"
                ),
                "contact": entity.get("contact"),
                "email": entity.get("email"),
                "updated_at": now,
                "failed_at": now,
            }
        },
        upsert=True,
    )

    await write_audit_log(
        event_type="payment_updated",
        actor="payment_processor",
        entity_type="payment",
        entity_id=payment_id,
        metadata={
            "status": "failed",
        },
    )

    # ---------------------------------------------------------
    # 3. Create/update exactly one recovery case.
    # ---------------------------------------------------------

    case_id = _case_id_for(payment_id)

    result = await db.recovery_cases.update_one(
        {"_id": case_id},
        {
            "$setOnInsert": {
                "_id": case_id,
                "payment_id": payment_id,
                "customer_contact": entity.get(
                    "contact"
                ),
                "amount_paise": entity.get(
                    "amount"
                ),
                "status": "open",
                "auto_retry_count": 0,
                "first_failure_at": now,
                "recovered_at": None,
                "recovered_amount_paise": None,
            },
            "$set": {
                "updated_at": now,
            },
            "$inc": {
                "failure_event_count": 1,
            },
        },
        upsert=True,
    )

    if result.upserted_id is not None:
        audit_event = "recovery_case_created"
    else:
        audit_event = "recovery_case_updated"

    await write_audit_log(
        event_type=audit_event,
        actor="payment_processor",
        entity_type="recovery_case",
        entity_id=case_id,
        metadata={
            "payment_id": payment_id,
        },
    )


async def process_payment_captured(payload: dict) -> None:
    """
    Process a verified payment.captured webhook.

    Behavior:
    - Mark the payment as captured.
    - Find the related recovery case.
    - Support Payment Link captures where Razorpay gives
      the successful payment a new payment_id.
    - Mark the recovery case recovered exactly once.
    - Never double-count recovered revenue.
    """

    entity = payload["payload"]["payment"]["entity"]

    payment_id = entity["id"]
    captured_amount = entity.get("amount")

    db = get_db()
    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # 1. Update/create the payment as captured.
    # ---------------------------------------------------------

    await db.payments.update_one(
        {"_id": payment_id},
        {
            "$set": {
                "amount_paise": captured_amount,
                "currency": entity.get(
                    "currency",
                    "INR",
                ),
                "status": "captured",
                "method": entity.get("method"),
                "order_id": entity.get("order_id"),
                "captured_amount_paise": captured_amount,
                "contact": entity.get("contact"),
                "email": entity.get("email"),
                "updated_at": now,
                "captured_at": now,
            }
        },
        upsert=True,
    )

    await write_audit_log(
        event_type="payment_updated",
        actor="payment_processor",
        entity_type="payment",
        entity_id=payment_id,
        metadata={
            "status": "captured",
        },
    )

    # ---------------------------------------------------------
    # 2. Normal case lookup.
    #
    # Normally the captured payment belongs to:
    #     case_<payment_id>
    # ---------------------------------------------------------

    case_id = _case_id_for(payment_id)

    case = await db.recovery_cases.find_one(
        {"_id": case_id}
    )

    # ---------------------------------------------------------
    # 3. Payment Link fallback.
    #
    # Payment Links can create a NEW payment ID when
    # the customer pays.
    #
    # We stored the original recovery case ID in:
    #
    #     notes.recovery_case_id
    #
    # when the Payment Link was created.
    # ---------------------------------------------------------

    if case is None:
        notes = entity.get("notes") or {}

        linked_case_id = notes.get(
            "recovery_case_id"
        )

        if linked_case_id:
            case = await db.recovery_cases.find_one(
                {"_id": linked_case_id}
            )

            if case is not None:
                case_id = linked_case_id

    # ---------------------------------------------------------
    # 4. No recovery case.
    #
    # This was simply a successful payment that did not
    # originate from a recovery workflow.
    # ---------------------------------------------------------

    if case is None:
        return

    # ---------------------------------------------------------
    # 5. Already recovered.
    #
    # Prevent double-counting if the same capture is
    # processed again.
    # ---------------------------------------------------------

    if case.get("status") == "recovered":
        await write_audit_log(
            event_type="duplicate_capture_ignored",
            actor="payment_processor",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "payment_id": payment_id,
                "reason": (
                    "case already recovered; "
                    "not double-counting"
                ),
            },
        )
        return

    # ---------------------------------------------------------
    # 6. Mark recovery case as recovered.
    # ---------------------------------------------------------

    await db.recovery_cases.update_one(
        {"_id": case_id},
        {
            "$set": {
                "status": "recovered",
                "recovered_at": now,
                "recovered_amount_paise": captured_amount,
                "updated_at": now,
            }
        },
    )

    # ---------------------------------------------------------
    # 7. Audit recovered revenue.
    # ---------------------------------------------------------

    await write_audit_log(
        event_type="payment_recovered",
        actor="payment_processor",
        entity_type="recovery_case",
        entity_id=case_id,
        metadata={
            "payment_id": payment_id,
            "recovered_amount_paise": captured_amount,
        },
    )