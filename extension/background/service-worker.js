/**
 * Custos Quick Capture - Background Service Worker
 * Story 38.1: Browser Extension Scaffold
 * Story 38.5: Recent Captures Indicator
 *
 * Handles background tasks and extension lifecycle events.
 */

// Badge background color (brand color)
const BADGE_COLOR = '#2563eb';

// Extension installed or updated
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('Custos Quick Capture installed');
    // Initialize badge
    initializeBadge();
    // Open options page on first install
    chrome.runtime.openOptionsPage();
  } else if (details.reason === 'update') {
    console.log('Custos Quick Capture updated to', chrome.runtime.getManifest().version);
    // Initialize badge on update too
    initializeBadge();
  }
});

// Initialize badge on service worker startup
initializeBadge();

// Listen for messages from popup or options
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'HEALTH_CHECK') {
    // Perform health check from background
    performHealthCheck(message.url, message.apiKey)
      .then((result) => sendResponse(result))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }

  // Story 38.5: Handle capture notification from popup
  if (message.type === 'CAPTURE_SUBMITTED') {
    handleCaptureSubmitted(message.capture)
      .then(() => sendResponse({ success: true }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

/**
 * Perform health check against Custos backend
 */
async function performHealthCheck(url, apiKey) {
  try {
    const headers = {
      'Content-Type': 'application/json',
    };
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }

    const response = await fetch(`${url}/api/health`, {
      method: 'GET',
      headers,
    });

    if (response.ok) {
      const data = await response.json();
      return { success: true, status: data.status || 'ok' };
    } else {
      return { success: false, error: `HTTP ${response.status}` };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Update badge based on connection status
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && (changes.custosUrl || changes.custosApiKey)) {
    // Settings changed - could update badge here
    console.log('Custos settings updated');
  }
});

// =============================================================================
// Story 38.5: Badge and Recent Captures Management
// =============================================================================

/**
 * Get current date as ISO string (YYYY-MM-DD)
 */
function getTodayDateString() {
  return new Date().toISOString().split('T')[0];
}

/**
 * Initialize badge on startup
 */
async function initializeBadge() {
  try {
    // Set badge color
    await chrome.action.setBadgeBackgroundColor({ color: BADGE_COLOR });

    // Check if we need to reset for new day
    const data = await chrome.storage.local.get(['capturesToday', 'captureDate']);
    const today = getTodayDateString();

    if (data.captureDate !== today) {
      // New day - reset count
      await chrome.storage.local.set({
        capturesToday: 0,
        captureDate: today,
        recentCaptures: [],
      });
      await updateBadge(0);
    } else {
      // Same day - restore count
      await updateBadge(data.capturesToday || 0);
    }
  } catch (error) {
    console.warn('Failed to initialize badge:', error.message);
  }
}

/**
 * Update badge text based on count
 */
async function updateBadge(count) {
  try {
    if (count === 0) {
      // Hide badge when count is 0
      await chrome.action.setBadgeText({ text: '' });
    } else if (count > 99) {
      // Show "99+" for large counts
      await chrome.action.setBadgeText({ text: '99+' });
    } else {
      await chrome.action.setBadgeText({ text: String(count) });
    }
  } catch (error) {
    console.warn('Failed to update badge:', error.message);
  }
}

/**
 * Handle capture submitted from popup (Story 38.5 - Task 1.5, 2.1-2.3)
 */
async function handleCaptureSubmitted(capture) {
  // Defensive null check
  if (!capture || typeof capture !== 'object') {
    console.warn('handleCaptureSubmitted called with invalid capture:', capture);
    return;
  }

  try {
    const today = getTodayDateString();
    const data = await chrome.storage.local.get(['capturesToday', 'captureDate', 'recentCaptures']);

    // Check if new day (reset if so)
    let count = data.capturesToday || 0;
    let recentCaptures = data.recentCaptures || [];

    if (data.captureDate !== today) {
      count = 0;
      recentCaptures = [];
    }

    // Increment count
    count += 1;

    // Add to recent captures (newest first, max 5)
    const captureRecord = {
      timestamp: new Date().toISOString(),
      capture_type: capture.capture_type || 'notes',
      target_type: capture.target_type || 'meeting',
      target_name: capture.target_name || 'Unknown',
      text_preview: (capture.text_preview || '').substring(0, 100),
    };

    recentCaptures.unshift(captureRecord);
    if (recentCaptures.length > 5) {
      recentCaptures = recentCaptures.slice(0, 5);
    }

    // Save to storage
    await chrome.storage.local.set({
      capturesToday: count,
      captureDate: today,
      recentCaptures: recentCaptures,
    });

    // Update badge
    await updateBadge(count);
  } catch (error) {
    console.warn('Failed to handle capture submitted:', error.message);
    throw error;
  }
}
