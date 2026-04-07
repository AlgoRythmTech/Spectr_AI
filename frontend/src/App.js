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
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-[#1A1A2E] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-[#64748B] font-medium tracking-wide">Loading Associate...</p>
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
