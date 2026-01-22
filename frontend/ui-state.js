export function formatDate(value) {
  if (!value) return null;
  return new Date(value).toISOString().replace('T', ' ').slice(0, 16);
}

export function getApiBase() {
  if (typeof window !== 'undefined' && window.CUSTOS_API_BASE) {
    return normalizeApiBase(window.CUSTOS_API_BASE);
  }
  return '';
}

export function apiUrl(path) {
  const base = getApiBase();
  if (!base) return path;
  return `${base}${path}`;
}

export function getApiHeaders() {
  const headers = {};
  if (typeof localStorage !== 'undefined') {
    const apiKey = localStorage.getItem('custos_api_key');
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
  }
  return headers;
}

export function getStoredApiKey() {
  if (typeof localStorage === 'undefined') {
    return '';
  }
  return localStorage.getItem('custos_api_key') || '';
}

export function isSetupComplete() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('custos_setup_complete') === 'true';
  }
  return getSetupCompleteFallback();
}

export function setSetupComplete(value) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_setup_complete', value ? 'true' : 'false');
    return;
  }
  if (typeof globalThis !== 'undefined') {
    globalThis.__custos_setup_complete = value ? 'true' : 'false';
  }
}

export function getSetupCompleteFallback() {
  if (typeof globalThis === 'undefined') {
    return false;
  }
  return globalThis.__custos_setup_complete === 'true';
}

function normalizeApiBase(value) {
  if (!value) return '';
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

export function statusLabel(status, lastSourceAt) {
  const relative = relativeFromNow(lastSourceAt);
  if (status === 'missing') return 'Missing: no recent context';
  if (status === 'stale') return `Stale: last source ${relative}`;
  return `Last source: ${relative}`;
}

export const SEED_BANNER_COPY = 'Showing example data from seeded fixtures.';

export function isSeedIdentifier(value) {
  if (!value) return false;
  if (value.startsWith('seed://')) return true;
  return (
    value.startsWith('p_seed_') ||
    value.startsWith('m_seed_') ||
    value.startsWith('sr_seed_') ||
    value.startsWith('c_seed_')
  );
}

export function relativeFromNow(value) {
  if (!value) return 'no recent source';
  const then = new Date(value);
  const diffMs = Date.now() - then.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days <= 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

export function computeBriefMeta({ cached, offline, updatedAt }) {
  const formatted = formatDate(updatedAt) || 'unknown';
  if (offline) {
    return {
      showOffline: true,
      statusText: `Last updated: ${formatted} (cached)`,
    };
  }
  if (cached) {
    return {
      showOffline: false,
      statusText: `Updated ${formatted} (cached)`,
    };
  }
  return {
    showOffline: false,
    statusText: `Updated ${formatted}`,
  };
}
