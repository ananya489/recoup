export type CaseStatus =
  | "open"
  | "action_pending"
  | "action_executed"
  | "action_failed"
  | "recovered"
  | "expired"
  | "escalated"
  | "stopped";

export type ActionStatus =
  | "requested"
  | "executed"
  | "failed"
  | "skipped";

export type FailureCategory =
  | "insufficient_funds"
  | "bank_timeout"
  | "invalid_card_or_expired"
  | "otp_or_auth_failure"
  | "mandate_cancelled"
  | "gateway_or_network_error"
  | "suspected_fraud_block"
  | "unknown";

export type RecommendedAction =
  | "retry_now"
  | "retry_later"
  | "send_payment_link"
  | "send_reminder_only"
  | "escalate_to_human"
  | "stop";

export type RiskLevel =
  | "low"
  | "medium"
  | "high";

export interface RecoveryDecision {
  case_id: string;
  failure_category: FailureCategory;
  confidence: number;
  recommended_action: RecommendedAction;
  suggested_retry_window_hours:
    | number
    | null;
  reasoning: string;
  risk_level: RiskLevel;
  requires_human_approval: boolean;
  model_name: string;
  prompt_version: string;
}

export interface PolicyVerdict {
  case_id: string;
  decision_id: string;
  approved: boolean;
  reason_code: string;
  final_action: RecommendedAction;
  policy_version: string;
}

export interface RecoveryCase {
  _id: string;

  payment_id: string;

  customer_id?: string | null;

  customer_contact?: string | null;

  amount_paise: number;

  status: CaseStatus;

  auto_retry_count?: number;

  failure_event_count?: number;

  first_failure_at?: string | null;

  recovered_at?: string | null;

  recovered_amount_paise?: number | null;

  last_ai_decision?:
    | RecoveryDecision
    | null;

  last_policy_verdict?:
    | PolicyVerdict
    | null;

  last_evaluated_at?: string | null;

  last_action_at?: string | null;

  updated_at?: string | null;
}

export interface Payment {
  _id: string;
  razorpay_order_id?: string | null;
  amount_paise: number;
  currency?: string;
  method?: string | null;
  status: string;
  error_code?: string | null;
  error_description?: string | null;
  captured_amount_paise?: number | null;
  contact?: string | null;
  email?: string | null;
  updated_at?: string | null;
}

export interface Customer {
  _id: string;
  name?: string;
  email?: string;
  contact?: string;
  [key: string]: unknown;
}

export interface RecoveryAction {
  _id: string;
  idempotency_key?: string;
  case_id: string;
  action_type: RecommendedAction;
  amount_paise: number;
  status: ActionStatus;
  requested_by?: string;
  approved_by?: string;
  requested_at?: string;
  executed_at?: string | null;
  provider_reference?: string | null;
  result?: {
    simulated?: boolean;
    [key: string]: unknown;
  } | null;
  error?: string | null;
}

export interface AuditLog {
  _id: string;
  event_type: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface CaseStatusCounts {
  total: number;
  open: number;
  action_pending: number;
  action_executed: number;
  recovered: number;
  escalated: number;
  stopped: number;
  expired: number;
  action_failed: number;
}

export interface RevenueSummary {
  at_risk_paise: number;
  recovered_paise: number;
  recovery_rate: number;
}

export interface ActionSummary {
  total: number;
  executed: number;
  failed: number;
  requested: number;
}

export interface DashboardSummary {
  cases: CaseStatusCounts;
  revenue: RevenueSummary;
  actions: ActionSummary;
  recent_actions: RecoveryAction[];
}

export interface CaseDetailResponse {
  case: RecoveryCase;
  payment: Payment | null;
  customer: Customer | null;
  actions: RecoveryAction[];
  audit_logs: AuditLog[];
}