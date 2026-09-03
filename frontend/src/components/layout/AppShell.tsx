import type { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({
  children,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            Recoup
          </span>

          <span className="brand-tagline">
            AI Revenue Recovery — Razorpay
            Test Mode
          </span>
        </div>

        <nav className="app-nav">
          <span className="nav-item nav-item--active">
            Dashboard
          </span>

          <span
            className="nav-item nav-item--disabled"
            title="Coming in Sub-batch B3"
          >
            Cases
          </span>
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