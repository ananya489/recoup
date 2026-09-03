import {
  useEffect,
  useState,
} from "react";

import { ApiError } from "../api/client";

import {
  evaluateCase,
  executeCase,
  getRecoveryCase,
} from "../api/endpoints";

import type {
  CaseDetailResponse,
} from "../api/types";


interface CaseDetailPageProps {
  caseId: string;
  onBack: () => void;
}


function formatPaise(
  paise: number,
): string {
  return `₹${(
    paise / 100
  ).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}


function formatDate(
  value?: string | null,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "—";
  }

  return date.toLocaleString(
    "en-IN",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
}


function statusClass(
  status: string,
): string {
  if (status === "recovered") {
    return "case-status case-status--positive";
  }

  if (
    status === "escalated" ||
    status === "expired"
  ) {
    return "case-status case-status--warning";
  }

  if (status === "action_failed") {
    return "case-status case-status--danger";
  }

  return "case-status";
}


export default function CaseDetailPage({
  caseId,
  onBack,
}: CaseDetailPageProps) {
  const [
    data,
    setData,
  ] = useState<CaseDetailResponse | null>(
    null,
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    evaluating,
    setEvaluating,
  ] = useState(false);

  const [
    executing,
    setExecuting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    evaluationError,
    setEvaluationError,
  ] = useState<string | null>(
    null,
  );

  const [
    executionError,
    setExecutionError,
  ] = useState<string | null>(
    null,
  );

  const [
    executionResult,
    setExecutionResult,
  ] = useState<
    Awaited<
      ReturnType<typeof executeCase>
    > | null
  >(null);


  /*
   * Load the complete case detail.
   */
  const loadCase = async () => {
    setLoading(true);
    setError(null);

    try {
      const response =
        await getRecoveryCase(
          caseId,
        );

      setData(response);
    } catch (
      caughtError
    ) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not load this recovery case.",
      );
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    void loadCase();
  }, [caseId]);


  /*
   * Evaluate the recovery case.
   *
   * recovery score
   *      ↓
   * AI recommendation
   *      ↓
   * deterministic policy
   *      ↓
   * persistence
   *
   * Evaluation does NOT execute a financial action.
   */
  const handleEvaluate =
    async () => {
      setEvaluating(true);
      setEvaluationError(null);
      setExecutionError(null);

      try {
        await evaluateCase(
          caseId,
        );

        /*
         * Reload the case so the persisted
         * AI recommendation and policy verdict
         * are displayed.
         */
        const refreshed =
          await getRecoveryCase(
            caseId,
          );

        setData(
          refreshed,
        );
      } catch (
        caughtError
      ) {
        setEvaluationError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not evaluate the recovery case.",
        );
      } finally {
        setEvaluating(false);
      }
    };


  /*
   * Execute ONLY when the deterministic
   * policy engine explicitly approves.
   */
  const handleExecute =
    async () => {
      if (
        !policyVerdict ||
        policyVerdict.approved !== true
      ) {
        return;
      }

      setExecuting(true);
      setExecutionError(null);
      setExecutionResult(null);

      try {
        const result =
          await executeCase(
            caseId,
          );

        setExecutionResult(
          result,
        );

        /*
         * Reload the complete case so the UI
         * immediately reflects new actions,
         * status and audit records.
         */
        const refreshed =
          await getRecoveryCase(
            caseId,
          );

        setData(
          refreshed,
        );
      } catch (
        caughtError
      ) {
        setExecutionError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not execute the recovery action.",
        );
      } finally {
        setExecuting(false);
      }
    };


  /* =========================================================
     Loading
     ========================================================= */

  if (loading) {
    return (
      <div className="case-detail-page">
        <button
          type="button"
          className="back-button"
          onClick={onBack}
        >
          ← Recovery Cases
        </button>

        <div className="panel">
          <p className="muted">
            Loading recovery case…
          </p>
        </div>
      </div>
    );
  }


  /* =========================================================
     Error
     ========================================================= */

  if (error || !data) {
    return (
      <div className="case-detail-page">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
        >
          ← Recovery Cases
        </button>

        <section className="panel panel-error">

          <p className="eyebrow">
            CASE ERROR
          </p>

          <h2>
            Couldn&apos;t load case
          </h2>

          <p>
            {error ??
              "Case data was not returned."}
          </p>

          <button
            type="button"
            className="btn-primary"
            onClick={() =>
              void loadCase()
            }
          >
            Try again
          </button>

        </section>
      </div>
    );
  }


  const {
    case: recoveryCase,
    payment,
    customer,
    actions,
    audit_logs,
  } = data;


  const aiDecision =
    recoveryCase.last_ai_decision;

  const policyVerdict =
    recoveryCase.last_policy_verdict;


  /*
   * A case should never expose Execute after
   * it has reached a successful or already-run
   * execution state.
   */
  const executionTerminal =
    recoveryCase.status ===
      "recovered" ||
    recoveryCase.status ===
      "action_executed";


  const canExecute =
    policyVerdict?.approved === true &&
    !executionTerminal;


  return (
    <div className="case-detail-page">

      {/* =====================================================
          HEADER
          ===================================================== */}

      <div className="case-detail-header">

        <div>

          <button
            type="button"
            className="back-button"
            onClick={onBack}
          >
            ← Recovery Cases
          </button>

          <p className="eyebrow">
            RECOVERY CASE
          </p>

          <h1 className="cases-title">
            {recoveryCase._id}
          </h1>

          <p className="muted">
            Payment{" "}
            {recoveryCase.payment_id}
          </p>

        </div>


        <div className="case-detail-header-right">

          <span
            className={statusClass(
              recoveryCase.status,
            )}
          >
            <span className="case-status-dot" />

            {recoveryCase.status.replace(
              /_/g,
              " ",
            )}
          </span>


          {recoveryCase.status !==
            "recovered" &&
          recoveryCase.status !==
            "stopped" &&
          recoveryCase.status !==
            "expired" &&
          recoveryCase.status !==
            "escalated" ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() =>
                void handleEvaluate()
              }
              disabled={evaluating}
            >
              {evaluating
                ? "Evaluating…"
                : aiDecision
                  ? "Re-evaluate"
                  : "Evaluate Recovery"}
            </button>
          ) : null}

        </div>

      </div>


      {evaluationError ? (
        <div className="evaluation-error">
          {evaluationError}
        </div>
      ) : null}


      {/* =====================================================
          PAYMENT + CUSTOMER
          ===================================================== */}

      <section className="detail-grid">

        <div className="panel">

          <p className="eyebrow">
            PAYMENT
          </p>

          <h2 className="section-title">
            Payment details
          </h2>

          <div className="detail-list">

            <DetailRow
              label="Payment ID"
              value={
                payment?._id ??
                "—"
              }
            />

            <DetailRow
              label="Amount"
              value={formatPaise(
                recoveryCase.amount_paise,
              )}
            />

            <DetailRow
              label="Method"
              value={
                payment?.method ??
                "—"
              }
            />

            <DetailRow
              label="Status"
              value={
                payment?.status ??
                "—"
              }
            />

            <DetailRow
              label="Failure code"
              value={
                payment?.error_code ??
                "—"
              }
            />

            <DetailRow
              label="Failure reason"
              value={
                payment?.error_description ??
                "—"
              }
            />

          </div>

        </div>


        <div className="panel">

          <p className="eyebrow">
            CUSTOMER
          </p>

          <h2 className="section-title">
            Customer details
          </h2>

          <div className="detail-list">

            <DetailRow
              label="Contact"
              value={
                recoveryCase.customer_contact ??
                payment?.contact ??
                customer?.contact ??
                "—"
              }
            />

            <DetailRow
              label="Email"
              value={
                payment?.email ??
                customer?.email ??
                "—"
              }
            />

            <DetailRow
              label="Customer ID"
              value={
                customer?._id ??
                recoveryCase.customer_id ??
                "—"
              }
            />

          </div>

        </div>

      </section>


      {/* =====================================================
          AI RECOMMENDATION
          ===================================================== */}

      <section className="panel">

        <p className="eyebrow">
          AI RECOMMENDATION
        </p>

        <h2 className="section-title">
          What the AI recommended
        </h2>


        {aiDecision ? (

          <div className="detail-grid">

            <DetailRow
              label="Failure category"
              value={String(
                aiDecision.failure_category ??
                  "—",
              )}
            />

            <DetailRow
              label="Confidence"
              value={
                typeof aiDecision.confidence ===
                "number"
                  ? `${(
                      aiDecision.confidence *
                      100
                    ).toFixed(1)}%`
                  : "—"
              }
            />

            <DetailRow
              label="Recommended action"
              value={String(
                aiDecision.recommended_action ??
                  "—",
              ).replace(
                /_/g,
                " ",
              )}
            />

            <DetailRow
              label="Risk"
              value={String(
                aiDecision.risk_level ??
                  "—",
              )}
            />

            <DetailRow
              label="Reasoning"
              value={String(
                aiDecision.reasoning ??
                  "—",
              )}
            />

          </div>

        ) : (

          <div className="decision-empty">

            <div className="decision-empty-icon">
              AI
            </div>

            <div>

              <strong>
                Case has not been evaluated
              </strong>

              <p className="muted">
                Click &quot;Evaluate Recovery&quot;
                to generate an AI recommendation
                and deterministic policy verdict.
              </p>

            </div>

          </div>

        )}

      </section>


      {/* =====================================================
          POLICY DECISION
          ===================================================== */}

      <section className="panel">

        <p className="eyebrow">
          POLICY DECISION
        </p>

        <h2 className="section-title">
          Deterministic policy verdict
        </h2>


        {policyVerdict ? (

          <div className="policy-verdict">

            <div
              className={
                policyVerdict.approved
                  ? "policy-state policy-state--approved"
                  : "policy-state policy-state--blocked"
              }
            >
              {policyVerdict.approved
                ? "APPROVED"
                : "BLOCKED"}
            </div>


            <DetailRow
              label="Reason code"
              value={
                policyVerdict.reason_code
              }
            />


            <DetailRow
              label="Final action"
              value={
                policyVerdict.final_action.replace(
                  /_/g,
                  " ",
                )
              }
            />


            <DetailRow
              label="Policy version"
              value={
                policyVerdict.policy_version
              }
            />

          </div>

        ) : (

          <div className="decision-empty">

            <div className="decision-empty-icon">
              →
            </div>

            <div>

              <strong>
                Waiting for policy evaluation
              </strong>

              <p className="muted">
                The deterministic policy engine
                will decide whether the recommendation
                is allowed to proceed.
              </p>

            </div>

          </div>

        )}

      </section>


      {/* =====================================================
          EXECUTION
          ===================================================== */}

      <section className="panel">

        <div className="section-header-row">

          <div>

            <p className="eyebrow">
              EXECUTION
            </p>

            <h2 className="section-title">
              Recovery action
            </h2>

          </div>


          <span className="activity-count">
            {actions.length}{" "}
            {actions.length === 1
              ? "action"
              : "actions"}
          </span>

        </div>


        <p className="muted section-subtitle">
          AI recommendations never execute directly.
          Only actions explicitly approved by the
          deterministic policy engine can proceed.
        </p>


        {canExecute ? (

          <div className="execution-approval">

            <div>

              <strong>
                Policy approved this recovery
              </strong>

              <p className="muted">
                The approved action can now be
                sent through the recovery executor.
              </p>

            </div>


            <button
              type="button"
              className="btn-primary"
              onClick={() =>
                void handleExecute()
              }
              disabled={executing}
            >
              {executing
                ? "Executing…"
                : "Execute Recovery"}
            </button>

          </div>

        ) : policyVerdict ? (

          <div className="execution-blocked">

            <div>

              <strong>
                {executionTerminal
                  ? "Recovery already executed"
                  : "Execution blocked"}
              </strong>

              <p className="muted">
                {executionTerminal
                  ? "This case has already reached an execution state. Another automatic execution is not allowed."
                  : "The deterministic policy engine did not approve an automatic recovery action."}
              </p>

            </div>

          </div>

        ) : (

          <div className="action-empty">

            <div className="action-empty-icon">
              →
            </div>

            <div>

              <strong>
                Evaluation required
              </strong>

              <p className="muted">
                Evaluate the case before an action
                can be considered for execution.
              </p>

            </div>

          </div>

        )}


        {executing ? (

          <div className="execution-progress">

            <span className="execution-spinner" />

            <div>

              <strong>
                Executing approved recovery action
              </strong>

              <p className="muted">
                The action is being sent through the
                recovery executor.
              </p>

            </div>

          </div>

        ) : null}


        {executionError ? (

          <div className="evaluation-error">
            {executionError}
          </div>

        ) : null}


        {executionResult ? (

          <div className="execution-result">

            <div className="execution-result-header">

              <span className="badge badge--positive">
                EXECUTED
              </span>

              <strong>
                Recovery action completed
              </strong>

            </div>


            <div className="execution-result-grid">

              <DetailRow
                label="Case ID"
                value={
                  executionResult.case_id
                }
              />

              <DetailRow
                label="Action"
                value={
                  executionResult.action.action_type.replace(
                    /_/g,
                    " ",
                  )
                }
              />

              <DetailRow
                label="Action status"
                value={
                  executionResult.action.status
                }
              />

              <DetailRow
                label="Provider reference"
                value={
                  executionResult.action.provider_reference ??
                  "—"
                }
              />

              <DetailRow
                label="Duplicate request"
                value={
                  executionResult.duplicate_request
                    ? "Yes"
                    : "No"
                }
              />

              <DetailRow
                label="Case status"
                value={
                  executionResult.case_status ??
                  "—"
                }
              />

            </div>

          </div>

        ) : null}


        {actions.length > 0 ? (

          <div className="case-actions-list">

            {actions.map(
              (action) => (

                <div
                  key={action._id}
                  className="case-action-card"
                >

                  <div>

                    <strong>
                      {action.action_type.replace(
                        /_/g,
                        " ",
                      )}
                    </strong>

                    <p className="muted">
                      {formatDate(
                        action.requested_at,
                      )}
                    </p>

                    {action.provider_reference ? (
                      <p className="muted">
                        Provider ref:{" "}
                        {
                          action.provider_reference
                        }
                      </p>
                    ) : null}

                  </div>


                  <span
                    className={statusClass(
                      action.status ===
                      "executed"
                        ? "recovered"
                        : action.status ===
                            "failed"
                          ? "action_failed"
                          : "open",
                    )}
                  >
                    {action.status}
                  </span>

                </div>

              ),
            )}

          </div>

        ) : null}

      </section>


      {/* =====================================================
          AUDIT TRAIL
          ===================================================== */}

      <section className="panel">

        <p className="eyebrow">
          AUDIT TRAIL
        </p>

        <h2 className="section-title">
          Decision history
        </h2>


        {audit_logs.length === 0 ? (

          <div className="action-empty">

            <div className="action-empty-icon">
              ✓
            </div>

            <div>

              <strong>
                No audit records yet
              </strong>

              <p className="muted">
                Evaluation and execution events
                will appear here automatically.
              </p>

            </div>

          </div>

        ) : (

          <div className="audit-timeline">

            {audit_logs.map(
              (log) => (

                <div
                  key={log._id}
                  className="audit-item"
                >

                  <div className="audit-dot" />

                  <div>

                    <strong>
                      {log.event_type.replace(
                        /_/g,
                        " ",
                      )}
                    </strong>

                    <p className="muted">
                      {log.actor} ·{" "}
                      {formatDate(
                        log.timestamp,
                      )}
                    </p>

                    {log.metadata &&
                    Object.keys(
                      log.metadata,
                    ).length > 0 ? (
                      <div className="audit-metadata">
                        {Object.entries(
                          log.metadata,
                        ).map(
                          ([
                            key,
                            value,
                          ]) => (
                            <span
                              key={key}
                              className="audit-metadata-item"
                            >
                              <strong>
                                {key.replace(
                                  /_/g,
                                  " ",
                                )}
                                :
                              </strong>{" "}
                              {String(value)}
                            </span>
                          ),
                        )}
                      </div>
                    ) : null}

                  </div>

                </div>

              ),
            )}

          </div>

        )}

      </section>

    </div>
  );
}


function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="detail-row">

      <span className="muted">
        {label}
      </span>

      <span className="detail-value">
        {value}
      </span>

    </div>
  );
}