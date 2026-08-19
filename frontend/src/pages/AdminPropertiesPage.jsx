import { useState, useEffect, useCallback } from 'react';
import { Search, Check, X, Building2 } from 'lucide-react';
import { adminApi } from '../lib/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import toast from 'react-hot-toast';

const STATUS_LABELS = {
  active: 'Activo',
  pending: 'Pendiente',
  sold: 'Vendido',
  rented: 'Arrendado',
  withdrawn: 'Retirado',
  rejected: 'Rechazado',
};

const STATUS_VARIANTS = {
  active: 'success',
  pending: 'warning',
  sold: 'secondary',
  rented: 'secondary',
  withdrawn: 'secondary',
  rejected: 'error',
};

const STATUS_OPTIONS = ['', 'pending', 'active', 'sold', 'rented', 'withdrawn', 'rejected'];

const TYPE_LABELS = {
  apartment: 'Apartamento',
  house: 'Casa',
  commercial: 'Comercial',
  land: 'Terreno',
  office: 'Oficina',
  warehouse: 'Bodega',
  room: 'Habitación',
};

const OPERATION_LABELS = {
  sale: 'Venta',
  rent: 'Arriendo',
  lease: 'Lease',
};

function formatCop(value) {
  if (value == null) return '—';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value);
}

export default function AdminPropertiesPage({ onPageView }) {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const [rejecting, setRejecting] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [saving, setSaving] = useState(false);

  const loadProperties = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 20 };
      if (statusFilter) params.status_filter = statusFilter;
      if (search) params.search = search;
      const res = await adminApi.properties(params);
      setProperties(res.data.properties || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 0);
    } catch (e) {
      toast.error('Error al cargar propiedades');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, search]);

  useEffect(() => {
    onPageView?.('admin_properties');
    loadProperties();
  }, [loadProperties]);

  const handleApprove = async (property) => {
    try {
      await adminApi.approveProperty(property.id);
      toast.success('Propiedad aprobada');
      loadProperties();
    } catch (e) {
      toast.error('Error al aprobar la propiedad');
    }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!rejectReason.trim()) return;
    setSaving(true);
    try {
      await adminApi.rejectProperty(rejecting.id, rejectReason.trim());
      toast.success('Propiedad rechazada');
      setRejecting(null);
      setRejectReason('');
      loadProperties();
    } catch (err) {
      toast.error('Error al rechazar la propiedad');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Moderación de Propiedades</h1>
        <p className="text-gray-500 mt-1">
          {total} propiedades · Aprueba o rechaza publicaciones
        </p>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="Buscar por título..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              leftIcon={<Search className="w-5 h-5" />}
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-4 py-3 rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
          >
            <option value="">Todos los estados</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Properties table */}
      <Card>
        {loading ? (
          <div className="p-8 text-center text-gray-500">
            <Building2 className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            Cargando propiedades...
          </div>
        ) : properties.length === 0 ? (
          <div className="p-8 text-center">
            <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No se encontraron propiedades</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Propiedad</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Tipo</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Precio</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Publicante</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Estado</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {properties.map((property) => (
                  <tr key={property.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-lg bg-gray-100 overflow-hidden flex-shrink-0">
                          {property.photo ? (
                            <img src={property.photo} alt={property.title} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-300">
                              <Building2 className="w-5 h-5" />
                            </div>
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{property.title}</p>
                          {property.rejection_reason && (
                            <p className="text-xs text-error">Motivo: {property.rejection_reason}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {TYPE_LABELS[property.type] || property.type} · {OPERATION_LABELS[property.operation] || property.operation}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">{formatCop(property.price)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {property.owner?.username || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANTS[property.status] || 'secondary'} size="sm">
                        {STATUS_LABELS[property.status] || property.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {(property.status === 'pending' || property.status === 'rejected') && (
                          <Button variant="success" size="sm" onClick={() => handleApprove(property)}>
                            <Check className="w-4 h-4" /> Aprobar
                          </Button>
                        )}
                        {property.status === 'pending' && (
                          <Button variant="danger" size="sm" onClick={() => { setRejecting(property); setRejectReason(''); }}>
                            <X className="w-4 h-4" /> Rechazar
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-between">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <span className="text-sm text-gray-500">Página {page} de {totalPages}</span>
            <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Siguiente
            </Button>
          </div>
        )}
      </Card>

      {/* Reject modal */}
      {rejecting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setRejecting(null)} />
          <Card className="relative w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Rechazar propiedad</h2>
              <button
                onClick={() => setRejecting(null)}
                className="p-1 rounded-lg hover:bg-gray-100 text-gray-500"
                aria-label="Cerrar"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              {rejecting.title}
            </p>
            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo del rechazo</label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  required
                  placeholder="Ej: Fotos de baja calidad, información incompleta, precio inconsistente..."
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={() => setRejecting(null)}>
                  Cancelar
                </Button>
                <Button type="submit" variant="danger" loading={saving} fullWidth>
                  Rechazar
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
