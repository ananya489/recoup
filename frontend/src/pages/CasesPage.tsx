import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError } from "../api/client";
import {
  getRecoveryCases,
} from "../api/endpoints";

import type {
  CaseStatus,
  RecoveryCase,
} from "../api/types";

type StatusFilter =
  | "all"
  | CaseStatus;

interface CasesPageProps {
  onOpenCase: (
    caseId: string,
  ) => void;

  onBackToDashboard: () => void;
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

function formatStatus(
  status: CaseStatus,
): string {
  return status.replace(
    /_/g,
    " ",
  );
}

function getStatusClass(
  status: CaseStatus,
): string {
  switch (status) {
    case "recovered":
      return "case-status case-status--positive";

    case "escalated":
    case "expired":
      return "case-status case-status--warning";

    case "action_failed":
      return "case-status case-status--danger";

    default:
      return "case-status";
  }
}

const FILTERS: Array<{
  key: StatusFilter;
  label: string;
}> = [
  {
    key: "all",
    label: "All",
  },
  {
    key: "open",
    label: "Open",
  },
  {
    key: "action_pending",
    label: "Pending",
  },
  {
    key: "action_executed",
    label: "Executed",
  },
  {
    key: "recovered",
    label: "Recovered",
  },
  {
    key: "escalated",
    label: "Escalated",
  },
  {
    key: "stopped",
    label: "Stopped",
  },
  {
    key: "expired",
    label: "Expired",
  },
  {
    key: "action_failed",
    label: "Failed",
  },
];

export default function CasesPage({
  onOpenCase,
  onBackToDashboard,
}: CasesPageProps) {
  const [
    cases,
    setCases,
  ] = useState<RecoveryCase[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(null);

  const [
    filter,
    setFilter,
  ] = useState<StatusFilter>("all");

  const [
    search,
    setSearch,
  ] = useState("");

  const loadCases =
    useCallback(
      async (
        isRefresh = false,
      ) => {
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError(null);

        try {
          const response =
            await getRecoveryCases({
              limit: 100,
              status:
                filter === "all"
                  ? undefined
                  : filter,
            });

          setCases(
            response.cases,
          );
        } catch (
          caughtError
        ) {
          const message =
            caughtError instanceof ApiError
              ? caughtError.message
              : "Could not load recovery cases.";

          setError(message);
        } finally {
          setLoading(false);
          setRefreshing(false);
        }
      },
      [filter],
    );

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  const filteredCases =
    useMemo(() => {
      const normalizedSearch =
        search.trim().toLowerCase();

      if (!normalizedSearch) {
        return cases;
      }

      return cases.filter(
        (item) =>
          item._id
            .toLowerCase()
            .includes(
              normalizedSearch,
            ) ||
          item.payment_id
            .toLowerCase()
            .includes(
              normalizedSearch,
            ) ||
          item.customer_id
            ?.toLowerCase()
            .includes(
              normalizedSearch,
            ) ||
          item.customer_contact
            ?.toLowerCase()
            .includes(
              normalizedSearch,
            ),
      );
    }, [cases, search]);

  return (
    <div className="cases-page">
      <div className="cases-header">
        <div>
          <button
            type="button"
            className="back-button"
            onClick={
              onBackToDashboard
            }
          >
            ← Dashboard
          </button>

          <p className="eyebrow">
            RECOVERY OPERATIONS
          </p>

          <h1 className="cases-title">
            Recovery Cases
          </h1>

          <p className="muted cases-subtitle">
            Review failed payments and inspect
            the recovery decisions protecting
            your revenue.
          </p>
        </div>

        <button
          type="button"
          className="btn-refresh"
          disabled={refreshing}
          onClick={() =>
            void loadCases(true)
          }
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

      <section className="cases-toolbar panel">
        <div className="cases-search-wrap">
          <label
            htmlFor="case-search"
            className="cases-search-label"
          >
            Search
          </label>

          <input
            id="case-search"
            type="search"
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value,
              )
            }
            placeholder="Search case, payment or customer…"
            className="cases-search"
          />
        </div>

        <div className="case-filters">
          {FILTERS.map(
            ({
              key,
              label,
            }) => (
              <button
                key={key}
                type="button"
                className={[
                  "case-filter",
                  filter === key
                    ? "case-filter--active"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() =>
                  setFilter(key)
                }
              >
                {label}

                {key !== "all" ? (
                  <span>
                    {
                      cases.filter(
                        (item) =>
                          item.status ===
                          key,
                      ).length
                    }
                  </span>
                ) : (
                  <span>
                    {cases.length}
                  </span>
                )}
              </button>
            ),
          )}
        </div>
      </section>

      {error ? (
        <section className="panel panel-error">
          <p className="eyebrow">
            CONNECTION ERROR
          </p>

          <h2>
            Couldn&apos;t load recovery cases
          </h2>

          <p>
            {error}
          </p>

          <button
            type="button"
            className="btn-refresh"
            onClick={() =>
              void loadCases()
            }
          >
            Try again
          </button>
        </section>
      ) : null}

      {!error &&
      loading ? (
        <section className="panel">
          <div className="cases-table-skeleton">
            {Array.from({
              length: 6,
            }).map(
              (_, index) => (
                <div
                  key={index}
                  className="case-row-skeleton"
                />
              ),
            )}
          </div>
        </section>
      ) : null}

      {!error &&
      !loading &&
      filteredCases.length === 0 ? (
        <section className="panel cases-empty">
          <div className="empty-state-icon">
            +
          </div>

          <h2>
            No matching cases
          </h2>

          <p className="muted">
            Try a different search term or
            status filter.
          </p>
        </section>
      ) : null}

      {!error &&
      !loading &&
      filteredCases.length > 0 ? (
        <section className="panel cases-table-panel">
          <div className="cases-table-heading">
            <div>
              <p className="eyebrow">
                LIVE CASE QUEUE
              </p>

              <h2 className="section-title">
                {filteredCases.length}{" "}
                {filteredCases.length ===
                1
                  ? "case"
                  : "cases"}
              </h2>
            </div>

            <span className="muted cases-count">
              Updated from live MongoDB state
            </span>
          </div>

          <div className="cases-table-container">
            <table className="cases-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Payment</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Failures</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {filteredCases.map(
                  (item) => (
                    <tr
                      key={item._id}
                      className="case-table-row"
                      onClick={() =>
                        onOpenCase(
                          item._id,
                        )
                      }
                    >
                      <td>
                        <div className="case-id-cell">
                          <strong>
                            {item._id}
                          </strong>

                          {item.customer_id ? (
                            <span className="muted">
                              customer{" "}
                              {
                                item.customer_id
                              }
                            </span>
                          ) : null}
                        </div>
                      </td>

                      <td>
                        <span className="payment-id">
                          {item.payment_id}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {formatPaise(
                            item.amount_paise,
                          )}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={getStatusClass(
                            item.status,
                          )}
                        >
                          <span className="case-status-dot" />
                          {formatStatus(
                            item.status,
                          )}
                        </span>
                      </td>

                      <td>
                        {item.failure_event_count ??
                          0}
                      </td>

                      <td>
                        <span className="muted">
                          {formatDate(
                            item.updated_at,
                          )}
                        </span>
                      </td>

                      <td>
  <button
    type="button"
    className="case-view-button"
    onClick={(event) => {
      event.stopPropagation();
      onOpenCase(item._id);
    }}
  >
    View →
  </button>
</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}