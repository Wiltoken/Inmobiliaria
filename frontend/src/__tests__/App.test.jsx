import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

// Mock auth as unauthenticated
vi.mock('../lib/auth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
  }),
  AuthProvider: ({ children }) => children,
}));

// Mock all page components
vi.mock('../pages/LoginPage', () => ({ default: () => <div>Login Page</div> }));
vi.mock('../pages/RegisterPage', () => ({ default: () => <div>Register Page</div> }));
vi.mock('../pages/ForgotPasswordPage', () => ({ default: () => <div>Forgot Password</div> }));
vi.mock('../pages/ResetPasswordPage', () => ({ default: () => <div>Reset Password</div> }));
vi.mock('../pages/DashboardPage', () => ({ default: () => <div>Dashboard</div> }));
vi.mock('../pages/SearchPage', () => ({ default: () => <div>Search</div> }));
vi.mock('../pages/PropertyDetailPage', () => ({ default: () => <div>Property Detail</div> }));
vi.mock('../pages/NotFoundPage', () => ({ default: () => <div>Not Found</div> }));
vi.mock('../components/analytics/BIDashboard', () => ({ default: () => <div>BI Dashboard</div> }));
vi.mock('../components/auth/ProtectedRoute', () => ({
  ProtectedRoute: ({ children }) => <div>{children}</div>,
}));
vi.mock('../components/layout/MainLayout', () => ({ default: () => <div>Main Layout</div> }));
vi.mock('../hooks/useAudit', () => ({
  useAudit: () => ({ trackPageView: vi.fn() }),
}));

function renderRoute(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe('App routing', () => {
  it('renders login page at /login', () => {
    renderRoute('/login');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('renders register page at /register', () => {
    renderRoute('/register');
    expect(screen.getByText('Register Page')).toBeInTheDocument();
  });

  it('renders forgot password page at /forgot-password', () => {
    renderRoute('/forgot-password');
    expect(screen.getByText('Forgot Password')).toBeInTheDocument();
  });

  it('renders reset password page at /reset-password', () => {
    renderRoute('/reset-password');
    expect(screen.getByText('Reset Password')).toBeInTheDocument();
  });

  it('renders 404 page for unknown route', () => {
    renderRoute('/some-random-path');
    expect(screen.getByText('Not Found')).toBeInTheDocument();
  });
});
