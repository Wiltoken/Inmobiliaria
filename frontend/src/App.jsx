import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './lib/auth';
import { useAudit } from './hooks/useAudit';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import MainLayout from './components/layout/MainLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import SearchPage from './pages/SearchPage';
import PropertyDetailPage from './pages/PropertyDetailPage';
import NotFoundPage from './pages/NotFoundPage';
import AdminUsersPage from './pages/AdminUsersPage';
import BIDashboard from './components/analytics/BIDashboard';

function AppRoutes() {
  const { user, isLoading } = useAuth();
  const { trackPageView } = useAudit();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500">Cargando...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          user ? <Navigate to="/dashboard" replace /> : <LoginPage />
        }
      />
      <Route
        path="/register"
        element={
          user ? <Navigate to="/dashboard" replace /> : <RegisterPage />
        }
      />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route
          path="/dashboard"
          element={<DashboardPage onPageView={trackPageView} />}
        />
        <Route
          path="/search"
          element={<SearchPage onPageView={trackPageView} />}
        />
        <Route
          path="/property/:id"
          element={<PropertyDetailPage onPageView={trackPageView} />}
        />
        <Route
          path="/favorites"
          element={<div className="p-4"><h1 className="text-2xl font-bold">Favoritos</h1></div>}
        />
        <Route
          path="/messages"
          element={<div className="p-4"><h1 className="text-2xl font-bold">Mensajes</h1></div>}
        />
        <Route
          path="/profile"
          element={<div className="p-4"><h1 className="text-2xl font-bold">Perfil</h1></div>}
        />
        <Route
          path="/admin/analytics"
          element={
            <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
              <BIDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
              <AdminUsersPage onPageView={trackPageView} />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default function App() {
  return <AppRoutes />;
}
