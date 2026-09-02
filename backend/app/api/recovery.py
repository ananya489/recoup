from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.ai.analyzer import analyze_failure
from app.audit.logger import write_audit_log
from app.db.mongo import get_db
from app.policy.engine import evaluate_policy
from app.recovery import actions_repository
from app.recovery.executor import (
    ACTIONABLE_ACTIONS,
    execute_action,
)
from app.recovery.scoring import compute_recovery_score


router = APIRouter(
    prefix="/api/recovery-cases"
)


_TERMINAL_STATUS_FOR_REASON = {
    "RECOVERY_WINDOW_EXPIRED": "expired",
    "MAX_RETRIES_HIT": "escalated",
    "LLM_OUTPUT_INVALID": "escalated",
    "LOW_CONFIDENCE": "escalated",
    "HIGH_VALUE_REQUIRES_HUMAN": "escalated",
    "AMOUNT_EXCEEDS_AUTO_CEILING": "escalated",
    "LLM_FLAGGED_HIGH_RISK": "escalated",
}


@router.post("/{case_id}/evaluate")
async def evaluate_case(case_id: str):
    """
    Run the Batch 2 evaluation pipeline:

    recovery score
        ↓
    AI recommendation
        ↓
    deterministic policy
        ↓
    persist result
        ↓
    audit

    IMPORTANT:
    This endpoint does NOT execute any financial action.
    """

    db = get_db()

    # ---------------------------------------------------------
    # 1. Find recovery case
    # ---------------------------------------------------------

    case = await db.recovery_cases.find_one(
        {"_id": case_id}
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="recovery case not found",
        )

    # ---------------------------------------------------------
    # 2. Find related payment
    # ---------------------------------------------------------

    payment = await db.payments.find_one(
        {"_id": case["payment_id"]}
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="payment not found for case",
        )

    failure_event_count = case.get(
        "failure_event_count",
        1,
    )

    # ---------------------------------------------------------
    # 3. Calculate deterministic recovery score
    # ---------------------------------------------------------

    score = compute_recovery_score(
        amount_paise=case["amount_paise"],
        payment_method=payment.get(
            "method",
            "unknown",
        ),
        failure_event_count=failure_event_count,
        first_failure_at=case.get(
            "first_failure_at"
        ),
        case_status=case["status"],
    )

    # ---------------------------------------------------------
    # 4. Build AI failure context
    # ---------------------------------------------------------

    failure_context = {
        "amount_paise": case["amount_paise"],
        "payment_method": payment.get("method"),
        "error_code": payment.get("error_code"),
        "error_description": payment.get(
            "error_description"
        ),
        "failure_event_count": failure_event_count,
        "recovery_score": score.score,
    }

    # ---------------------------------------------------------
    # 5. Ask AI for recommendation
    # ---------------------------------------------------------

    decision = await analyze_failure(
        case_id=case_id,
        failure_context=failure_context,
    )

    if decision is not None:
        await write_audit_log(
            event_type="ai_decision_created",
            actor="ai_analyzer",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "failure_category": (
                    decision.failure_category.value
                ),
                "confidence": decision.confidence,
                "recommended_action": (
                    decision.recommended_action.value
                ),
                "risk_level": (
                    decision.risk_level.value
                ),
            },
        )

    else:
        await write_audit_log(
            event_type="ai_fallback_used",
            actor="ai_analyzer",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "reason": (
                    "LLM call failed, timed out, "
                    "or returned invalid output"
                ),
            },
        )

    # ---------------------------------------------------------
    # 6. Run deterministic policy engine
    # ---------------------------------------------------------

    verdict = evaluate_policy(
        decision=decision,
        case_id=case_id,
        case_status=case["status"],
        amount_paise=case["amount_paise"],
        payment_status=payment["status"],
        failure_event_count=failure_event_count,
        first_failure_at=case.get(
            "first_failure_at"
        ),
        last_action_at=case.get(
            "last_action_at"
        ),
        has_action_in_flight=(
            await actions_repository.has_action_in_flight(
                case_id
            )
        ),
    )

    await write_audit_log(
        event_type="policy_evaluated",
        actor="policy_engine",
        entity_type="recovery_case",
        entity_id=case_id,
        metadata={
            "reason_code": verdict.reason_code,
            "approved": verdict.approved,
            "final_action": (
                verdict.final_action.value
            ),
        },
    )

    # ---------------------------------------------------------
    # 7. Audit escalation / blocking
    # ---------------------------------------------------------

    if (
        verdict.final_action.value
        == "escalate_to_human"
    ):
        await write_audit_log(
            event_type="human_approval_required",
            actor="policy_engine",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "reason_code": verdict.reason_code,
            },
        )

    elif (
        not verdict.approved
        and verdict.final_action.value == "stop"
    ):
        await write_audit_log(
            event_type="action_blocked",
            actor="policy_engine",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "reason_code": verdict.reason_code,
            },
        )

    # ---------------------------------------------------------
    # 8. Determine resulting case state
    # ---------------------------------------------------------

    if verdict.reason_code == "OK":

        if verdict.final_action.value == "stop":
            new_status = "stopped"
        else:
            new_status = "action_pending"

    else:

        new_status = _TERMINAL_STATUS_FOR_REASON.get(
            verdict.reason_code,
            case["status"],
        )

    # ---------------------------------------------------------
    # 9. Persist evaluation
    # ---------------------------------------------------------

    now = datetime.now(timezone.utc)

    await db.recovery_cases.update_one(
        {"_id": case_id},
        {
            "$set": {
                "status": new_status,
                "last_ai_decision": (
                    decision.model_dump()
                    if decision is not None
                    else None
                ),
                "last_policy_verdict": (
                    verdict.model_dump()
                ),
                "last_evaluated_at": now,
                "updated_at": now,
            }
        },
    )

    # ---------------------------------------------------------
    # 10. Return evaluation result
    # ---------------------------------------------------------

    return {
        "case_id": case_id,
        "recovery_score": score.model_dump(),
        "ai_decision": (
            decision.model_dump()
            if decision is not None
            else None
        ),
        "policy_verdict": (
            verdict.model_dump()
        ),
        "case_status": new_status,
    }


@router.post("/{case_id}/execute")
async def execute_case_action(case_id: str):
    """
    Execute exactly the action approved by the last
    policy evaluation.

    The caller cannot choose the action.

    The stored PolicyVerdict is the source of truth.
    """

    db = get_db()

    # ---------------------------------------------------------
    # 1. Find recovery case
    # ---------------------------------------------------------

    case = await db.recovery_cases.find_one(
        {"_id": case_id}
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="recovery case not found",
        )

    # ---------------------------------------------------------
    # 2. Case must be evaluated first
    # ---------------------------------------------------------

    verdict = case.get(
        "last_policy_verdict"
    )

    if verdict is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "case has not been evaluated yet; "
                "call /evaluate first"
            ),
        )

    # ---------------------------------------------------------
    # 3. Get action from stored policy verdict
    # ---------------------------------------------------------

    final_action = verdict["final_action"]

    # ---------------------------------------------------------
    # 4. Never execute non-actionable decisions
    # ---------------------------------------------------------

    if final_action not in ACTIONABLE_ACTIONS:

        await write_audit_log(
            event_type="action_blocked",
            actor="recovery_executor",
            entity_type="recovery_case",
            entity_id=case_id,
            metadata={
                "reason": (
                    f"final_action '{final_action}' "
                    "is not executable"
                ),
                "final_action": final_action,
            },
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"final_action '{final_action}' "
                "is not an actionable recovery action"
            ),
        )

    # ---------------------------------------------------------
    # 5. Prevent concurrent action execution
    # ---------------------------------------------------------

    if await actions_repository.has_action_in_flight(
        case_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "an action is already in flight "
                "for this case"
            ),
        )

    # ---------------------------------------------------------
    # 6. Create deterministic idempotency key
    # ---------------------------------------------------------

    idempotency_key = (
        f"{case_id}:"
        f"{case['last_evaluated_at'].isoformat()}:"
        f"{final_action}"
    )

    # ---------------------------------------------------------
    # 7. Persist requested action BEFORE execution
    # ---------------------------------------------------------

    action_doc = (
        await actions_repository.create_requested_action(
            idempotency_key=idempotency_key,
            case_id=case_id,
            action_type=final_action,
            amount_paise=case["amount_paise"],
            approved_by=(
                f"policy_engine:"
                f"{verdict['policy_version']}"
            ),
        )
    )

    # ---------------------------------------------------------
    # 8. Duplicate execute request
    # ---------------------------------------------------------

    if action_doc is None:

        existing = (
            await actions_repository.get_action(
                idempotency_key
            )
        )

        return {
            "case_id": case_id,
            "action": existing,
            "duplicate_request": True,
        }

    # ---------------------------------------------------------
    # 9. Audit requested action
    # ---------------------------------------------------------

    await write_audit_log(
        event_type="action_requested",
        actor="recovery_executor",
        entity_type="recovery_case",
        entity_id=case_id,
        metadata={
            "action_type": final_action,
            "idempotency_key": idempotency_key,
        },
    )

    # ---------------------------------------------------------
    # 10. Execute bounded recovery action
    # ---------------------------------------------------------

    outcome = await execute_action(
        action_type=final_action,
        case_id=case_id,
        amount_paise=case["amount_paise"],
        customer_contact=case.get(
            "customer_contact"
        ),
    )

    # ---------------------------------------------------------
    # 11. Persist execution result
    # ---------------------------------------------------------

    await actions_repository.finalize_action(
        idempotency_key=idempotency_key,
        status=outcome["status"],
        provider_reference=(
            outcome["provider_reference"]
        ),
        result=outcome["result"],
        error=outcome["error"],
    )

    # ---------------------------------------------------------
    # 12. Audit execution result
    # ---------------------------------------------------------

    audit_event = (
        "action_executed"
        if outcome["status"] == "executed"
        else "action_failed"
    )

    await write_audit_log(
        event_type=audit_event,
        actor="recovery_executor",
        entity_type="recovery_case",
        entity_id=case_id,
        metadata={
            "action_type": final_action,
            "provider_reference": (
                outcome["provider_reference"]
            ),
            "simulated": (
                outcome["result"].get(
                    "simulated"
                )
            ),
            "error": outcome["error"],
        },
    )

    # ---------------------------------------------------------
    # 13. Update case state
    # ---------------------------------------------------------

    new_case_status = (
        "action_executed"
        if outcome["status"] == "executed"
        else "action_failed"
    )

    now = datetime.now(timezone.utc)

    await db.recovery_cases.update_one(
        {"_id": case_id},
        {
            "$set": {
                "status": new_case_status,
                "last_action_at": now,
                "updated_at": now,
            }
        },
    )

    # ---------------------------------------------------------
    # 14. Return final action document
    # ---------------------------------------------------------

    final_action_doc = (
        await actions_repository.get_action(
            idempotency_key
        )
    )

    return {
        "case_id": case_id,
        "action": final_action_doc,
        "duplicate_request": False,
        "case_status": new_case_status,
    }