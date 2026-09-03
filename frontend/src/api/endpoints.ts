import { request } from "./client";

import type {
  AuditLog,
  CaseDetailResponse,
  DashboardSummary,
  RecoveryAction,
  RecoveryCase,
} from "./types";

export interface CaseListResponse {
  count: number;
  cases: RecoveryCase[];
}

export interface CaseActionsResponse {
  case_id: string;
  count: number;
  actions: RecoveryAction[];
}

export interface CaseAuditResponse {
  case_id: string;
  count: number;
  audit_logs: AuditLog[];
}

export interface EvaluateCaseResponse {
  case_id: string;
  recovery_score: Record<
    string,
    unknown
  >;
  ai_decision:
    | Record<string, unknown>
    | null;
  policy_verdict: Record<
    string,
    unknown
  >;
  case_status: string;
}

export interface ExecuteCaseResponse {
  case_id: string;
  action: RecoveryAction;
  duplicate_request: boolean;
  case_status?: string;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>(
    "/api/dashboard/summary",
  );
}

export function getRecoveryCases(
  params?: {
    status?: string;
    limit?: number;
  },
): Promise<CaseListResponse> {
  const query = new URLSearchParams();

  if (params?.status) {
    query.set(
      "status",
      params.status,
    );
  }

  if (params?.limit) {
    query.set(
      "limit",
      String(params.limit),
    );
  }

  const queryString =
    query.toString();

  return request<CaseListResponse>(
    `/api/recovery-cases${
      queryString
        ? `?${queryString}`
        : ""
    }`,
  );
}

export function getRecoveryCase(
  caseId: string,
): Promise<CaseDetailResponse> {
  return request<CaseDetailResponse>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}`,
  );
}

export function getCaseActions(
  caseId: string,
): Promise<CaseActionsResponse> {
  return request<CaseActionsResponse>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}/actions`,
  );
}

export function getCaseAudit(
  caseId: string,
): Promise<CaseAuditResponse> {
  return request<CaseAuditResponse>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}/audit`,
  );
}

export function getRecoveryAction(
  idempotencyKey: string,
): Promise<RecoveryAction> {
  return request<RecoveryAction>(
    `/api/recovery-actions/${encodeURIComponent(idempotencyKey)}`,
  );
}

export function evaluateCase(
  caseId: string,
): Promise<EvaluateCaseResponse> {
  return request<EvaluateCaseResponse>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}/evaluate`,
    {
      method: "POST",
    },
  );
}

export function executeCase(
  caseId: string,
): Promise<ExecuteCaseResponse> {
  return request<ExecuteCaseResponse>(
    `/api/recovery-cases/${encodeURIComponent(caseId)}/execute`,
    {
      method: "POST",
    },
  );
}