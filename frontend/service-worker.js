/**
 * Custos Service Worker
 * Provides offline caching and background sync for the Custos PWA
 *
 * Caching Strategy:
 * - Static assets: Cache-first (fast loads, update in background)
 * - API calls: Network-first with cache fallback (fresh data preferred)
 * - Offline captures: Queue and sync when online
 */

const CACHE_NAME = 'custos-v1';
const STATIC_CACHE_NAME = 'custos-static-v1';
const API_CACHE_NAME = 'custos-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/people.html',
  '/status.html',
  '/styles.css',
  '/app.js',
  '/capture.js',
  '/status.js',
  '/people.js',
  '/ui-state.js',
  '/offline-queue.js',
  '/config.js',
  '/manifest.json',
  '/favicon.svg',
  '/favicon.ico',
  '/icon-192.svg',
  '/icon-512.svg'
];

// API endpoints to cache for offline access
const CACHEABLE_API_PATTERNS = [
  /\/api\/people$/,
  /\/api\/briefings\/(next|today)$/,
  /\/api\/status\/summary$/,
  /\/api\/meetings/,
  /\/api\/commitments/
];

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        // Activate immediately without waiting for existing clients to close
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old versioned caches
              return name.startsWith('custos-') &&
                     name !== STATIC_CACHE_NAME &&
                     name !== API_CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        // Take control of all clients immediately
        return self.clients.claim();
      })
  );
});

/**
 * Fetch event - serve from cache or network
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests (let them pass through)
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // API requests: Network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // Static assets: Cache-first with network fallback
  event.respondWith(cacheFirstWithNetwork(request));
});

/**
 * Cache-first strategy for static assets
 * Returns cached version if available, otherwise fetches from network
 */
async function cacheFirstWithNetwork(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Return cached version and update cache in background
    updateCacheInBackground(request);
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // If both cache and network fail, return offline fallback for HTML
    if (request.headers.get('Accept')?.includes('text/html')) {
      const offlineResponse = await caches.match('/index.html');
      if (offlineResponse) {
        return offlineResponse;
      }
    }

    throw error;
  }
}

/**
 * Network-first strategy for API calls
 * Tries network first, falls back to cache if offline
 */
async function networkFirstWithCache(request) {
  const url = new URL(request.url);

  // Check if this API endpoint should be cached
  const shouldCache = CACHEABLE_API_PATTERNS.some(pattern => pattern.test(url.pathname));

  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok && shouldCache) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      console.log('[SW] Serving cached API response:', url.pathname);

      // Clone and modify response to indicate it's cached
      const cachedData = await cachedResponse.json();
      const modifiedData = { ...cachedData, cached: true, offline: true };

      return new Response(JSON.stringify(modifiedData), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Custos-Cached': 'true'
        }
      });
    }

    // No cache available, return error response
    return new Response(JSON.stringify({
      error: 'Offline',
      message: 'No cached data available',
      offline: true
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Update cache in background without blocking response
 */
function updateCacheInBackground(request) {
  fetch(request)
    .then((response) => {
      if (response.ok) {
        caches.open(STATIC_CACHE_NAME)
          .then((cache) => cache.put(request, response));
      }
    })
    .catch(() => {
      // Silently fail - we already served the cached version
    });
}

/**
 * Message event - handle commands from main thread
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_CACHE':
      caches.keys().then((names) => {
        return Promise.all(names.map((name) => caches.delete(name)));
      }).then(() => {
        event.ports[0]?.postMessage({ success: true });
      });
      break;

    case 'GET_CACHE_STATUS':
      getCacheStatus().then((status) => {
        event.ports[0]?.postMessage(status);
      });
      break;

    default:
      console.log('[SW] Unknown message type:', type);
  }
});

/**
 * Get current cache status for debugging
 */
async function getCacheStatus() {
  const cacheNames = await caches.keys();
  const status = {};

  for (const name of cacheNames) {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    status[name] = keys.length;
  }

  return {
    caches: status,
    version: CACHE_NAME
  };
}

/**
 * Background sync for offline captures
 * Triggered when connectivity is restored
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'custos-offline-sync') {
    event.waitUntil(syncOfflineCaptures());
  }
});

/**
 * Sync offline captures to server
 */
async function syncOfflineCaptures() {
  // Notify clients to perform sync
  const clients = await self.clients.matchAll();

  for (const client of clients) {
    client.postMessage({
      type: 'SYNC_OFFLINE_CAPTURES'
    });
  }
}
