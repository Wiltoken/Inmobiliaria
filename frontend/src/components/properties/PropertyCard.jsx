import { Link } from 'react-router-dom';
import { Heart, MapPin, Bed, Bath, Square, Building2 } from 'lucide-react';
import Badge from '../ui/Badge';
import { useState } from 'react';
import { favoritesApi } from '../../lib/api';
import toast from 'react-hot-toast';

export default function PropertyCard({
  property,
  showMatchScore = false,
  matchScore = 0,
  onFavoriteToggle,
}) {
  const [isFavorite, setIsFavorite] = useState(property.is_favorite || false);
  const [imageError, setImageError] = useState(false);

  const formatPrice = (price, operation) => {
    const formatted = new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: operation === 'rent' ? 'COP' : 'COP',
      maximumFractionDigits: 0,
    }).format(price);

    return operation === 'rent' ? `${formatted}/mes` : formatted;
  };

  const handleFavoriteClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      if (isFavorite) {
        await favoritesApi.remove(property.id);
        setIsFavorite(false);
        toast.success('Eliminado de favoritos');
      } else {
        await favoritesApi.add(property.id);
        setIsFavorite(true);
        toast.success('Añadido a favoritos');
      }
      onFavoriteToggle?.(property.id, isFavorite ? 'remove' : 'add');
    } catch (error) {
      toast.error('Error al actualizar favoritos');
    }
  };

  const mainPhoto = property.photos?.[0]?.url ||
    `https://picsum.photos/seed/${property.id}/400/300`;

  const locationStr = property.location?.address ||
    property.location?.neighborhood ||
    property.location?.city ||
    'Ubicación no disponible';

  return (
    <Link to={`/property/${property.id}`} className="block">
      <div className="card-hover h-full flex flex-col">
        {/* Image Container */}
        <div className="relative aspect-[4/3] bg-gray-100 overflow-hidden">
          <img
            src={imageError ? `https://picsum.photos/seed/${property.id}/400/300` : mainPhoto}
            alt={property.title}
            className="w-full h-full object-cover property-image"
            onError={() => setImageError(true)}
            loading="lazy"
          />

          {/* Badges */}
          <div className="absolute top-2 left-2 flex gap-2">
            <Badge variant="primary" className="bg-primary text-white">
              {property.type === 'apartment' ? 'Apartamento' :
               property.type === 'house' ? 'Casa' :
               property.type === 'commercial' ? 'Comercial' :
               property.type === 'land' ? 'Terreno' :
               property.type === 'office' ? 'Oficina' :
               property.type === 'warehouse' ? 'Bodega' : property.type}
            </Badge>
            {property.operation === 'rent' && (
              <Badge variant="accent" className="bg-accent text-white">
                Arriendo
              </Badge>
            )}
            {property.operation === 'sale' && (
              <Badge variant="success" className="bg-success text-white">
                Venta
              </Badge>
            )}
          </div>

          {/* Match Score Badge */}
          {showMatchScore && matchScore > 0 && (
            <div className="match-score">
              {Math.round(matchScore)}% coincidencia
            </div>
          )}

          {/* Favorite Button */}
          <button
            onClick={handleFavoriteClick}
            className={`
              absolute top-2 right-2 p-2 rounded-full transition-all duration-200
              ${isFavorite
                ? 'bg-error text-white'
                : 'bg-white/90 text-gray-600 hover:bg-white hover:text-error'
              }
            `}
            aria-label={isFavorite ? 'Quitar de favoritos' : 'Añadir a favoritos'}
          >
            <Heart className={`w-5 h-5 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 flex-1 flex flex-col">
          {/* Price */}
          <div className="mb-2">
            <span className="price-large">
              {formatPrice(property.price, property.operation)}
            </span>
          </div>

          {/* Title */}
          <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 flex-1">
            {property.title}
          </h3>

          {/* Location */}
          <div className="flex items-center gap-1 text-gray-500 text-sm mb-3">
            <MapPin className="w-4 h-4 flex-shrink-0" />
            <span className="line-clamp-1">{locationStr}</span>
          </div>

          {/* Features */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            {property.area_m2 && (
              <div className="flex items-center gap-1">
                <Square className="w-4 h-4" />
                <span>{property.area_m2} m²</span>
              </div>
            )}
            {property.rooms && (
              <div className="flex items-center gap-1">
                <Bed className="w-4 h-4" />
                <span>{property.rooms}</span>
              </div>
            )}
            {property.bathrooms && (
              <div className="flex items-center gap-1">
                <Bath className="w-4 h-4" />
                <span>{property.bathrooms}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
