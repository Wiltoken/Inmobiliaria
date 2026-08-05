import { Link } from 'react-router-dom';
import { Heart, Search, MessageSquare, ArrowRight, Sparkles } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import PropertyGrid from '../properties/PropertyGrid';
import { SkeletonPropertyList } from '../ui/Skeleton';
import EmptyState from '../ui/EmptyState';

export default function BuyerDashboard({
  matches = [],
  recentProperties = [],
  loading = false,
  stats = {},
}) {
  const formatPrice = (price, operation) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(price);
  };

  return (
    <div className="p-4 lg:p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">¡Bienvenido de vuelta!</h1>
        <p className="text-gray-500 mt-1">
          Encuentra tu próxima propiedad ideal
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Search className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.propertiesViewed || 0}</p>
              <p className="text-sm text-gray-500">Vistas</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.newMatches || 0}</p>
              <p className="text-sm text-gray-500">Nuevos matches</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <Heart className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.favorites || 0}</p>
              <p className="text-sm text-gray-500">Favoritos</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.activeInquiries || 0}</p>
              <p className="text-sm text-gray-500">Consultas activas</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Matches Carousel */}
      {matches.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-accent" />
              <h2 className="text-xl font-bold text-gray-900">Matches para ti</h2>
              <Badge variant="accent">{matches.length}</Badge>
            </div>
            <Link to="/matches">
              <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
                Ver todos
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {matches.slice(0, 3).map((match) => (
              <Link key={match.id} to={`/property/${match.property_id}`}>
                <Card hover className="relative">
                  <div className="absolute top-2 right-2 bg-accent text-white px-2 py-1 rounded-lg text-sm font-bold">
                    {Math.round(match.score)}% match
                  </div>
                  <div className="aspect-[4/3] bg-gray-100">
                    <img
                      src={match.property?.photos?.[0]?.url || `https://picsum.photos/seed/${match.property_id}/400/300`}
                      alt={match.property?.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="p-4">
                    <p className="text-xl font-bold text-primary">
                      {formatPrice(match.property?.price, match.property?.operation)}
                    </p>
                    <p className="font-medium text-gray-900 mt-1 line-clamp-1">
                      {match.property?.title}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {match.property?.location?.neighborhood}, {match.property?.location?.city}
                    </p>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Recent Properties */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Recién publicados</h2>
          <Link to="/search">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Ver todos
            </Button>
          </Link>
        </div>

        {loading ? (
          <SkeletonPropertyList count={3} />
        ) : recentProperties.length > 0 ? (
          <PropertyGrid properties={recentProperties.slice(0, 6)} />
        ) : (
          <EmptyState
            type="search"
            title="No hay propiedades publicadas"
            description="Vuelve más tarde para ver nuevas publicaciones"
          />
        )}
      </section>

      {/* Quick Search CTA */}
      <Card className="bg-gradient-to-r from-primary to-primary-light text-white p-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold">¿Buscas algo específico?</h3>
            <p className="text-white/80 mt-1">
              Utiliza nuestros filtros avanzados para encontrar tu propiedad ideal
            </p>
          </div>
          <Link to="/search">
            <Button
              variant="secondary"
              className="bg-white text-primary hover:bg-white/90"
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Buscar propiedades
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
