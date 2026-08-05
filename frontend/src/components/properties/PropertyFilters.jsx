import { useState } from 'react';
import { ChevronDown, X, SlidersHorizontal } from 'lucide-react';
import Button from '../ui/Button';
import Input from '../ui/Input';

const propertyTypes = [
  { value: 'apartment', label: 'Apartamento' },
  { value: 'house', label: 'Casa' },
  { value: 'commercial', label: 'Local/Bodega' },
  { value: 'land', label: 'Terreno' },
  { value: 'office', label: 'Oficina' },
];

const propertyOperations = [
  { value: 'sale', label: 'Venta' },
  { value: 'rent', label: 'Arriendo' },
];

export default function PropertyFilters({
  onFilter,
  initialFilters = {},
  className = '',
}) {
  const [filters, setFilters] = useState({
    operation: initialFilters.operation || 'sale',
    type: initialFilters.type || [],
    price_min: initialFilters.price_min || '',
    price_max: initialFilters.price_max || '',
    city: initialFilters.city || '',
    neighborhood: initialFilters.neighborhood || '',
    rooms_min: initialFilters.rooms_min || '',
    bathrooms_min: initialFilters.bathrooms_min || '',
    area_min: initialFilters.area_min || '',
    area_max: initialFilters.area_max || '',
    radius: initialFilters.radius || 5,
  });

  const [showFilters, setShowFilters] = useState(false);

  const handleTypeToggle = (value) => {
    setFilters((prev) => ({
      ...prev,
      type: prev.type.includes(value)
        ? prev.type.filter((t) => t !== value)
        : [...prev.type, value],
    }));
  };

  const handleOperationChange = (value) => {
    setFilters((prev) => ({ ...prev, operation: value }));
  };

  const handleChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onFilter(filters);
    setShowFilters(false);
  };

  const handleReset = () => {
    const resetFilters = {
      operation: 'sale',
      type: [],
      price_min: '',
      price_max: '',
      city: '',
      neighborhood: '',
      rooms_min: '',
      bathrooms_min: '',
      area_min: '',
      area_max: '',
      radius: 5,
    };
    setFilters(resetFilters);
    onFilter(resetFilters);
  };

  return (
    <div className={`bg-white rounded-xl border border-gray-200 ${className}`}>
      {/* Mobile Filter Toggle */}
      <button
        onClick={() => setShowFilters(!showFilters)}
        className="md:hidden w-full flex items-center justify-between p-4"
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-5 h-5" />
          <span className="font-medium">Filtros</span>
        </div>
        <ChevronDown
          className={`w-5 h-5 transition-transform ${showFilters ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Filter Form */}
      <form
        onSubmit={handleSubmit}
        className={`
          ${showFilters ? 'block' : 'hidden'}
          md:block p-4 space-y-4
        `}
      >
        {/* Operation Toggle */}
        <div>
          <label className="label">Operación</label>
          <div className="flex gap-2">
            {propertyOperations.map((op) => (
              <button
                key={op.value}
                type="button"
                onClick={() => handleOperationChange(op.value)}
                className={`
                  flex-1 py-2 px-4 rounded-lg font-medium text-sm transition-all
                  ${filters.operation === op.value
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }
                `}
              >
                {op.label}
              </button>
            ))}
          </div>
        </div>

        {/* Property Type */}
        <div>
          <label className="label">Tipo de propiedad</label>
          <div className="flex flex-wrap gap-2">
            {propertyTypes.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => handleTypeToggle(type.value)}
                className={`
                  px-3 py-1.5 rounded-full text-sm font-medium transition-all
                  ${filters.type.includes(type.value)
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }
                `}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        {/* Price Range */}
        <div>
          <label className="label">Rango de precio (COP)</label>
          <div className="flex gap-2 items-center">
            <Input
              type="number"
              placeholder="Mínimo"
              aria-label="Precio mínimo"
              value={filters.price_min}
              onChange={(e) => handleChange('price_min', e.target.value)}
              className="flex-1"
            />
            <span className="text-gray-400">-</span>
            <Input
              type="number"
              placeholder="Máximo"
              aria-label="Precio máximo"
              value={filters.price_max}
              onChange={(e) => handleChange('price_max', e.target.value)}
              className="flex-1"
            />
          </div>
        </div>

        {/* Location */}
        <div className="grid grid-cols-2 gap-2">
          <Input
            label="Ciudad"
            placeholder="Ej: Bogotá"
            value={filters.city}
            onChange={(e) => handleChange('city', e.target.value)}
          />
          <Input
            label="Barrio"
            placeholder="Ej: Chapinero"
            value={filters.neighborhood}
            onChange={(e) => handleChange('neighborhood', e.target.value)}
          />
        </div>

        {/* Rooms & Bathrooms */}
        <div className="grid grid-cols-2 gap-2">
          <Input
            label="Habitaciones min."
            type="number"
            min="1"
            value={filters.rooms_min}
            onChange={(e) => handleChange('rooms_min', e.target.value)}
          />
          <Input
            label="Baños min."
            type="number"
            min="1"
            value={filters.bathrooms_min}
            onChange={(e) => handleChange('bathrooms_min', e.target.value)}
          />
        </div>

        {/* Area Range */}
        <div>
          <label className="label">Área (m²)</label>
          <div className="flex gap-2 items-center">
            <Input
              type="number"
              placeholder="Mín"
              aria-label="Área mínima"
              value={filters.area_min}
              onChange={(e) => handleChange('area_min', e.target.value)}
              className="flex-1"
            />
            <span className="text-gray-400">-</span>
            <Input
              type="number"
              placeholder="Máx"
              aria-label="Área máxima"
              value={filters.area_max}
              onChange={(e) => handleChange('area_max', e.target.value)}
              className="flex-1"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={handleReset}>
            Limpiar
          </Button>
          <Button type="submit" variant="primary" className="flex-1">
            Aplicar filtros
          </Button>
        </div>
      </form>
    </div>
  );
}
