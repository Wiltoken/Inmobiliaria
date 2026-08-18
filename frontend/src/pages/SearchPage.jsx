import { useState, useEffect } from 'react';
import { Map, List, SlidersHorizontal, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useProperties } from '../hooks/useProperties';
import { trackSearch, trackFilterUsed } from '../lib/audit';
import { useAuth } from '../lib/auth';
import { matchesApi } from '../lib/api';
import PropertyGrid from '../components/properties/PropertyGrid';
import PropertyFilters from '../components/properties/PropertyFilters';
import PropertyMap from '../components/properties/PropertyMap';
import Button from '../components/ui/Button';
import { SkeletonPropertyList } from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';

export default function SearchPage({ onPageView }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'map'
  const [showFilters, setShowFilters] = useState(false);
  const [matchScores, setMatchScores] = useState({});

  const { isAuthenticated, isBuyer } = useAuth();

  const {
    properties,
    loading,
    pagination,
    searchProperties,
    loadMore,
  } = useProperties();

  // Parse initial filters from URL
  const getInitialFilters = () => {
    const filters = {};
    if (searchParams.get('type')) filters.type = searchParams.get('type').split(',');
    if (searchParams.get('operation')) filters.operation = searchParams.get('operation');
    if (searchParams.get('city')) filters.city = searchParams.get('city');
    if (searchParams.get('price_min')) filters.price_min = searchParams.get('price_min');
    if (searchParams.get('price_max')) filters.price_max = searchParams.get('price_max');
    return filters;
  };

  useEffect(() => {
    onPageView?.('search');
    const filters = getInitialFilters();
    if (Object.keys(filters).length > 0) {
      searchProperties(filters);
    } else {
      searchProperties({});
    }
  }, []);

  // Feature 1: Fetch match scores after properties load (non-blocking)
  useEffect(() => {
    if (!isAuthenticated || !isBuyer()) return;

    matchesApi.list()
      .then((res) => {
        const scores = {};
        const matches = res.data?.items || res.data || [];
        matches.forEach((m) => {
          if (m.property_id) {
            scores[m.property_id] = m.score;
          }
        });
        setMatchScores(scores);
      })
      .catch(() => {}); // Silently ignore — matches are additive
  }, [isAuthenticated]);

  const handleFilter = (filters) => {
    // Update URL params
    const params = new URLSearchParams();
    if (filters.type?.length) params.set('type', filters.type.join(','));
    if (filters.operation) params.set('operation', filters.operation);
    if (filters.city) params.set('city', filters.city);
    if (filters.price_min) params.set('price_min', filters.price_min);
    if (filters.price_max) params.set('price_max', filters.price_max);
    setSearchParams(params);

    // Track filter usage
    Object.entries(filters).forEach(([key, value]) => {
      if (value && key !== 'type') {
        trackFilterUsed(key, value);
      }
    });

    // Search
    searchProperties(filters);
  };

  const handleLoadMore = async () => {
    const result = await loadMore();
    if (result) {
      trackSearch(getInitialFilters(), result.total);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Buscar propiedades</h1>
              <p className="text-sm text-gray-500">
                {loading
                  ? 'Buscando...'
                  : `${pagination.total} propiedades encontradas`}
              </p>
            </div>

            <div className="flex items-center gap-2">
              {/* Mobile Filter Toggle */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="md:hidden btn-ghost p-2"
                aria-label="Filtros"
              >
                <SlidersHorizontal className="w-5 h-5" />
              </button>

              {/* View Toggle */}
              <div className="hidden md:flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('list')}
                  className={`
                    p-2 rounded-md transition-all
                    ${viewMode === 'list' ? 'bg-white shadow-sm' : 'hover:bg-gray-200'}
                  `}
                  aria-label="Vista de lista"
                >
                  <List className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`
                    p-2 rounded-md transition-all
                    ${viewMode === 'map' ? 'bg-white shadow-sm' : 'hover:bg-gray-200'}
                  `}
                  aria-label="Vista de mapa"
                >
                  <Map className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex">
        {/* Sidebar Filters - Desktop */}
        <aside className="hidden md:block w-72 flex-shrink-0 p-4">
          <div className="sticky top-24">
            <PropertyFilters
              onFilter={handleFilter}
              initialFilters={getInitialFilters()}
            />
          </div>
        </aside>

        {/* Mobile Filters Drawer */}
        {showFilters && (
          <div className="md:hidden fixed inset-0 z-50">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setShowFilters(false)}
            />
            <div className="absolute right-0 top-0 bottom-0 w-80 bg-white overflow-y-auto">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h2 className="font-semibold text-lg">Filtros</h2>
                <button
                  onClick={() => setShowFilters(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg"
                  aria-label="Cerrar"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4">
                <PropertyFilters
                  onFilter={handleFilter}
                  initialFilters={getInitialFilters()}
                />
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        <div className="flex-1 p-4">
          {loading && properties.length === 0 ? (
            <SkeletonPropertyList count={6} />
          ) : properties.length === 0 ? (
            <EmptyState
              type="search"
              title="Sin resultados"
              description="No encontramos propiedades con esos filtros. Intenta ampliar tu búsqueda."
              action={
                <Button
                  variant="outline"
                  onClick={() => handleFilter({})}
                >
                  Limpiar filtros
                </Button>
              }
            />
          ) : (
            <>
              {/* Map View */}
              {viewMode === 'map' && (
                <div className="mb-6 h-96 rounded-xl overflow-hidden">
                  <PropertyMap properties={properties} />
                </div>
              )}

              {/* Property Grid */}
              <PropertyGrid
                properties={properties}
                loading={loading}
                onLoadMore={handleLoadMore}
                hasMore={pagination.page < pagination.totalPages}
                showMatchScore={isAuthenticated && isBuyer()}
                matchScores={matchScores}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
