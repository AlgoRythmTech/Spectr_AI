import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthCallback from "./components/AuthCallback";
import LandingPage from "./pages/LandingPage";
import DashboardLayout from "./pages/DashboardLayout";
import AssistantPage from "./pages/AssistantPage";
import VaultPage from "./pages/VaultPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import LibraryPage from "./pages/LibraryPage";
import HistoryPage from "./pages/HistoryPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Skip if user was passed from AuthCallback
  if (location.state?.user) return children;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#1A1A2E] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRouter() {
  const location = useLocation();

  // Check URL fragment for session_id — synchronous, prevents race conditions
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
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
        <Route path="vault" element={<VaultPage />} />
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="history" element={<HistoryPage />} />
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
