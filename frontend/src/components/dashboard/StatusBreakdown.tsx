import type {
  CaseStatusCounts,
} from "../../api/types";

type StatusKey = Exclude<
  keyof CaseStatusCounts,
  "total"
>;

type Tone =
  | "neutral"
  | "positive"
  | "warning"
  | "danger";

interface StatusMeta {
  key: StatusKey;
  label: string;
  tone: Tone;
}

const STATUS_META: StatusMeta[] = [
  {
    key: "open",
    label: "Open",
    tone: "neutral",
  },
  {
    key: "action_pending",
    label: "Action pending",
    tone: "neutral",
  },
  {
    key: "action_executed",
    label: "Action executed",
    tone: "neutral",
  },
  {
    key: "recovered",
    label: "Recovered",
    tone: "positive",
  },
  {
    key: "escalated",
    label: "Escalated",
    tone: "warning",
  },
  {
    key: "stopped",
    label: "Stopped",
    tone: "neutral",
  },
  {
    key: "expired",
    label: "Expired",
    tone: "warning",
  },
  {
    key: "action_failed",
    label: "Action failed",
    tone: "danger",
  },
];

interface StatusBreakdownProps {
  cases: CaseStatusCounts;
  selectedStatus?: StatusKey | null;
  onSelect?: (status: StatusKey) => void;
}

export default function StatusBreakdown({
  cases,
  selectedStatus,
  onSelect,
}: StatusBreakdownProps) {
  return (
    <section className="panel">
      <div className="section-header-row">
        <div>
          <p className="eyebrow">
            CASE PIPELINE
          </p>

          <h2 className="section-title">
            Recovery case status
          </h2>
        </div>

        {selectedStatus ? (
          <button
            type="button"
            className="clear-selection"
            onClick={() => {
              // There is intentionally no navigation yet.
              // B3 will connect this interaction to filtering.
              onSelect?.(selectedStatus);
            }}
          >
            Selected:{" "}
            {selectedStatus.replace(
              /_/g,
              " ",
            )}
          </button>
        ) : null}
      </div>

      <div className="status-grid">
        {STATUS_META.map(
          ({
            key,
            label,
            tone,
          }) => {
            const selected =
              selectedStatus === key;

            return (
              <button
                key={key}
                type="button"
                className={[
                  "status-chip",
                  `status-chip--${tone}`,
                  selected
                    ? "status-chip--selected"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() =>
                  onSelect?.(key)
                }
                aria-pressed={selected}
              >
                <span className="status-chip-count">
                  {cases[key]}
                </span>

                <span className="status-chip-label">
                  {label}
                </span>
              </button>
            );
          },
        )}
      </div>
    </section>
  );
}