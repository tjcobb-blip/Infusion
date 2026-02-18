import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import LoginPage from "./pages/LoginPage";
import CaseListPage from "./pages/CaseListPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import "./App.css";

function Navbar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="navbar">
      <Link to="/cases" className="navbar-brand">
        Infusion Platform
      </Link>
      <div className="navbar-right">
        <span className="navbar-role">
          {user.role === "PROVIDER" ? "Provider" : "Infusion Admin"}
        </span>
        <span className="navbar-email">{user.email}</span>
        <button className="btn btn-secondary btn-sm" onClick={logout}>
          Sign Out
        </button>
      </div>
    </nav>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <div className="app-layout">
      <Navbar />
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/cases" replace /> : <LoginPage />}
        />
        <Route
          path="/cases"
          element={
            <ProtectedRoute>
              <CaseListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cases/:id"
          element={
            <ProtectedRoute>
              <CaseDetailPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
