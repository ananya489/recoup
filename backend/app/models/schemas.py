from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    insufficient_funds = "insufficient_funds"
    bank_timeout = "bank_timeout"
    invalid_card_or_expired = "invalid_card_or_expired"
    otp_or_auth_failure = "otp_or_auth_failure"
    mandate_cancelled = "mandate_cancelled"
    gateway_or_network_error = "gateway_or_network_error"
    suspected_fraud_block = "suspected_fraud_block"
    unknown = "unknown"


class RecommendedAction(str, Enum):
    retry_now = "retry_now"
    retry_later = "retry_later"
    send_payment_link = "send_payment_link"
    send_reminder_only = "send_reminder_only"
    escalate_to_human = "escalate_to_human"
    stop = "stop"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class CaseStatus(str, Enum):
    open = "open"
    action_pending = "action_pending"
    action_executed = "action_executed"
    action_failed = "action_failed"
    recovered = "recovered"
    expired = "expired"
    escalated = "escalated"
    stopped = "stopped"


class RecoveryDecision(BaseModel):
    case_id: str
    failure_category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: RecommendedAction
    suggested_retry_window_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=168,
    )
    reasoning: str = Field(max_length=400)
    risk_level: RiskLevel
    requires_human_approval: bool
    model_name: str
    prompt_version: str


class PolicyVerdict(BaseModel):
    case_id: str
    decision_id: str
    approved: bool
    reason_code: str
    final_action: RecommendedAction
    policy_version: str


class Payment(BaseModel):
    id: str
    razorpay_order_id: Optional[str] = None
    customer_id: str
    amount_paise: int = Field(gt=0)
    currency: str = "INR"
    method: str
    status: str
    error_code: Optional[str] = None
    error_description: Optional[str] = None


class Customer(BaseModel):
    id: str
    name: str
    email: str
    contact: str
    account_age_days: int = Field(ge=0)
    ltv_paise: int = Field(ge=0)
    prior_failures_90d: int = Field(ge=0)
    prior_chargebacks: int = Field(ge=0)
    segment: str


class RecoveryCase(BaseModel):
    id: str
    payment_id: str
    customer_contact: Optional[str] = None
    amount_paise: int = Field(gt=0)
    status: CaseStatus = CaseStatus.open
    auto_retry_count: int = Field(default=0, ge=0)
    first_failure_at: Optional[datetime] = None
    recovered_at: Optional[datetime] = None
    recovered_amount_paise: Optional[int] = None
    updated_at: Optional[datetime] = None


class ProcessingStatus(str, Enum):
    stored = "stored"
    processed = "processed"
    failed = "failed"
    skipped = "skipped"


class WebhookEvent(BaseModel):
    event_id: str
    event_type: str
    received_at: datetime
    signature_verified: bool
    processing_status: ProcessingStatus = ProcessingStatus.stored
    attempts: int = Field(default=1, ge=1)
    error: Optional[str] = None
    processed_at: Optional[datetime] = None


class AuditLog(BaseModel):
    event_type: str
    actor: str
    entity_type: str
    entity_id: str
    metadata: dict = {}
    timestamp: datetime


class ActionStatus(str, Enum):
    requested = "requested"
    executed = "executed"
    failed = "failed"
    skipped = "skipped"


class RecoveryAction(BaseModel):
    idempotency_key: str
    case_id: str
    action_type: RecommendedAction
    amount_paise: int = Field(gt=0)
    status: ActionStatus = ActionStatus.requested
    requested_by: str = "policy_engine"
    approved_by: str
    requested_at: datetime
    executed_at: Optional[datetime] = None
    provider_reference: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None