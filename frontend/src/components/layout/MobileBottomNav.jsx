import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Home, Search, Heart, MessageSquare, User } from 'lucide-react';

export default function MobileBottomNav({ className = '' }) {
  const { isBuyer, isSeller } = useAuth();
  const location = useLocation();

  const getMenuItems = () => {
    if (isBuyer()) {
      return [
        { path: '/dashboard', label: 'Inicio', icon: Home },
        { path: '/search', label: 'Buscar', icon: Search },
        { path: '/favorites', label: 'Favoritos', icon: Heart },
        { path: '/messages', label: 'Consultas', icon: MessageSquare },
        { path: '/profile', label: 'Perfil', icon: User },
      ];
    }
    if (isSeller()) {
      return [
        { path: '/dashboard', label: 'Inicio', icon: Home },
        { path: '/my-properties', label: 'Mis Props', icon: Heart },
        { path: '/publish', label: 'Publicar', icon: Home },
        { path: '/messages', label: 'Consultas', icon: MessageSquare },
        { path: '/profile', label: 'Perfil', icon: User },
      ];
    }
    return [
      { path: '/dashboard', label: 'Inicio', icon: Home },
      { path: '/search', label: 'Buscar', icon: Search },
      { path: '/favorites', label: 'Favoritos', icon: Heart },
      { path: '/messages', label: 'Consultas', icon: MessageSquare },
      { path: '/profile', label: 'Perfil', icon: User },
    ];
  };

  const menuItems = getMenuItems();

  return (
    <nav
      className={`
        fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200
        mobile-bottom-nav z-50 ${className}
      `}
    >
      <div className="flex items-center justify-around h-16">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`
                flex flex-col items-center justify-center gap-1 px-3 py-2
                transition-colors duration-200 min-w-[60px]
                ${isActive ? 'text-primary' : 'text-gray-500'}
              `}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : ''}`} />
              <span className="text-xs font-medium">{item.label}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
