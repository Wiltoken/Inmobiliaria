import { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Pencil, Trash2, RotateCcw, X, Users as UsersIcon } from 'lucide-react';
import { adminApi } from '../lib/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import toast from 'react-hot-toast';

const ROLE_LABELS = {
  buyer: 'Comprador',
  seller: 'Vendedor',
  agent: 'Agente',
  admin: 'Admin',
  super_admin: 'Super Admin',
};

const ROLE_OPTIONS = ['buyer', 'seller', 'agent', 'admin', 'super_admin'];

const EMPTY_FORM = {
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: 'buyer',
  is_active: true,
};

function userStatus(user) {
  if (user.deleted_at) return { label: 'Eliminado', variant: 'error' };
  if (!user.is_active) return { label: 'Inactivo', variant: 'warning' };
  if (user.is_locked) return { label: 'Bloqueado', variant: 'warning' };
  return { label: 'Activo', variant: 'success' };
}

export default function AdminUsersPage({ onPageView }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [roleFilter, setRoleFilter] = useState('');
  const [search, setSearch] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 20 };
      if (roleFilter) params.role = roleFilter;
      if (search) params.search = search;
      if (includeDeleted) params.include_deleted = true;
      const res = await adminApi.users(params);
      setUsers(res.data.users || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 0);
    } catch (e) {
      toast.error('Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  }, [page, roleFilter, search, includeDeleted]);

  useEffect(() => {
    onPageView?.('admin_users');
    loadUsers();
  }, [loadUsers]);

  const openCreate = () => {
    setEditingUser(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  };

  const openEdit = (user) => {
    setEditingUser(user);
    setForm({
      username: user.username,
      email: user.email,
      full_name: user.full_name || '',
      password: '',
      role: user.roles?.[0]?.name || 'buyer',
      is_active: user.is_active,
    });
    setModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingUser) {
        await adminApi.updateUser(editingUser.id, {
          email: form.email,
          full_name: form.full_name,
          roles: form.role ? [form.role] : [],
          is_active: form.is_active,
        });
        toast.success('Usuario actualizado');
      } else {
        await adminApi.createUser({
          username: form.username,
          email: form.email,
          full_name: form.full_name,
          password: form.password,
          role: form.role,
          is_active: form.is_active,
        });
        toast.success('Usuario creado');
      }
      setModalOpen(false);
      loadUsers();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail.forEach((d) => toast.error(typeof d === 'string' ? d : d.msg));
      } else if (detail) {
        toast.error(detail);
      } else {
        toast.error('Error al guardar el usuario');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`¿Eliminar a "${user.username}"? Esta acción es reversible.`)) return;
    try {
      await adminApi.deleteUser(user.id);
      toast.success('Usuario eliminado');
      loadUsers();
    } catch (e) {
      toast.error('Error al eliminar el usuario');
    }
  };

  const handleRestore = async (user) => {
    try {
      await adminApi.restoreUser(user.id);
      toast.success('Usuario restaurado');
      loadUsers();
    } catch (e) {
      toast.error('Error al restaurar el usuario');
    }
  };

  const setField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <div className="p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Administración de Usuarios</h1>
          <p className="text-gray-500 mt-1">
            {total} usuarios · Gestioná cuentas, roles y estados
          </p>
        </div>
        <Button variant="primary" leftIcon={<Plus className="w-4 h-4" />} onClick={openCreate}>
          Nuevo usuario
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="Buscar por usuario, email o nombre..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              leftIcon={<Search className="w-5 h-5" />}
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
            className="px-4 py-3 rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
          >
            <option value="">Todos los roles</option>
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeDeleted}
              onChange={(e) => { setIncludeDeleted(e.target.checked); setPage(1); }}
              className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            Incluir eliminados
          </label>
        </div>
      </Card>

      {/* Users table */}
      <Card>
        {loading ? (
          <div className="p-8 text-center text-gray-500">
            <UsersIcon className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            Cargando usuarios...
          </div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center">
            <UsersIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No se encontraron usuarios</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Usuario</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Rol</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Estado</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((user) => {
                  const status = userStatus(user);
                  return (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-900">
                          {user.full_name || user.username}
                          {user.full_name && (
                            <span className="text-gray-500 font-normal"> · @{user.username}</span>
                          )}
                        </p>
                        <p className="text-sm text-gray-500">{user.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {user.roles?.map((role) => (
                            <Badge key={role.id} variant="primary" size="sm">
                              {ROLE_LABELS[role.name] || role.name}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={status.variant} size="sm">{status.label}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {user.deleted_at ? (
                            <Button variant="ghost" size="sm" onClick={() => handleRestore(user)}>
                              <RotateCcw className="w-4 h-4" /> Restaurar
                            </Button>
                          ) : (
                            <>
                              <Button variant="ghost" size="sm" onClick={() => openEdit(user)}>
                                <Pencil className="w-4 h-4" /> Editar
                              </Button>
                              <Button variant="ghost" size="sm" className="text-error" onClick={() => handleDelete(user)}>
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Anterior
            </Button>
            <span className="text-sm text-gray-500">
              Página {page} de {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        )}
      </Card>

      {/* Create/Edit modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setModalOpen(false)} />
          <Card className="relative w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingUser ? 'Editar usuario' : 'Nuevo usuario'}
              </h2>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg hover:bg-gray-100 text-gray-500"
                aria-label="Cerrar"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
              {!editingUser && (
                <>
                  <Input
                    label="Usuario"
                    placeholder="Ej: juanperez"
                    value={form.username}
                    onChange={(e) => setField('username', e.target.value)}
                    required
                  />
                  <Input
                    label="Contraseña"
                    type="password"
                    placeholder="Mínimo 8 caracteres"
                    value={form.password}
                    onChange={(e) => setField('password', e.target.value)}
                    required
                  />
                </>
              )}
              <Input
                label="Email"
                type="email"
                placeholder="usuario@email.com"
                value={form.email}
                onChange={(e) => setField('email', e.target.value)}
                required
              />
              <Input
                label="Nombre completo"
                placeholder="Nombre y apellido"
                value={form.full_name}
                onChange={(e) => setField('full_name', e.target.value)}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
                <select
                  value={form.role}
                  onChange={(e) => setField('role', e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                >
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setField('is_active', e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm text-gray-700">Cuenta activa</span>
              </label>

              <div className="flex gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setModalOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" variant="primary" loading={saving} fullWidth>
                  {editingUser ? 'Guardar cambios' : 'Crear usuario'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
