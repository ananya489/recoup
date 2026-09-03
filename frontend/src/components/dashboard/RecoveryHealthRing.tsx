interface RecoveryHealthRingProps {
  recoveryRate: number;
  recoveredPaise: number;
  atRiskPaise: number;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function RecoveryHealthRing({
  recoveryRate,
  recoveredPaise,
  atRiskPaise,
}: RecoveryHealthRingProps) {
  const percentage = Math.max(
    0,
    Math.min(100, recoveryRate * 100),
  );

  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const offset =
    circumference -
    (percentage / 100) * circumference;

  return (
    <section className="panel health-panel">
      <div className="health-panel-header">
        <div>
          <p className="eyebrow">RECOVERY HEALTH</p>
          <h2 className="section-title">
            Current recovery performance
          </h2>
          <p className="muted section-subtitle">
            Based on the live recovery-case state in MongoDB.
          </p>
        </div>
      </div>

      <div className="health-content">
        <div className="health-ring-wrap">
          <svg
            className="health-ring"
            viewBox="0 0 140 140"
            role="img"
            aria-label={`Recovery rate ${percentage.toFixed(1)} percent`}
          >
            <circle
              className="health-ring-track"
              cx="70"
              cy="70"
              r={radius}
              fill="none"
              strokeWidth="12"
            />

            <circle
              className="health-ring-progress"
              cx="70"
              cy="70"
              r={radius}
              fill="none"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 70 70)"
            />
          </svg>

          <div className="health-ring-center">
            <span className="health-ring-value">
              {percentage.toFixed(1)}%
            </span>

            <span className="health-ring-label">
              recovered
            </span>
          </div>
        </div>

        <div className="health-summary">
          <div className="health-summary-row">
            <span className="muted">
              Revenue recovered
            </span>
            <strong className="health-positive">
              {formatPaise(recoveredPaise)}
            </strong>
          </div>

          <div className="health-summary-row">
            <span className="muted">
              Revenue at risk
            </span>
            <strong>
              {formatPaise(atRiskPaise)}
            </strong>
          </div>

          <div className="health-bar">
            <div className="health-bar-track">
              <div
                className="health-bar-fill"
                style={{
                  width: `${percentage}%`,
                }}
              />
            </div>

            <div className="health-bar-labels">
              <span>Recovered</span>
              <span>{percentage.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}