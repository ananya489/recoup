import type {
  ActionStatus,
  RecoveryAction,
} from "../../api/types";

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

function formatTimestamp(
  value?: string,
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
    return value;
  }

  return date.toLocaleString(
    "en-IN",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
}

const STATUS_TONE: Record<
  ActionStatus,
  "positive" | "warning" | "danger" | "neutral"
> = {
  executed: "positive",
  failed: "danger",
  requested: "warning",
  skipped: "neutral",
};

export default function RecentActionsList({
  actions,
}: {
  actions: RecoveryAction[];
}) {
  return (
    <section className="panel">
      <div className="section-header-row">
        <div>
          <p className="eyebrow">
            AUDITABLE ACTIVITY
          </p>

          <h2 className="section-title">
            Recent recovery activity
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
        These records represent recovery actions,
        not raw AI recommendations. Every action
        passed through the deterministic policy
        layer before execution.
      </p>

      {actions.length === 0 ? (
        <div className="action-empty">
          <div className="action-empty-icon">
            ✓
          </div>

          <div>
            <strong>
              No recovery activity yet
            </strong>

            <p className="muted">
              Approved actions will appear here
              when the recovery engine executes them.
            </p>
          </div>
        </div>
      ) : (
        <ul className="action-timeline">
          {actions.map((action) => {
            const tone =
              STATUS_TONE[action.status];

            return (
              <li
                key={action._id}
                className="action-timeline-item"
              >
                <div
                  className={`timeline-marker timeline-marker--${tone}`}
                  aria-hidden="true"
                />

                <div className="action-feed-card">
                  <div className="action-feed-top">
                    <div className="action-feed-title">
                      <span
                        className={`badge badge--${tone}`}
                      >
                        {action.status}
                      </span>

                      <span className="action-type">
                        {action.action_type.replace(
                          /_/g,
                          " ",
                        )}
                      </span>

                      {action.result?.simulated ===
                      true ? (
                        <span className="badge badge--simulated">
                          simulated
                        </span>
                      ) : null}

                      {action.result?.simulated ===
                      false ? (
                        <span className="badge badge--real">
                          Test Mode · real call
                        </span>
                      ) : null}
                    </div>

                    <strong>
                      {formatPaise(
                        action.amount_paise,
                      )}
                    </strong>
                  </div>

                  <div className="action-feed-meta">
                    <span>
                      case {action.case_id}
                    </span>

                    <span>
                      {formatTimestamp(
                        action.requested_at,
                      )}
                    </span>

                    {action.provider_reference ? (
                      <span>
                        ref:{" "}
                        {action.provider_reference}
                      </span>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}