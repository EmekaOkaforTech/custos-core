export function formatDate(value) {
  if (!value) return null;
  return new Date(value).toISOString().replace('T', ' ').slice(0, 16);
}

export function statusLabel(status, lastSourceAt) {
  const relative = relativeFromNow(lastSourceAt);
  if (status === 'missing') return 'Missing: no recent context';
  if (status === 'stale') return `Stale: last source ${relative}`;
  return `Last source: ${relative}`;
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
