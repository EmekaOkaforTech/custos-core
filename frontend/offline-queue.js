/**
 * Custos Offline Queue
 * Manages offline capture storage using IndexedDB with localStorage fallback
 *
 * Features:
 * - Queue captures when offline
 * - Persist across page reloads
 * - Automatic sync when online
 * - Retry logic with exponential backoff
 */

import { apiUrl, getApiHeaders } from './ui-state.js';

const DB_NAME = 'custos-offline';
const DB_VERSION = 1;
const STORE_NAME = 'pending-captures';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

let db = null;
let dbInitPromise = null;

/**
 * Initialize IndexedDB connection
 * @returns {Promise<IDBDatabase>}
 */
function initDB() {
  if (dbInitPromise) {
    return dbInitPromise;
  }

  dbInitPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      console.warn('[OfflineQueue] IndexedDB not available, using localStorage fallback');
      resolve(null);
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      console.error('[OfflineQueue] Failed to open IndexedDB:', request.error);
      resolve(null); // Fall back to localStorage
    };

    request.onsuccess = () => {
      db = request.result;
      console.log('[OfflineQueue] IndexedDB initialized');
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = event.target.result;

      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const store = database.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('synced', 'synced', { unique: false });
        console.log('[OfflineQueue] Object store created');
      }
    };
  });

  return dbInitPromise;
}

/**
 * Generate unique ID for queue entries
 * @returns {string}
 */
function generateId() {
  return `capture_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Queue a capture for later sync
 * @param {Object} captureData - The capture payload
 * @returns {Promise<string>} - The queued item ID
 */
export async function queueCapture(captureData) {
  const entry = {
    id: generateId(),
    timestamp: Date.now(),
    payload: captureData,
    synced: false,
    retryCount: 0,
    lastError: null
  };

  await initDB();

  if (db) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.add(entry);

      request.onsuccess = () => {
        console.log('[OfflineQueue] Capture queued:', entry.id);
        notifyPendingChange();
        resolve(entry.id);
      };

      request.onerror = () => {
        console.error('[OfflineQueue] Failed to queue capture:', request.error);
        // Fall back to localStorage
        queueToLocalStorage(entry);
        resolve(entry.id);
      };
    });
  } else {
    // localStorage fallback
    queueToLocalStorage(entry);
    return entry.id;
  }
}

/**
 * Fallback: Queue to localStorage
 * @param {Object} entry
 */
function queueToLocalStorage(entry) {
  if (typeof localStorage === 'undefined') {
    console.error('[OfflineQueue] No storage available');
    return;
  }

  const queue = getLocalStorageQueue();
  queue.push(entry);
  localStorage.setItem('custos_offline_queue', JSON.stringify(queue));
  console.log('[OfflineQueue] Capture queued to localStorage:', entry.id);
  notifyPendingChange();
}

/**
 * Get queue from localStorage
 * @returns {Array}
 */
function getLocalStorageQueue() {
  if (typeof localStorage === 'undefined') {
    return [];
  }

  try {
    const stored = localStorage.getItem('custos_offline_queue');
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.error('[OfflineQueue] Failed to parse localStorage queue:', e);
    return [];
  }
}

/**
 * Save queue to localStorage
 * @param {Array} queue
 */
function saveLocalStorageQueue(queue) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_offline_queue', JSON.stringify(queue));
  }
}

/**
 * Get all pending (unsynced) captures
 * @returns {Promise<Array>}
 */
export async function getPendingCaptures() {
  await initDB();

  if (db) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const index = store.index('synced');
      const request = index.getAll(IDBKeyRange.only(false));

      request.onsuccess = () => {
        resolve(request.result || []);
      };

      request.onerror = () => {
        console.error('[OfflineQueue] Failed to get pending captures:', request.error);
        resolve(getLocalStorageQueue().filter(e => !e.synced));
      };
    });
  } else {
    return getLocalStorageQueue().filter(e => !e.synced);
  }
}

/**
 * Get count of pending captures
 * @returns {Promise<number>}
 */
export async function getPendingCount() {
  const pending = await getPendingCaptures();
  return pending.length;
}

/**
 * Remove a capture from the queue
 * @param {string} id - The capture ID
 * @returns {Promise<boolean>}
 */
export async function removePendingCapture(id) {
  await initDB();

  if (db) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => {
        console.log('[OfflineQueue] Capture removed:', id);
        notifyPendingChange();
        resolve(true);
      };

      request.onerror = () => {
        console.error('[OfflineQueue] Failed to remove capture:', request.error);
        resolve(false);
      };
    });
  } else {
    const queue = getLocalStorageQueue();
    const filtered = queue.filter(e => e.id !== id);
    saveLocalStorageQueue(filtered);
    notifyPendingChange();
    return true;
  }
}

/**
 * Mark a capture as synced (but keep for history)
 * @param {string} id
 * @returns {Promise<boolean>}
 */
async function markAsSynced(id) {
  await initDB();

  if (db) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const entry = getRequest.result;
        if (entry) {
          entry.synced = true;
          entry.syncedAt = Date.now();
          const putRequest = store.put(entry);
          putRequest.onsuccess = () => resolve(true);
          putRequest.onerror = () => resolve(false);
        } else {
          resolve(false);
        }
      };

      getRequest.onerror = () => resolve(false);
    });
  } else {
    const queue = getLocalStorageQueue();
    const entry = queue.find(e => e.id === id);
    if (entry) {
      entry.synced = true;
      entry.syncedAt = Date.now();
      saveLocalStorageQueue(queue);
    }
    return true;
  }
}

/**
 * Update retry count and error for a capture
 * @param {string} id
 * @param {string} error
 * @returns {Promise<void>}
 */
async function updateRetryInfo(id, error) {
  await initDB();

  if (db) {
    return new Promise((resolve) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const entry = getRequest.result;
        if (entry) {
          entry.retryCount = (entry.retryCount || 0) + 1;
          entry.lastError = error;
          entry.lastRetryAt = Date.now();
          store.put(entry);
        }
        resolve();
      };

      getRequest.onerror = () => resolve();
    });
  } else {
    const queue = getLocalStorageQueue();
    const entry = queue.find(e => e.id === id);
    if (entry) {
      entry.retryCount = (entry.retryCount || 0) + 1;
      entry.lastError = error;
      entry.lastRetryAt = Date.now();
      saveLocalStorageQueue(queue);
    }
  }
}

/**
 * Sync all pending captures to the server
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<{synced: number, failed: number, errors: Array}>}
 */
export async function syncPendingCaptures(onProgress) {
  const pending = await getPendingCaptures();

  if (pending.length === 0) {
    console.log('[OfflineQueue] No pending captures to sync');
    return { synced: 0, failed: 0, errors: [] };
  }

  console.log(`[OfflineQueue] Syncing ${pending.length} pending captures`);

  let synced = 0;
  let failed = 0;
  const errors = [];

  for (const entry of pending) {
    // Skip if max retries exceeded
    if (entry.retryCount >= MAX_RETRIES) {
      console.warn(`[OfflineQueue] Max retries exceeded for ${entry.id}`);
      failed++;
      errors.push({ id: entry.id, error: 'Max retries exceeded' });
      continue;
    }

    try {
      const response = await fetch(apiUrl('/api/ingestion'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getApiHeaders()
        },
        body: JSON.stringify(entry.payload)
      });

      if (response.ok) {
        await removePendingCapture(entry.id);
        synced++;
        console.log(`[OfflineQueue] Synced capture ${entry.id}`);
      } else {
        const errorText = await response.text();
        await updateRetryInfo(entry.id, `HTTP ${response.status}: ${errorText}`);
        failed++;
        errors.push({ id: entry.id, error: `HTTP ${response.status}` });
      }
    } catch (error) {
      await updateRetryInfo(entry.id, error.message);
      failed++;
      errors.push({ id: entry.id, error: error.message });
      console.error(`[OfflineQueue] Failed to sync ${entry.id}:`, error);
    }

    // Progress callback
    if (onProgress) {
      onProgress({ synced, failed, total: pending.length });
    }

    // Small delay between requests to avoid overwhelming server
    if (pending.indexOf(entry) < pending.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  notifyPendingChange();

  return { synced, failed, errors };
}

/**
 * Notify listeners that pending count has changed
 */
function notifyPendingChange() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('custos-pending-change'));
  }
}

/**
 * Check if we're online
 * @returns {boolean}
 */
export function isOnline() {
  if (typeof navigator === 'undefined') {
    return true;
  }
  return navigator.onLine;
}

/**
 * Set up automatic sync when coming online
 */
export function setupAutoSync() {
  if (typeof window === 'undefined') {
    return;
  }

  window.addEventListener('online', async () => {
    console.log('[OfflineQueue] Online - starting sync');
    const result = await syncPendingCaptures();

    if (result.synced > 0) {
      window.dispatchEvent(new CustomEvent('custos-sync-complete', {
        detail: result
      }));
    }
  });

  // Also listen for service worker sync messages
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'SYNC_OFFLINE_CAPTURES') {
        syncPendingCaptures();
      }
    });
  }

  console.log('[OfflineQueue] Auto-sync initialized');
}

/**
 * Request background sync (if supported)
 * @returns {Promise<boolean>}
 */
export async function requestBackgroundSync() {
  if ('serviceWorker' in navigator && 'SyncManager' in window) {
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('custos-offline-sync');
      console.log('[OfflineQueue] Background sync registered');
      return true;
    } catch (error) {
      console.warn('[OfflineQueue] Background sync not available:', error);
      return false;
    }
  }
  return false;
}

/**
 * Clear all queued captures (for testing/reset)
 * @returns {Promise<void>}
 */
export async function clearQueue() {
  await initDB();

  if (db) {
    return new Promise((resolve) => {
      const transaction = db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.clear();
      request.onsuccess = () => {
        console.log('[OfflineQueue] Queue cleared');
        notifyPendingChange();
        resolve();
      };
      request.onerror = () => resolve();
    });
  } else {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('custos_offline_queue');
    }
    notifyPendingChange();
  }
}

// Initialize auto-sync on module load
if (typeof window !== 'undefined') {
  setupAutoSync();
}
