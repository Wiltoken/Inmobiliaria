import { getAccessToken } from './auth';
import { api } from './api';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Log a user action to the backend audit system.
 * Fire-and-forget - failures are silently ignored.
 */
export function logAction(action, details = {}) {
  const user = getCurrentUser();
  const payload = {
    action,
    details: {
      ...details,
      url: window.location.href,
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
    },
  };

  // Use fetch for fire-and-forget behavior
  fetch(`${API_URL}/audit/user-action`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(user?.token ? { Authorization: `Bearer ${user.token}` } : {}),
    },
    body: JSON.stringify(payload),
  }).catch(() => {
    // Silently ignore failures
  });
}

/**
 * Get current user from localStorage
 */
function getCurrentUser() {
  try {
    const stored = localStorage.getItem('inmobiliaria_auth');
    if (stored) {
      return JSON.parse(stored).user;
    }
  } catch {
    // Ignore
  }
  return null;
}

// ── Business Intelligence Event Trackers ──────────────────────────────────────

/**
 * Track page view
 */
export function trackPageView(page, properties = {}) {
  logAction('page_view', {
    page,
    ...properties,
  });
}

/**
 * Track search performed
 */
export function trackSearch(filters, resultsCount) {
  logAction('search_performed', {
    filters,
    results_count: resultsCount,
  });
}

/**
 * Track property viewed
 */
export function trackPropertyView(propertyId, propertyType, timeOnPage) {
  logAction('property_viewed', {
    property_id: propertyId,
    property_type: propertyType,
    time_on_page: timeOnPage,
  });
}

/**
 * Track match viewed
 */
export function trackMatchView(matchId, score) {
  logAction('match_viewed', {
    match_id: matchId,
    score,
  });
}

/**
 * Track inquiry sent
 */
export function trackInquiry(propertyId, fromRole) {
  logAction('inquiry_sent', {
    property_id: propertyId,
    from_role: fromRole,
  });
}

/**
 * Track favorite toggled
 */
export function trackFavoriteToggle(propertyId, action) {
  logAction('favorite_toggled', {
    property_id: propertyId,
    action, // 'add' or 'remove'
  });
}

/**
 * Track registration complete
 */
export function trackRegistration(role) {
  logAction('registration_complete', {
    role,
  });
}

/**
 * Track login
 */
export function trackLogin(method) {
  logAction('login', {
    method, // 'email_password', etc.
  });
}

/**
 * Track filter used
 */
export function trackFilterUsed(filterType, value) {
  logAction('filter_used', {
    filter_type: filterType,
    value,
  });
}
