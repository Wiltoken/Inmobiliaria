import { useEffect, useRef } from 'react';
import { useAuth } from '../lib/auth';
import {
  trackPageView,
  trackSearch,
  trackPropertyView,
  trackMatchView,
  trackInquiry,
  trackFavoriteToggle,
  trackRegistration,
  trackLogin,
  trackFilterUsed,
} from '../lib/audit';

/**
 * Hook for audit logging and BI event tracking.
 * Provides ready-to-use tracking functions.
 */
export function useAudit() {
  const { user } = useAuth();

  /**
   * Track page view with automatic route tracking
   */
  const trackPageViewFn = useCallback((page, properties = {}) => {
    trackPageView(page, {
      ...properties,
      user_id: user?.id,
    });
  }, [user?.id]);

  /**
   * Track search with filter details
   */
  const trackSearchFn = useCallback((filters, resultsCount) => {
    trackSearch(filters, resultsCount);
  }, []);

  /**
   * Track property view with time tracking
   */
  const trackPropertyViewFn = useCallback((propertyId, propertyType) => {
    const startTime = Date.now();
    return {
      startTime,
      complete: () => {
        const timeOnPage = Date.now() - startTime;
        trackPropertyView(propertyId, propertyType, timeOnPage);
      },
    };
  }, []);

  /**
   * Track match interaction
   */
  const trackMatchViewFn = useCallback((matchId, score) => {
    trackMatchView(matchId, score);
  }, []);

  /**
   * Track inquiry submission
   */
  const trackInquiryFn = useCallback((propertyId) => {
    const role = user?.roles?.[0]?.name || 'unknown';
    trackInquiry(propertyId, role);
  }, [user?.roles]);

  /**
   * Track favorite toggle
   */
  const trackFavoriteFn = useCallback((propertyId, action) => {
    trackFavoriteToggle(propertyId, action);
  }, []);

  /**
   * Track registration
   */
  const trackRegistrationFn = useCallback((role) => {
    trackRegistration(role);
  }, []);

  /**
   * Track login
   */
  const trackLoginFn = useCallback((method) => {
    trackLogin(method);
  }, []);

  /**
   * Track filter usage
   */
  const trackFilterFn = useCallback((filterType, value) => {
    trackFilterUsed(filterType, value);
  }, []);

  return {
    trackPageView: trackPageViewFn,
    trackSearch: trackSearchFn,
    trackPropertyView: trackPropertyViewFn,
    trackMatchView: trackMatchViewFn,
    trackInquiry: trackInquiryFn,
    trackFavorite: trackFavoriteFn,
    trackRegistration: trackRegistrationFn,
    trackLogin: trackLoginFn,
    trackFilter: trackFilterFn,
  };
}

// Need to import useCallback
import { useCallback } from 'react';
