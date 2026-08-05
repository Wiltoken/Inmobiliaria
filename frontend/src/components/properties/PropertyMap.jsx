import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function FitBounds({ properties }) {
  const map = useMap();

  const bounds = useMemo(() => {
    const validProps = properties.filter((p) => p.location?.lat && p.location?.lon);
    if (validProps.length === 0) return null;
    return validProps.map((p) => [p.location.lat, p.location.lon]);
  }, [properties]);

  useEffect(() => {
    if (bounds && bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [map, bounds]);

  return null;
}

export default function PropertyMap({ properties = [] }) {
  const formatPrice = (price) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(price);

  const validProperties = properties.filter(
    (p) => p.location?.lat && p.location?.lon
  );

  const center = validProperties.length > 0
    ? [validProperties[0].location.lat, validProperties[0].location.lon]
    : [4.57, -74.29]; // Colombia center

  return (
    <div className="h-96 rounded-xl overflow-hidden">
      <MapContainer
        center={center}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBounds properties={validProperties} />

        {validProperties.map((property) => (
          <Marker
            key={property.id}
            position={[property.location.lat, property.location.lon]}
          >
            <Popup>
              <div className="min-w-[180px]">
                <h3 className="font-semibold text-sm mb-1">{property.title}</h3>
                <p className="text-primary font-bold text-sm mb-2">
                  {formatPrice(property.price)}
                  {property.operation === 'rent' ? '/mes' : ''}
                </p>
                <p className="text-xs text-gray-500 mb-2">
                  {property.location.address || property.location.neighborhood || property.location.city}
                </p>
                <a
                  href={`/property/${property.id}`}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Ver detalle →
                </a>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
