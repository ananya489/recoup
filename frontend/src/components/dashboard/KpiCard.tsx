export type KpiTone =
  | "neutral"
  | "positive"
  | "warning"
  | "danger"
  | "prominent";

export type KpiSize =
  | "primary"
  | "secondary";

interface KpiCardProps {
  label: string;
  value: string;
  tone?: KpiTone;
  size?: KpiSize;
  sublabel?: string;
}

export default function KpiCard({
  label,
  value,
  tone = "neutral",
  size = "secondary",
  sublabel,
}: KpiCardProps) {
  return (
    <div
      className={[
        "kpi-card",
        `kpi-card--${tone}`,
        `kpi-card--${size}`,
      ].join(" ")}
    >
      <div className="kpi-label">
        {label}
      </div>

      <div className="kpi-value">
        {value}
      </div>

      {sublabel ? (
        <div className="kpi-sublabel">
          {sublabel}
        </div>
      ) : null}
    </div>
  );
}