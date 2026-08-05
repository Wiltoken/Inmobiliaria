import { Home, Search, FolderOpen, Inbox, AlertCircle } from 'lucide-react';

const illustrations = {
  empty: Home,
  search: Search,
  folder: FolderOpen,
  inbox: Inbox,
  error: AlertCircle,
};

const messages = {
  empty: 'No hay nada aquí todavía',
  search: 'No encontramos resultados',
  folder: 'Esta carpeta está vacía',
  inbox: 'No tienes mensajes',
  error: 'Algo salió mal',
};

export function EmptyState({
  type = 'empty',
  title,
  description,
  action,
  className = '',
}) {
  const Icon = illustrations[type] || illustrations.empty;
  const defaultMessage = messages[type] || messages.empty;

  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
      <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <Icon className="w-10 h-10 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {title || defaultMessage}
      </h3>
      {description && (
        <p className="text-gray-500 mb-6 max-w-sm">{description}</p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}

export default EmptyState;
