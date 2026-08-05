import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Bell, Menu, X, LogOut, User, Settings } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import Badge from '../ui/Badge';

export default function Navbar({ className = '' }) {
  const { user, logout, isAdmin } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className={`bg-white border-b border-gray-200 sticky top-0 z-50 ${className}`}>
      <div className="px-4 lg:px-6">
        <nav role="navigation" aria-label="Principal" className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">I</span>
            </div>
            <span className="text-xl font-bold text-primary hidden lg:block">Inmobiliaria</span>
          </Link>

          {/* Search Bar - Desktop */}
          <div className="flex-1 max-w-xl mx-8 hidden md:block">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="search"
                placeholder="Buscar propiedades..."
                aria-label="Búsqueda de propiedades"
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 bg-gray-50
                         focus:outline-none focus:ring-2 focus:ring-primary focus:bg-white"
              />
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Notifications */}
            <button
              className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label="Notificaciones"
            >
              <Bell className="w-5 h-5 text-gray-600" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-accent rounded-full" />
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                aria-expanded={showUserMenu}
                aria-haspopup="true"
              >
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </div>
                <span className="hidden lg:block text-sm font-medium text-gray-700">
                  {user?.username || 'Usuario'}
                </span>
              </button>

              {/* Dropdown Menu */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-gray-100 py-2">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="font-medium text-gray-900">{user?.username}</p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                    <div className="mt-1">
                      {user?.roles?.map((role) => (
                        <Badge key={role.id} size="sm" className="mr-1">
                          {role.name}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Link
                    to="/profile"
                    className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <User className="w-4 h-4" />
                    Mi Perfil
                  </Link>

                  <Link
                    to="/settings"
                    className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings className="w-4 h-4" />
                    Configuración
                  </Link>

                  {isAdmin() && (
                    <Link
                      to="/admin/analytics"
                      className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-50"
                      onClick={() => setShowUserMenu(false)}
                    >
                      Analytics
                    </Link>
                  )}

                  <div className="border-t border-gray-100 mt-2 pt-2">
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 px-4 py-2 text-error hover:bg-error/5 w-full"
                    >
                      <LogOut className="w-4 h-4" />
                      Cerrar Sesión
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </nav>
      </div>
    </header>
  );
}
