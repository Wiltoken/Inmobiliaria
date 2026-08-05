import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MainLayout from '../../src/components/layout/MainLayout';

vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../../src/lib/auth', () => ({
  useAuth: () => ({
    user: { username: 'test', email: 'test@example.com', roles: [{ id: 1, name: 'buyer' }] },
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
    fetchProfile: vi.fn(),
    hasRole: () => false,
    isBuyer: () => true,
    isSeller: () => false,
    isAgent: () => false,
    isAdmin: () => false,
  }),
  AuthProvider: ({ children }) => children,
}));

vi.mock('../../src/lib/api', () => ({
  api: { defaults: { headers: { common: {} } } },
  authApi: { register: vi.fn(), login: vi.fn() },
  userApi: { me: vi.fn() },
  matchesApi: { list: vi.fn(() => Promise.resolve({ data: [] })) },
}));

vi.mock('../../src/lib/audit', () => ({
  trackRegistration: vi.fn(),
  trackLogin: vi.fn(),
}));

describe('Accessibility', () => {
  it('MainLayout has skip-to-content link', () => {
    render(
      <MemoryRouter>
        <MainLayout />
      </MemoryRouter>
    );
    expect(screen.getByText(/saltar al contenido/i)).toBeInTheDocument();
  });

  it('MainLayout has main landmark', () => {
    render(
      <MemoryRouter>
        <MainLayout />
      </MemoryRouter>
    );
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('Sidebar has navigation landmark', () => {
    render(
      <MemoryRouter>
        <MainLayout />
      </MemoryRouter>
    );
    expect(screen.getByRole('navigation', { name: /navegación principal/i })).toBeInTheDocument();
  });
});
