export default function DashboardSkeleton() {
  return (
    <div
      className="skeleton-wrap"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <div className="skeleton skeleton-header" />

      <div className="kpi-grid">
        {Array.from({
          length: 7,
        }).map((_, index) => (
          <div
            key={index}
            className={`skeleton skeleton-card ${
              index < 3
                ? "skeleton-card--primary"
                : ""
            }`}
          />
        ))}
      </div>

      <div className="skeleton skeleton-health" />

      <div className="skeleton skeleton-panel" />

      <div className="skeleton skeleton-panel" />
    </div>
  );
}