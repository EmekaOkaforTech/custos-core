export function formatDate(value) {
  if (!value) return null;
  return new Date(value).toISOString().replace('T', ' ').slice(0, 16);
}

export function getApiBase() {
  if (typeof window !== 'undefined' && window.CUSTOS_API_BASE) {
    return normalizeApiBase(window.CUSTOS_API_BASE);
  }
  if (typeof localStorage !== 'undefined') {
    return normalizeApiBase(localStorage.getItem('custos_api_base') || '');
  }
  if (typeof globalThis !== 'undefined' && globalThis.__custos_api_base) {
    return normalizeApiBase(globalThis.__custos_api_base);
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

export function setApiBase(value) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_api_base', normalizeApiBase(value));
    return;
  }
  if (typeof globalThis !== 'undefined') {
    globalThis.__custos_api_base = normalizeApiBase(value);
  }
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

// Briefing cache state
let _briefingCache = null;

export function setBriefingCache(data) {
  _briefingCache = data;
  if (typeof sessionStorage !== 'undefined') {
    try {
      sessionStorage.setItem('custos_briefing_cache', JSON.stringify(data));
    } catch (e) {
      // Session storage may be unavailable or full
    }
  }
}

export function getBriefingCache() {
  if (_briefingCache) return _briefingCache;
  if (typeof sessionStorage !== 'undefined') {
    try {
      const cached = sessionStorage.getItem('custos_briefing_cache');
      if (cached) {
        _briefingCache = JSON.parse(cached);
        return _briefingCache;
      }
    } catch (e) {
      // Parse error or storage unavailable
    }
  }
  return null;
}

// Demo mode state
let _demoMode = false;

export function setDemoMode(enabled) {
  _demoMode = Boolean(enabled);
}

export function getDemoMode() {
  return _demoMode;
}

// Reflection closeout state
export function setReflectionCloseout(dateStr) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_reflection_closeout', dateStr || '');
  }
}

export function getReflectionCloseout() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('custos_reflection_closeout') || null;
  }
  return null;
}

// Capture form defaults state
export function setCaptureDefaults(defaults) {
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem('custos_capture_defaults', JSON.stringify(defaults));
    } catch (e) {
      // Storage may be unavailable or full
    }
  }
}

export function getCaptureDefaults() {
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem('custos_capture_defaults');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      // Parse error or storage unavailable
    }
  }
  return null;
}

export function clearCaptureDefaults() {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('custos_capture_defaults');
  }
}

// Calendar consent state
export function setCalendarConsent(granted) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_calendar_consent', granted ? 'true' : 'false');
  }
}

export function getCalendarConsent() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('custos_calendar_consent') === 'true';
  }
  return false;
}

// ============================================================================
// Epic 33: Briefing Mode (time-first vs person-first)
// ============================================================================

const BRIEFING_MODE_KEY = 'custos_briefing_mode';

export function getBriefingMode() {
  if (typeof localStorage === 'undefined') return 'time';
  return localStorage.getItem(BRIEFING_MODE_KEY) || 'time';
}

export function setBriefingMode(mode) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(BRIEFING_MODE_KEY, mode === 'person' ? 'person' : 'time');
  }
}

// ============================================================================
// Epic 34: Care Context Mode
// ============================================================================

const CARE_MODE_KEY = 'custos_care_mode';

export function getCareMode() {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(CARE_MODE_KEY) === 'true';
}

export function setCareMode(enabled) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(CARE_MODE_KEY, enabled ? 'true' : 'false');
    // Disable professional mode if enabling care mode (mutually exclusive)
    if (enabled) {
      localStorage.setItem(PROFESSIONAL_MODE_KEY, 'false');
    }
  }
}

// ============================================================================
// Epic 35: Professional Context Mode
// ============================================================================

const PROFESSIONAL_MODE_KEY = 'custos_professional_mode';

export function getProfessionalMode() {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(PROFESSIONAL_MODE_KEY) === 'true';
}

export function setProfessionalMode(enabled) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(PROFESSIONAL_MODE_KEY, enabled ? 'true' : 'false');
    // Disable care mode if enabling professional mode (mutually exclusive)
    if (enabled) {
      localStorage.setItem(CARE_MODE_KEY, 'false');
    }
  }
}

// ============================================================================
// Terminology (Epic 34/35)
// ============================================================================

export function getTerminology() {
  if (getCareMode()) {
    return {
      meeting: 'Visit',
      meetings: 'Visits',
      person: 'Care recipient',
      people: 'Care recipients',
      commitment: 'Follow-up',
      commitments: 'Follow-ups',
      session: 'Visit',
    };
  }
  if (getProfessionalMode()) {
    return {
      meeting: 'Session',
      meetings: 'Sessions',
      person: 'Client',
      people: 'Clients',
      commitment: 'Action item',
      commitments: 'Action items',
      session: 'Session',
    };
  }
  return {
    meeting: 'Meeting',
    meetings: 'Meetings',
    person: 'Person',
    people: 'People',
    commitment: 'Commitment',
    commitments: 'Commitments',
    session: 'Meeting',
  };
}

// ============================================================================
// Capture Types (Epic 34/35)
// ============================================================================

export function getCaptureTypes() {
  const baseTypes = [
    { value: 'notes', label: 'Notes' },
    { value: 'transcript', label: 'Transcript' },
    { value: 'audio', label: 'Audio recording' },
    { value: 'decision', label: 'Decision' },
    { value: 'follow-up', label: 'Follow-up' },
    { value: 'reflection', label: 'Reflection' },
  ];

  if (getCareMode()) {
    return [
      ...baseTypes,
      { value: 'observation', label: 'Observation' },
      { value: 'symptom', label: 'Symptom' },
      { value: 'mood', label: 'Mood' },
      { value: 'medication', label: 'Medication' },
    ];
  }

  if (getProfessionalMode()) {
    return [
      ...baseTypes,
      { value: 'intake', label: 'Intake' },
    ];
  }

  return baseTypes;
}
