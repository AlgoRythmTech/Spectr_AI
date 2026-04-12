import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
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

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', sans-serif",
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 24, height: 24,
            border: '2px solid #0A0A0A', borderTopColor: 'transparent',
            borderRadius: '50%', animation: 'spin 0.6s linear infinite',
          }} />
          <p style={{ fontSize: 13, color: '#999', fontWeight: 500, letterSpacing: '-0.01em' }}>
            Loading Associate...
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
