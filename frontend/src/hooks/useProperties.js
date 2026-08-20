import { useState, useCallback, useRef } from 'react';
import { propertiesApi } from '../lib/api';

/**
 * Hook for property list and search operations.
 */
export function useProperties() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  // Last filters used, so pagination (loadMore) keeps the same search context.
  const lastFiltersRef = useRef({});

  /**
   * Fetch properties with optional filters
   */
  const fetchProperties = useCallback(async (filters = {}, page = 1) => {
    lastFiltersRef.current = filters;
    setLoading(true);
    setError(null);

    try {
      // Only forward params supported by the backend PropertySearch schema,
      // skipping empty values so the API never receives invalid/empty filters
      // (e.g. empty strings for numeric fields cause a 422).
      const params = { page, limit: pagination.pageSize };
      const supportedFilters = [
        'type', 'operation', 'price_min', 'price_max',
        'rooms_min', 'bathrooms_min', 'area_min', 'area_max', 'query',
      ];
      supportedFilters.forEach((key) => {
        const value = filters[key];
        if (value !== undefined && value !== null && value !== '') {
          params[key] = value;
        }
      });

      const response = await propertiesApi.list(params);
      const { properties: items, total, total_pages } = response.data;

      setProperties(page === 1 ? items : [...properties, ...items]);
      setPagination({
        page,
        pageSize: pagination.pageSize,
        total,
        totalPages: total_pages,
      });

      return { items, total, totalPages: total_pages };
    } catch (err) {
      setError(err.message || 'Error al cargar propiedades');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [pagination.pageSize, properties]);

  /**
   * Search properties with filters
   */
  const searchProperties = useCallback(async (filters) => {
    return fetchProperties(filters, 1);
  }, [fetchProperties]);

  /**
   * Load more properties (pagination)
   */
  const loadMore = useCallback(async () => {
    if (pagination.page < pagination.totalPages && !loading) {
      return fetchProperties(lastFiltersRef.current, pagination.page + 1);
    }
    return null;
  }, [pagination.page, pagination.totalPages, loading, fetchProperties]);

  /**
   * Get single property by ID
   */
  const getProperty = useCallback(async (id) => {
    setLoading(true);
    setError(null);

    try {
      const response = await propertiesApi.get(id);
      return response.data;
    } catch (err) {
      setError(err.message || 'Error al cargar propiedad');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    properties,
    loading,
    error,
    pagination,
    fetchProperties,
    searchProperties,
    loadMore,
    getProperty,
  };
}
