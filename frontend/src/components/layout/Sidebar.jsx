import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import {
  Home,
  Search,
  Heart,
  MessageSquare,
  User,
  Building2,
  Users,
  FileText,
  BarChart3,
  PlusCircle,
  Shield,
} from 'lucide-react';

const buyerMenu = [
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/search', label: 'Buscar', icon: Search },
  { path: '/favorites', label: 'Favoritos', icon: Heart },
  { path: '/messages', label: 'Consultas', icon: MessageSquare },
  { path: '/profile', label: 'Perfil', icon: User },
];

const sellerMenu = [
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/my-properties', label: 'Mis Propiedades', icon: Building2 },
  { path: '/publish', label: 'Publicar', icon: PlusCircle },
  { path: '/messages', label: 'Consultas Recibidas', icon: MessageSquare },
  { path: '/profile', label: 'Perfil', icon: User },
];

const agentMenu = [
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/properties', label: 'Propiedades', icon: Building2 },
  { path: '/clients', label: 'Clientes', icon: Users },
  { path: '/matches', label: 'Matches', icon: Heart },
  { path: '/profile', label: 'Perfil', icon: User },
];

const adminMenu = [
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/admin/users', label: 'Usuarios', icon: Users },
  { path: '/admin/properties', label: 'Propiedades', icon: Building2 },
  { path: '/admin/audit', label: 'Auditoría', icon: FileText },
  { path: '/admin/analytics', label: 'Analíticas', icon: BarChart3 },
];

export default function Sidebar({ className = '' }) {
  const { isBuyer, isSeller, isAgent, isAdmin } = useAuth();
  const location = useLocation();

  let menuItems = buyerMenu;
  if (isSeller()) menuItems = sellerMenu;
  if (isAgent()) menuItems = agentMenu;
  if (isAdmin()) menuItems = adminMenu;

  return (
    <aside
      className={`
        fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200
        flex flex-col z-40 ${className}
      `}
    >
      {/* Menu Items */}
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-hide" aria-label="Navegación principal">
        <ul className="space-y-1 px-3">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  aria-current={isActive ? 'page' : undefined}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium
                    transition-all duration-200
                    ${isActive
                      ? 'bg-primary text-white'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }
                  `}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Admin section divider */}
      {isAdmin() && (
        <div className="px-3 py-2">
          <div className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-gray-400 uppercase">
            <Shield className="w-4 h-4" />
            Administración
          </div>
        </div>
      )}
    </aside>
  );
}
