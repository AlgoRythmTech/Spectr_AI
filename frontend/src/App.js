import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import TermsPage from "./pages/TermsPage";
import NotFoundPage from "./pages/NotFoundPage";
import DashboardLayout from "./pages/DashboardLayout";
import AssistantPage from "./pages/AssistantPage";
import VaultPage from "./pages/VaultPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import LibraryPage from "./pages/LibraryPage";
import HistoryPage from "./pages/HistoryPage";
import ReconcilerPage from "./pages/ReconcilerPage";
import PortfolioPage from "./pages/PortfolioPage";
import CaseLawPage from "./pages/CaseLawPage";
import CourtTrackerPage from "./pages/CourtTrackerPage";
import SettingsPage from "./pages/SettingsPage";
import TOSAcceptanceGate from "./components/TOSAcceptanceGate";
import { ToastProvider } from "./components/Toast";
import KeyboardShortcutsOverlay from "./components/KeyboardShortcutsOverlay";


function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'DM Sans', sans-serif",
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 22, height: 22,
            border: '2px solid #0A0A0A', borderTopColor: 'transparent',
            borderRadius: '50%', animation: 'spin 0.7s linear infinite',
          }} />
          <p style={{ fontSize: 13, color: '#999', fontWeight: 500, letterSpacing: '-0.01em' }}>
            Loading Spectr...
          </p>
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/" replace />;
  // T&C v2.0 Clause 2.1-2.3: no protected page renders until the user has a
  // recorded Acceptance Event for the current Agreement version.
  return <TOSAcceptanceGate>{children}</TOSAcceptanceGate>;
}

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/legal/terms" element={<TermsPage />} />
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/assistant" replace />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="caselaw" element={<CaseLawPage />} />
        <Route path="vault" element={<VaultPage />} />
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="reconciler" element={<ReconcilerPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="court-tracker" element={<CourtTrackerPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      {/* Global grain texture — adds warmth, kills gradient banding. */}
      <div className="spectr-grain" />
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRouter />
            <KeyboardShortcutsOverlay />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
