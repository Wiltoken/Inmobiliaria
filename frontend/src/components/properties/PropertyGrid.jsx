import PropertyCard from './PropertyCard';
import { SkeletonPropertyList } from '../ui/Skeleton';
import EmptyState from '../ui/EmptyState';

export default function PropertyGrid({
  properties,
  loading = false,
  showMatchScore = false,
  matchScores = {},
  onLoadMore,
  hasMore = false,
  emptyMessage = 'No hay propiedades para mostrar',
}) {
  if (loading && properties.length === 0) {
    return <SkeletonPropertyList count={6} />;
  }

  if (!loading && properties.length === 0) {
    return (
      <EmptyState
        type="search"
        title="Sin resultados"
        description={emptyMessage}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Property Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {properties.map((property) => (
          <PropertyCard
            key={property.id}
            property={property}
            showMatchScore={showMatchScore}
            matchScore={matchScores[property.id] || 0}
          />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center py-8">
          <button
            onClick={onLoadMore}
            disabled={loading}
            className="btn-outline"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Cargando...
              </>
            ) : (
              'Cargar más propiedades'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
