import { useState } from "react";

import AppShell, {
  type AppView,
} from "./components/layout/AppShell";

import DashboardPage from "./pages/DashboardPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";

type InternalView =
  | AppView
  | "case-detail";

export default function App() {
  const [view, setView] =
    useState<InternalView>("dashboard");

  const [
    selectedCaseId,
    setSelectedCaseId,
  ] = useState<string | null>(null);

  const handleOpenCase = (
    caseId: string,
  ) => {
    setSelectedCaseId(caseId);
    setView("case-detail");
  };

  const handleBackToCases = () => {
    setSelectedCaseId(null);
    setView("cases");
  };

  const handleNavigate = (
    nextView: AppView,
  ) => {
    setSelectedCaseId(null);
    setView(nextView);
  };

  const shellView: AppView =
    view === "case-detail"
      ? "cases"
      : view;

  return (
    <AppShell
      currentView={shellView}
      onNavigate={handleNavigate}
    >
      {view === "dashboard" && (
        <DashboardPage />
      )}

      {view === "cases" && (
        <CasesPage
          onOpenCase={handleOpenCase}
          onBackToDashboard={() =>
            setView("dashboard")
          }
        />
      )}

      {view === "case-detail" &&
        selectedCaseId && (
          <CaseDetailPage
            caseId={selectedCaseId}
            onBack={handleBackToCases}
          />
        )}
    </AppShell>
  );
}