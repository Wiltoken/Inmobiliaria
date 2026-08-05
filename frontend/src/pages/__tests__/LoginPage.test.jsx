import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../../pages/LoginPage';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock auth
const mockLogin = vi.fn();
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    isLoading: false,
  }),
  AuthProvider: ({ children }) => children,
}));

// Mock audit
vi.mock('../../lib/audit', () => ({
  trackLogin: vi.fn(),
}));

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with heading', () => {
    renderLogin();
    expect(screen.getByText('Inmobiliaria')).toBeInTheDocument();
    expect(screen.getByText('Inicia sesión en tu cuenta')).toBeInTheDocument();
  });

  it('renders username and password fields', () => {
    renderLogin();
    // The Input component renders labels as <label> elements, not linked via htmlFor
    expect(screen.getByText('Usuario o Email')).toBeInTheDocument();
    expect(screen.getByText('Contraseña')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  it('renders forgot password link', () => {
    renderLogin();
    expect(screen.getByText(/olvidaste tu contraseña/i)).toBeInTheDocument();
  });

  it('renders register link', () => {
    renderLogin();
    expect(screen.getByText(/regístrate aquí/i)).toBeInTheDocument();
  });

  it('allows typing username and password', async () => {
    renderLogin();
    // Find inputs by placeholder since Input component doesn't use htmlFor
    const usernameInput = screen.getByPlaceholderText('Ej: usuario123 o email@ejemplo.com');
    const passwordInput = screen.getByPlaceholderText('Tu contraseña');

    await userEvent.type(usernameInput, 'demo');
    await userEvent.type(passwordInput, 'demo123');

    expect(usernameInput).toHaveValue('demo');
    expect(passwordInput).toHaveValue('demo123');
  });

  it('shows validation error on empty submit', async () => {
    renderLogin();
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });
    await userEvent.click(submitButton);
    // Error appears both in alert span and input error paragraph
    const errors = screen.getAllByText('El usuario es requerido');
    expect(errors.length).toBeGreaterThanOrEqual(1);
  });
});
