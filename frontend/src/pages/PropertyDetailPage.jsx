import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  MapPin, Bed, Bath, Square, Calendar, Building2,
  Heart, Share2, ChevronLeft, ChevronRight, Check, Sparkles,
} from 'lucide-react';
import { useAuth } from '../lib/auth';
import { propertiesApi, favoritesApi } from '../lib/api';
import {
  trackPropertyView,
  trackFavoriteToggle,
  trackInquiry,
} from '../lib/audit';
import PhotoGallery from '../components/properties/PhotoGallery';
import ContactForm from '../components/properties/ContactForm';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import toast from 'react-hot-toast';

const featureIcons = {
  parking: '🅿️',
  pool: '🏊',
  garden: '🌳',
  security: '🔒',
  elevator: '🛗',
  gym: '💪',
  bbq: '🔥',
  balcony: '🏠',
  closet: '👕',
  laundry: '👕',
};

export default function PropertyDetailPage({ onPageView }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, isBuyer, user } = useAuth();

  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [matchScore, setMatchScore] = useState(0);

  // Track time on page
  const startTime = Date.now();

  useEffect(() => {
    loadProperty();
  }, [id]);

  useEffect(() => {
    if (property) {
      onPageView?.('property_detail');
      const timeOnPage = Date.now() - startTime;
      trackPropertyView(id, property.type, timeOnPage);
    }
  }, [property]);

  const loadProperty = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await propertiesApi.get(id);
      setProperty(response.data);
      setIsFavorite(response.data.is_favorite || false);

      // Calculate match score if user is logged in and is a buyer
      if (isAuthenticated && isBuyer() && user?.buyer_profile) {
        const score = calculateMatchScore(response.data, user.buyer_profile);
        setMatchScore(score);
      }
    } catch (err) {
      setError('Propiedad no encontrada');
    } finally {
      setLoading(false);
    }
  };

  const calculateMatchScore = (property, profile) => {
    let score = 0;
    let factors = 0;

    // Price match
    if (profile.budget_min && profile.budget_max) {
      if (property.price >= profile.budget_min && property.price <= profile.budget_max) {
        score += 30;
      }
      factors++;
    }

    // Area match
    if (profile.area_min && profile.area_max) {
      if (property.area_m2 >= profile.area_min && property.area_m2 <= profile.area_max) {
        score += 20;
      }
      factors++;
    }

    // Rooms match
    if (profile.rooms_min) {
      if (property.rooms >= profile.rooms_min) {
        score += 20;
      }
      factors++;
    }

    // Property type match
    if (profile.preferred_property_types?.length) {
      if (profile.preferred_property_types.includes(property.type)) {
        score += 20;
      }
      factors++;
    }

    // Location match
    if (profile.preferred_locations?.length && property.location?.city) {
      if (profile.preferred_locations.includes(property.location.city)) {
        score += 10;
      }
    }

    return factors > 0 ? Math.round((score / (factors * 10)) * 100) : 0;
  };

  const handleFavoriteToggle = async () => {
    if (!isAuthenticated) {
      toast.error('Debes iniciar sesión para guardar favoritos');
      return;
    }

    try {
      if (isFavorite) {
        await favoritesApi.remove(id);
        setIsFavorite(false);
        toast.success('Eliminado de favoritos');
      } else {
        await favoritesApi.add(id);
        setIsFavorite(true);
        toast.success('Añadido a favoritos');
      }
      trackFavoriteToggle(id, isFavorite ? 'remove' : 'add');
    } catch (err) {
      toast.error('Error al actualizar favoritos');
    }
  };

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({
          title: property.title,
          text: `Mira esta propiedad: ${property.title}`,
          url,
        });
      } catch (err) {
        // User cancelled
      }
    } else {
      navigator.clipboard.writeText(url);
      toast.success('Enlace copiado al portapapeles');
    }
  };

  const formatPrice = (price, operation) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(price);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto p-4">
          <Skeleton className="w-full aspect-[4/3] rounded-xl mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-6 w-1/2" />
              <Skeleton className="h-64 w-full" />
            </div>
            <div>
              <Skeleton className="h-96 w-full rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="p-8 text-center max-w-md">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Propiedad no encontrada</h1>
          <p className="text-gray-500 mb-6">
            Esta propiedad no existe o ha sido eliminada.
          </p>
          <Button onClick={() => navigate('/search')}>
            Volver a buscar
          </Button>
        </Card>
      </div>
    );
  }

  const features = property.features || {};
  const featureList = Object.entries(features)
    .filter(([_, value]) => value === true)
    .map(([key]) => key);

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-0">
      {/* Gallery */}
      <div className="max-w-7xl mx-auto p-4 pt-4">
        <PhotoGallery
          photos={property.photos || []}
          title={property.title}
        />
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Header */}
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  {/* Badges */}
                  <div className="flex flex-wrap gap-2 mb-2">
                    <Badge variant="primary">
                      {property.type === 'apartment' ? 'Apartamento' :
                       property.type === 'house' ? 'Casa' :
                       property.type === 'commercial' ? 'Comercial' :
                       property.type === 'land' ? 'Terreno' :
                       property.type === 'office' ? 'Oficina' :
                       property.type === 'warehouse' ? 'Bodega' : property.type}
                    </Badge>
                    <Badge variant={property.operation === 'rent' ? 'accent' : 'success'}
                           className={property.operation === 'rent' ? 'bg-accent text-white' : 'bg-success text-white'}>
                      {property.operation === 'rent' ? 'Arriendo' : 'Venta'}
                    </Badge>
                    <Badge variant={property.status === 'active' ? 'success' : 'warning'}>
                      {property.status === 'active' ? 'Activo' :
                       property.status === 'pending' ? 'Pendiente' :
                       property.status === 'sold' ? 'Vendido' :
                       property.status === 'rented' ? 'Arrendado' : property.status}
                    </Badge>
                  </div>

                  {/* Match Score */}
                  {matchScore > 0 && (
                    <div className="flex items-center gap-1 mb-3">
                      <Sparkles className="w-4 h-4 text-accent" />
                      <span className="text-sm font-medium text-accent">
                        {matchScore}% coincidencia con tu perfil
                      </span>
                    </div>
                  )}

                  <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
                    {property.title}
                  </h1>

                  {/* Location */}
                  <div className="flex items-center gap-1 text-gray-500 mt-2">
                    <MapPin className="w-5 h-5" />
                    <span>
                      {property.location?.address ||
                       `${property.location?.neighborhood || ''}, ${property.location?.city || ''}`}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={handleFavoriteToggle}
                    className={`
                      p-3 rounded-lg border-2 transition-all
                      ${isFavorite
                        ? 'border-error text-error bg-error/5'
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                    aria-label={isFavorite ? 'Quitar de favoritos' : 'Añadir a favoritos'}
                  >
                    <Heart className={`w-5 h-5 ${isFavorite ? 'fill-current' : ''}`} />
                  </button>
                  <button
                    onClick={handleShare}
                    className="p-3 rounded-lg border-2 border-gray-200 hover:border-gray-300 transition-all"
                    aria-label="Compartir"
                  >
                    <Share2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Price */}
              <div className="mt-4 pt-4 border-t border-gray-100">
                <span className="text-3xl md:text-4xl font-bold text-primary">
                  {formatPrice(property.price, property.operation)}
                </span>
                {property.operation === 'rent' && (
                  <span className="text-gray-500">/mes</span>
                )}
              </div>
            </Card>

            {/* Key Features */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Características</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {property.area_m2 && (
                  <div className="flex items-center gap-2">
                    <Square className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Área</p>
                      <p className="font-medium">{property.area_m2} m²</p>
                    </div>
                  </div>
                )}
                {property.rooms && (
                  <div className="flex items-center gap-2">
                    <Bed className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Habitaciones</p>
                      <p className="font-medium">{property.rooms}</p>
                    </div>
                  </div>
                )}
                {property.bathrooms && (
                  <div className="flex items-center gap-2">
                    <Bath className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Baños</p>
                      <p className="font-medium">{property.bathrooms}</p>
                    </div>
                  </div>
                )}
                {property.location?.stratum && (
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Estrato</p>
                      <p className="font-medium">{property.location.stratum}</p>
                    </div>
                  </div>
                )}
                {property.year_built && (
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm text-gray-500">Año</p>
                      <p className="font-medium">{property.year_built}</p>
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Features */}
            {featureList.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Amenidades</h2>
                <div className="flex flex-wrap gap-2">
                  {featureList.map((feature) => (
                    <span
                      key={feature}
                      className="px-3 py-1.5 bg-gray-100 rounded-full text-sm flex items-center gap-1"
                    >
                      {featureIcons[feature] || '✓'}
                      <span className="capitalize">{feature.replace(/_/g, ' ')}</span>
                    </span>
                  ))}
                </div>
              </Card>
            )}

            {/* Description */}
            {property.description && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Descripción</h2>
                <p className="text-gray-600 whitespace-pre-line">
                  {property.description}
                </p>
              </Card>
            )}

            {/* Location Map Placeholder */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Ubicación</h2>
              <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <MapPin className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">Mapa en desarrollo</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Contact Form */}
            <ContactForm
              propertyId={id}
              propertyTitle={property.title}
              ownerId={property.owner_id}
            />

            {/* Agent Info */}
            {property.agent && (
              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                    <span className="text-primary font-bold">
                      {property.agent.username?.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{property.agent.username}</p>
                    <p className="text-sm text-gray-500">Agente inmobiliario</p>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
