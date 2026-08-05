import { Link } from 'react-router-dom';
import { Building2, Eye, MessageSquare, Plus, TrendingUp, ArrowRight } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import { SkeletonPropertyList } from '../ui/Skeleton';

export default function SellerDashboard({
  properties = [],
  loading = false,
  stats = {},
}) {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(price);
  };

  const activeProperties = properties.filter(p => p.status === 'active');
  const pendingProperties = properties.filter(p => p.status === 'pending');

  return (
    <div className="p-4 lg:p-6 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Panel de Vendedor</h1>
          <p className="text-gray-500 mt-1">
            Gestiona tus propiedades y consultas
          </p>
        </div>
        <Link to="/publish">
          <Button leftIcon={<Plus className="w-4 h-4" />}>
            Publicar propiedad
          </Button>
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{activeProperties.length}</p>
              <p className="text-sm text-gray-500">Activas</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{pendingProperties.length}</p>
              <p className="text-sm text-gray-500">Pendientes</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Eye className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalViews || 0}</p>
              <p className="text-sm text-gray-500">Vistas totales</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.pendingInquiries || 0}</p>
              <p className="text-sm text-gray-500">Consultas pendientes</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Active Properties */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Mis propiedades activas</h2>
          <Link to="/my-properties">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Ver todas
            </Button>
          </Link>
        </div>

        {loading ? (
          <SkeletonPropertyList count={3} />
        ) : activeProperties.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeProperties.slice(0, 6).map((property) => (
              <Link key={property.id} to={`/property/${property.id}`}>
                <Card hover>
                  <div className="aspect-[4/3] bg-gray-100 relative">
                    <img
                      src={property.photos?.[0]?.url || `https://picsum.photos/seed/${property.id}/400/300`}
                      alt={property.title}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2">
                      <Badge variant="success" className="bg-success text-white">
                        Activo
                      </Badge>
                    </div>
                  </div>
                  <div className="p-4">
                    <p className="text-xl font-bold text-primary">
                      {formatPrice(property.price)}
                    </p>
                    <p className="font-medium text-gray-900 mt-1 line-clamp-1">
                      {property.title}
                    </p>
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Eye className="w-4 h-4" />
                        {property.view_count || 0}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-4 h-4" />
                        {property.inquiry_count || 0}
                      </span>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center">
            <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900">No tienes propiedades activas</h3>
            <p className="text-gray-500 mt-1 mb-4">
              Publica tu primera propiedad para comenzar
            </p>
            <Link to="/publish">
              <Button leftIcon={<Plus className="w-4 h-4" />}>
                Publicar propiedad
              </Button>
            </Link>
          </Card>
        )}
      </section>

      {/* Pending Review */}
      {pendingProperties.length > 0 && (
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Pendientes de aprobación</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingProperties.map((property) => (
              <Card key={property.id} className="flex items-center gap-4 p-4">
                <div className="w-20 h-20 rounded-lg bg-gray-100 flex-shrink-0 overflow-hidden">
                  <img
                    src={property.photos?.[0]?.url || `https://picsum.photos/seed/${property.id}/200/200`}
                    alt={property.title}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{property.title}</p>
                  <Badge variant="warning" size="sm" className="mt-1">
                    Pendiente
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* CTA */}
      <Card className="bg-gradient-to-r from-accent to-amber-500 text-white p-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold">¿Quieres más visibilidad?</h3>
            <p className="text-white/80 mt-1">
              Destaca tus propiedades para atraer más compradores
            </p>
          </div>
          <Button variant="secondary" className="bg-white text-accent hover:bg-white/90">
            Destacar propiedades
          </Button>
        </div>
      </Card>
    </div>
  );
}
