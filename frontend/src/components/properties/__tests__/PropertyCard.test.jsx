import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import PropertyCard from '../PropertyCard';

const mockProperty = {
  id: '550e8400-e29b-41d4-a716-446655440001',
  title: 'Apartamento en Chapinero',
  price: 350000000,
  operation: 'sale',
  type: 'apartment',
  area_m2: 85,
  rooms: 3,
  bathrooms: 2,
  photos: [{ url: 'https://example.com/photo.jpg' }],
  location: {
    address: 'Calle 63 #9-45',
    neighborhood: 'Chapinero Alto',
    city: 'Bogotá',
  },
  is_favorite: false,
};

function renderWithRouter(ui) {
  return render(
    <MemoryRouter>
      <Toaster />
      {ui}
    </MemoryRouter>
  );
}

describe('PropertyCard', () => {
  it('renders property title', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    expect(screen.getByText('Apartamento en Chapinero')).toBeInTheDocument();
  });

  it('renders formatted price for sale', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    // Intl.NumberFormat('es-CO') uses non-breaking space as group separator
    // e.g., "$\xa0350.000.000" — match flexibly
    const price = screen.getByText((content) => content.includes('350') && content.includes('000'));
    expect(price).toBeInTheDocument();
  });

  it('renders /mes suffix for rent', () => {
    const rentProperty = { ...mockProperty, operation: 'rent', price: 2500000 };
    renderWithRouter(<PropertyCard property={rentProperty} />);
    expect(screen.getByText(/\/mes/)).toBeInTheDocument();
  });

  it('renders location address', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    expect(screen.getByText('Calle 63 #9-45')).toBeInTheDocument();
  });

  it('renders area in m²', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    // Intl formats "85 m²" — the m² may have a space
    const area = screen.getByText((content) => content.includes('85') && content.includes('m'));
    expect(area).toBeInTheDocument();
  });

  it('renders apartment type badge', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    expect(screen.getByText('Apartamento')).toBeInTheDocument();
  });

  it('renders sale badge', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    expect(screen.getByText('Venta')).toBeInTheDocument();
  });

  it('renders rent badge for rent properties', () => {
    const rentProperty = { ...mockProperty, operation: 'rent' };
    renderWithRouter(<PropertyCard property={rentProperty} />);
    expect(screen.getByText('Arriendo')).toBeInTheDocument();
  });

  it('shows match score when showMatchScore is true', () => {
    renderWithRouter(<PropertyCard property={mockProperty} showMatchScore matchScore={85} />);
    expect(screen.getByText('85% coincidencia')).toBeInTheDocument();
  });

  it('links to property detail page', () => {
    renderWithRouter(<PropertyCard property={mockProperty} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/property/550e8400-e29b-41d4-a716-446655440001');
  });
});
