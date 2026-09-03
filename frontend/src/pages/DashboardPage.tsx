import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { ApiError } from "../api/client";
import {
  getDashboardSummary,
} from "../api/endpoints";

import type {
  DashboardSummary,
} from "../api/types";

import DashboardHeader from "../components/dashboard/DashboardHeader";
import DashboardSkeleton from "../components/dashboard/DashboardSkeleton";
import KpiCard from "../components/dashboard/KpiCard";
import RecentActionsList from "../components/dashboard/RecentActionsList";
import RecoveryHealthRing from "../components/dashboard/RecoveryHealthRing";
import StatusBreakdown from "../components/dashboard/StatusBreakdown";

type StatusKey =
  | "open"
  | "action_pending"
  | "action_executed"
  | "recovered"
  | "escalated"
  | "stopped"
  | "expired"
  | "action_failed";

type LoadState =
  | {
      status: "loading";
    }
  | {
      status: "error";
      message: string;
    }
  | {
      status: "empty";
    }
  | {
      status: "ready";
      data: DashboardSummary;
    };

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

export default function DashboardPage() {
  const [
    state,
    setState,
  ] = useState<LoadState>({
    status: "loading",
  });

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    lastUpdatedAt,
    setLastUpdatedAt,
  ] = useState<Date | null>(null);

  const [
    selectedStatus,
    setSelectedStatus,
  ] = useState<StatusKey | null>(
    null,
  );

  const load = useCallback(
    async (isRefresh: boolean) => {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setState({
          status: "loading",
        });
      }

      try {
        const data =
          await getDashboardSummary();

        setLastUpdatedAt(
          new Date(),
        );

        if (data.cases.total === 0) {
          setState({
            status: "empty",
          });
        } else {
          setState({
            status: "ready",
            data,
          });
        }
      } catch (error: unknown) {
        const message =
          error instanceof ApiError
            ? error.message
            : "Could not reach the Recoup backend.";

        setState({
          status: "error",
          message,
        });
      } finally {
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  const handleRefresh = () => {
    void load(true);
  };

  const handleStatusSelect = (
    status: StatusKey,
  ) => {
    setSelectedStatus(
      (current) =>
        current === status
          ? null
          : status,
    );
  };

  if (
    state.status === "loading"
  ) {
    return <DashboardSkeleton />;
  }

  if (
    state.status === "error"
  ) {
    return (
      <div className="dashboard">
        <div className="panel panel-error">
          <p className="eyebrow">
            CONNECTION ERROR
          </p>

          <h2>
            Couldn&apos;t load the dashboard
          </h2>

          <p>
            {state.message}
          </p>

          <p className="muted">
            Make sure the Recoup backend
            is running at{" "}
            <code>
              {(
                import.meta.env
                  .VITE_API_BASE_URL as
                  | string
                  | undefined
              ) ??
                "http://localhost:8000"}
            </code>
            .
          </p>

          <button
            type="button"
            className="btn-refresh"
            onClick={() =>
              void load(false)
            }
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (
    state.status === "empty"
  ) {
    return (
      <div className="dashboard">
        <DashboardHeader
          onRefresh={handleRefresh}
          refreshing={refreshing}
          lastUpdatedAt={
            lastUpdatedAt
          }
        />

        <div className="panel panel-empty">
          <div className="empty-state-icon">
            +
          </div>

          <h2>
            No recovery cases yet
          </h2>

          <p className="muted">
            Once a failed-payment webhook
            arrives, or a demo case is seeded,
            live recovery data will appear here.
          </p>
        </div>
      </div>
    );
  }

  const {
    cases,
    revenue,
    actions,
    recent_actions,
  } = state.data;

  return (
    <div className="dashboard">
      <DashboardHeader
        onRefresh={handleRefresh}
        refreshing={refreshing}
        lastUpdatedAt={
          lastUpdatedAt
        }
      />

      {/* Primary KPIs */}
      <div className="kpi-grid">
        <KpiCard
          label="Revenue at risk"
          value={formatPaise(
            revenue.at_risk_paise,
          )}
          tone="warning"
          size="primary"
        />

        <KpiCard
          label="Revenue recovered"
          value={formatPaise(
            revenue.recovered_paise,
          )}
          tone="positive"
          size="primary"
        />

        <KpiCard
          label="Recovery rate"
          value={`${(
            revenue.recovery_rate * 100
          ).toFixed(1)}%`}
          tone="prominent"
          size="primary"
        />

        <KpiCard
          label="Total cases"
          value={cases.total.toString()}
          size="secondary"
        />

        <KpiCard
          label="Open cases"
          value={cases.open.toString()}
          size="secondary"
        />

        <KpiCard
          label="Human escalations"
          value={cases.escalated.toString()}
          tone={
            cases.escalated > 0
              ? "warning"
              : "neutral"
          }
          size="secondary"
        />

        <KpiCard
          label="Actions executed"
          value={actions.executed.toString()}
          tone="positive"
          size="secondary"
        />

        <KpiCard
          label="Actions failed"
          value={actions.failed.toString()}
          tone={
            actions.failed > 0
              ? "danger"
              : "neutral"
          }
          size="secondary"
        />
      </div>

      <RecoveryHealthRing
        recoveryRate={
          revenue.recovery_rate
        }
        recoveredPaise={
          revenue.recovered_paise
        }
        atRiskPaise={
          revenue.at_risk_paise
        }
      />

      <StatusBreakdown
        cases={cases}
        selectedStatus={
          selectedStatus
        }
        onSelect={
          handleStatusSelect
        }
      />

      <RecentActionsList
        actions={recent_actions}
      />

      <div className="safety-banner">
        <div className="safety-banner-icon">
          ✓
        </div>

        <div>
          <strong>
            Safe automation by design
          </strong>

          <p>
            AI recommendations are advisory.
            Deterministic policy controls what
            can execute. Every executed action
            is auditable.
          </p>
        </div>
      </div>
    </div>
  );
}