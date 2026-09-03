interface DashboardHeaderProps {
  onRefresh: () => void;
  refreshing: boolean;
  lastUpdatedAt: Date | null;
}

function formatTime(
  value: Date | null,
): string {
  if (!value) {
    return "Not updated yet";
  }

  return value.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function DashboardHeader({
  onRefresh,
  refreshing,
  lastUpdatedAt,
}: DashboardHeaderProps) {
  return (
    <div className="dashboard-header">
      <div className="dashboard-header-copy">
        <p className="eyebrow">
          LIVE OPERATIONS
        </p>

        <h1 className="dashboard-title">
          Revenue Recovery
        </h1>

        <p className="muted dashboard-subtitle">
          Recover failed payments safely with AI
          recommendations and deterministic controls.
        </p>

        <div className="dashboard-meta">
          <span className="dashboard-meta-item">
            AI recommends
          </span>

          <span className="dashboard-meta-arrow">
            →
          </span>

          <span className="dashboard-meta-item">
            Policy decides
          </span>

          <span className="dashboard-meta-arrow">
            →
          </span>

          <span className="dashboard-meta-item">
            Approved action executes
          </span>
        </div>
      </div>

      <div className="dashboard-header-actions">
        <div className="live-block">
          <span className="live-indicator">
            <span
              className="live-dot"
              aria-hidden="true"
            />
            LIVE
          </span>

          <span className="last-updated">
            Updated {formatTime(lastUpdatedAt)}
          </span>
        </div>

        <button
          type="button"
          className="btn-refresh"
          onClick={onRefresh}
          disabled={refreshing}
        >
          <span
            className={
              refreshing
                ? "refresh-icon refresh-icon--spinning"
                : "refresh-icon"
            }
          >
            ↻
          </span>

          {refreshing
            ? "Refreshing…"
            : "Refresh"}
        </button>
      </div>
    </div>
  );
}