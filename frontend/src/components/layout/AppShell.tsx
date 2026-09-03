import type {
  ReactNode,
} from "react";

export type AppView =
  | "dashboard"
  | "cases";

interface AppShellProps {
  children: ReactNode;
  currentView: AppView;
  onNavigate: (
    view: AppView,
  ) => void;
}

export default function AppShell({
  children,
  currentView,
  onNavigate,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <button
          type="button"
          className="brand-button"
          onClick={() =>
            onNavigate("dashboard")
          }
        >
          <span className="brand-mark">
            Recoup
          </span>

          <span className="brand-tagline">
            AI Revenue Recovery — Razorpay
            Test Mode
          </span>
        </button>

        <nav className="app-nav">
          <button
            type="button"
            className={[
              "nav-item",
              currentView === "dashboard"
                ? "nav-item--active"
                : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() =>
              onNavigate("dashboard")
            }
          >
            Dashboard
          </button>

          <button
            type="button"
            className={[
              "nav-item",
              currentView === "cases"
                ? "nav-item--active"
                : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() =>
              onNavigate("cases")
            }
          >
            Cases
          </button>
        </nav>
      </header>

      <main className="app-main">
        {children}
      </main>

      <footer className="app-footer">
        <p>
          <strong>
            AI recommends
          </strong>{" "}
          →{" "}
          <strong>
            deterministic policy decides
          </strong>{" "}
          →{" "}
          <strong>
            approved action executes
          </strong>{" "}
          →{" "}
          <strong>
            everything is audited
          </strong>
          .
        </p>

        <p>
          Razorpay Test Mode only — no
          real money moves.
        </p>
      </footer>
    </div>
  );
}