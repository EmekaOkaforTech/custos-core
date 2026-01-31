/**
 * Custos Quick Capture - Popup Script
 * Story 38.1: Browser Extension Scaffold
 * Story 38.2: Popup Quick Capture Form
 * Story 38.3: Page Context Extraction
 */

// State
let settings = {
  custosUrl: '',
  custosApiKey: '',
};

// Cache for meetings and people
let meetingsCache = null;
let meetingsCacheTime = 0;
let peopleCache = null;
let peopleCacheTime = 0;
const CACHE_TTL = 60000; // 1 minute cache

// Current target mode: 'meeting' or 'person'
let targetMode = 'meeting';

// Story 38.3: Page context state
let currentPageContext = null;
const MAX_SELECTION_LENGTH = 10240; // 10KB limit for selected text

// Valid capture types per target mode
const MEETING_CAPTURE_TYPES = ['notes', 'transcript', 'decision', 'follow-up', 'reflection'];
const PERSON_CAPTURE_TYPES = ['notes', 'transcript', 'observation', 'symptom', 'mood', 'medication', 'intake'];

// DOM Elements
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const notConfigured = document.getElementById('not-configured');
const connected = document.getElementById('connected');
const errorState = document.getElementById('error-state');
const errorText = document.getElementById('error-text');
const captureText = document.getElementById('capture-text');
const captureType = document.getElementById('capture-type');
const submitCapture = document.getElementById('submit-capture');
const captureResult = document.getElementById('capture-result');

// Story 38.2 elements
const targetMeetingBtn = document.getElementById('target-meeting');
const targetPersonBtn = document.getElementById('target-person');
const meetingSelectRow = document.getElementById('meeting-select-row');
const personSelectRow = document.getElementById('person-select-row');
const meetingSelect = document.getElementById('meeting-select');
const personSelect = document.getElementById('person-select');

// Story 38.3 elements
const pageContextInfo = document.getElementById('page-context-info');
const pageContextText = document.getElementById('page-context-text');
const includeSourceUrlCheckbox = document.getElementById('include-source-url');

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  await loadLastUsedSettings();
  await loadSourceUrlPreference(); // Story 38.3
  await extractPageContext(); // Story 38.3
  await checkConnection();
  setupEventListeners();

  // Story 38.4: Ensure focus on textarea for keyboard shortcut activation (AC #2)
  // Focus is set in extractPageContext when text is pre-filled, but we need to
  // ensure focus even when no text was selected (shortcut from any page)
  ensureFocusOnTextarea();
});

/**
 * Ensure focus is on capture textarea (Story 38.4 - AC #2)
 * Called after initialization to guarantee focus regardless of activation method
 */
function ensureFocusOnTextarea() {
  // Only focus if connected state is visible (not on error/not-configured)
  // Null checks for defensive programming
  if (connected && captureText && !connected.classList.contains('hidden')) {
    // Small delay to ensure DOM is fully ready after state changes
    setTimeout(() => {
      if (connected && !connected.classList.contains('hidden') && captureText) {
        captureText.focus();
      }
    }, 50);
  }
}

/**
 * Load settings from Chrome storage
 */
async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['custosUrl', 'custosApiKey'], (result) => {
      if (chrome.runtime.lastError) {
        console.warn('Failed to load settings:', chrome.runtime.lastError.message);
      }
      settings.custosUrl = result.custosUrl || '';
      settings.custosApiKey = result.custosApiKey || '';
      resolve();
    });
  });
}

// Store pending capture type to restore after dropdown is populated
let pendingCaptureType = null;

/**
 * Load last-used capture settings (Story 38.2 - AC #6)
 */
async function loadLastUsedSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.get([
      'lastCaptureType',
      'lastTargetMode',
      'lastMeetingId',
      'lastPersonId',
    ], (result) => {
      if (chrome.runtime.lastError) {
        console.warn('Failed to load last-used settings:', chrome.runtime.lastError.message);
      }

      // Store capture type for restoration after updateTargetUI populates dropdown
      if (result.lastCaptureType) {
        pendingCaptureType = result.lastCaptureType;
      }

      // Restore target mode
      if (result.lastTargetMode === 'person') {
        targetMode = 'person';
      }

      // Update UI - this populates capture type dropdown
      // updateCaptureTypes() is called inside and will restore pendingCaptureType
      updateTargetUI();

      resolve();
    });
  });
}

/**
 * Save last-used capture settings (Story 38.2 - AC #6)
 */
async function saveLastUsedSettings() {
  const lastUsedData = {
    lastCaptureType: captureType.value,
    lastTargetMode: targetMode,
    lastMeetingId: meetingSelect.value || null,
    lastPersonId: personSelect.value || null,
  };
  chrome.storage.local.set(lastUsedData, () => {
    if (chrome.runtime.lastError) {
      console.warn('Failed to save settings:', chrome.runtime.lastError.message);
    }
  });
}

/**
 * Check connection to Custos backend
 */
async function checkConnection() {
  if (!settings.custosUrl) {
    showState('not-configured');
    setStatus('disconnected', 'Not configured');
    return;
  }

  setStatus('connecting', 'Connecting...');

  try {
    const response = await fetch(`${settings.custosUrl}/api/health`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (response.ok) {
      setStatus('connected', 'Connected');
      showState('connected');
      // Load meetings and people after successful connection
      await Promise.all([
        loadMeetings(),
        loadPeople(),
      ]);
      // Restore last selected meeting/person after loading
      await restoreLastSelections();
      // Smart default: if no meetings but people exist, suggest person mode
      autoSuggestTargetMode();
    } else if (response.status === 401) {
      setStatus('disconnected', 'Auth failed');
      showError('Invalid API key. Check your settings.');
    } else {
      setStatus('disconnected', 'Error');
      showError(`Backend returned error: ${response.status}`);
    }
  } catch (error) {
    setStatus('disconnected', 'Offline');
    showError('Cannot connect to Custos backend. Check the URL in settings.');
  }
}

/**
 * Restore last selected meeting/person (Story 38.2 - AC #6)
 */
async function restoreLastSelections() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['lastMeetingId', 'lastPersonId'], (result) => {
      if (chrome.runtime.lastError) {
        console.warn('Failed to restore selections:', chrome.runtime.lastError.message);
        resolve();
        return;
      }
      if (result.lastMeetingId && meetingSelect) {
        const option = meetingSelect.querySelector(`option[value="${result.lastMeetingId}"]`);
        if (option) {
          meetingSelect.value = result.lastMeetingId;
        }
      }
      if (result.lastPersonId && personSelect) {
        const option = personSelect.querySelector(`option[value="${result.lastPersonId}"]`);
        if (option) {
          personSelect.value = result.lastPersonId;
        }
      }
      resolve();
    });
  });
}

// =============================================================================
// Story 38.3: Page Context Extraction
// =============================================================================

/**
 * Extract selected text and page info from active tab (Story 38.3 - AC #1, #2)
 */
async function extractPageContext() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      console.warn('No active tab found');
      currentPageContext = { text: '', url: '', title: '', restricted: true };
      return;
    }

    // Check for restricted URLs (Task 5.1)
    if (!tab.url ||
        tab.url.startsWith('chrome://') ||
        tab.url.startsWith('chrome-extension://') ||
        tab.url.startsWith('about:') ||
        tab.url.startsWith('edge://') ||
        tab.url.startsWith('moz-extension://')) {
      currentPageContext = {
        text: '',
        url: tab.url || '',
        title: tab.title || '',
        restricted: true,
      };
      return;
    }

    // Execute script to get selected text (Task 2.1)
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString(),
      });

      let selectedText = results[0]?.result || '';

      // Truncate extremely long selections (Task 5.4)
      if (selectedText.length > MAX_SELECTION_LENGTH) {
        selectedText = selectedText.substring(0, MAX_SELECTION_LENGTH) + '... [truncated]';
      }

      currentPageContext = {
        text: selectedText.trim(),
        url: tab.url,
        title: tab.title || '',
        restricted: false,
      };

      // Pre-fill textarea if text was selected (Task 3.1, 3.2)
      if (currentPageContext.text) {
        captureText.value = currentPageContext.text;
        captureText.classList.add('auto-filled');

        // Set cursor at end (Task 3.3)
        captureText.focus();
        captureText.setSelectionRange(captureText.value.length, captureText.value.length);

        // Update submit button state
        updateSubmitButton();

        // Show visual indicator (Task 3.4)
        showPageContextIndicator();
      }
    } catch (scriptError) {
      // Handle pages that block content scripts (Task 5.2)
      console.warn('Cannot execute script on this page:', scriptError.message);
      currentPageContext = {
        text: '',
        url: tab.url,
        title: tab.title || '',
        restricted: false,
        error: scriptError.message,
      };
    }
  } catch (error) {
    console.warn('Failed to extract page context:', error.message);
    currentPageContext = { text: '', url: '', title: '', error: error.message };
  }
}

/**
 * Show page context indicator when text was auto-filled (Task 3.4)
 */
function showPageContextIndicator() {
  if (!currentPageContext || !pageContextInfo || !pageContextText) return;

  let displayText = '';
  if (currentPageContext.title) {
    displayText = `From: ${currentPageContext.title}`;
  } else if (currentPageContext.url) {
    // Show truncated URL - decode first to handle multi-byte chars properly
    try {
      const url = new URL(currentPageContext.url);
      let pathDisplay = url.pathname;
      try {
        pathDisplay = decodeURIComponent(url.pathname);
      } catch {
        // Keep encoded if decode fails
      }
      // Truncate at character boundary (not byte)
      if (pathDisplay.length > 30) {
        pathDisplay = pathDisplay.substring(0, 27) + '...';
      }
      displayText = `From: ${url.hostname}${pathDisplay}`;
    } catch {
      displayText = 'From current page';
    }
  }

  if (displayText) {
    pageContextText.textContent = displayText;
    pageContextInfo.classList.remove('hidden');
  }
}

/**
 * Hide page context indicator (called when user clears or starts fresh)
 */
function hidePageContextIndicator() {
  if (pageContextInfo) {
    pageContextInfo.classList.add('hidden');
  }
}

/**
 * Load source URL checkbox preference (Task 4.2)
 */
async function loadSourceUrlPreference() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['includeSourceUrl'], (result) => {
      if (chrome.runtime.lastError) {
        console.warn('Failed to load source URL preference:', chrome.runtime.lastError.message);
      }
      if (includeSourceUrlCheckbox && result.includeSourceUrl !== undefined) {
        includeSourceUrlCheckbox.checked = result.includeSourceUrl;
      }
      resolve();
    });
  });
}

/**
 * Save source URL checkbox preference (Task 4.2)
 */
function saveSourceUrlPreference() {
  if (!includeSourceUrlCheckbox) return;
  chrome.storage.local.set({ includeSourceUrl: includeSourceUrlCheckbox.checked }, () => {
    if (chrome.runtime.lastError) {
      console.warn('Failed to save source URL preference:', chrome.runtime.lastError.message);
    }
  });
}

/**
 * Sanitize URL for safe embedding in payload text (prevents injection)
 */
function sanitizeUrlForPayload(url) {
  if (!url) return '';
  try {
    // Parse and re-construct to ensure valid URL
    const parsed = new URL(url);
    // Only allow http/https protocols for safety
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return '';
    }
    // Remove control characters and limit length
    const sanitized = parsed.href.replace(/[\x00-\x1f\x7f]/g, '');
    // Limit URL length to prevent abuse
    return sanitized.substring(0, 2048);
  } catch {
    return '';
  }
}

/**
 * Build payload text with optional source URL (Task 4.3)
 */
function buildPayloadWithSourceUrl(text) {
  if (!includeSourceUrlCheckbox?.checked || !currentPageContext?.url) {
    return text;
  }

  const sanitizedUrl = sanitizeUrlForPayload(currentPageContext.url);
  if (!sanitizedUrl) {
    return text;
  }

  // Prepend source URL to payload
  const sourcePrefix = `[Source: ${sanitizedUrl}]\n\n`;
  return sourcePrefix + text;
}

// =============================================================================
// Original functions continue below
// =============================================================================

/**
 * Build request headers
 */
function buildHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (settings.custosApiKey) {
    headers['X-API-Key'] = settings.custosApiKey;
  }
  return headers;
}

/**
 * Set status indicator
 */
function setStatus(state, text) {
  statusIndicator.className = `status-indicator ${state}`;
  statusText.textContent = text;
}

/**
 * Show a specific state container
 */
function showState(state) {
  notConfigured.classList.add('hidden');
  connected.classList.add('hidden');
  errorState.classList.add('hidden');

  switch (state) {
    case 'not-configured':
      notConfigured.classList.remove('hidden');
      break;
    case 'connected':
      connected.classList.remove('hidden');
      break;
    case 'error':
      errorState.classList.remove('hidden');
      break;
  }
}

/**
 * Show error state
 */
function showError(message) {
  errorText.textContent = message;
  showState('error');
}

/**
 * Show capture result
 * Note: Uses textContent to prevent XSS from server-controlled error messages
 */
function showCaptureResult(success, message) {
  captureResult.className = `capture-result ${success ? 'success' : 'error'}`;

  // Clear existing content safely
  captureResult.innerHTML = '';

  // Create icon element
  const iconSpan = document.createElement('span');
  iconSpan.className = 'result-icon';
  iconSpan.textContent = success ? '✓' : '✗';

  // Create text element (use textContent for XSS protection)
  const textSpan = document.createElement('span');
  textSpan.className = 'result-text';
  textSpan.textContent = message;

  captureResult.appendChild(iconSpan);
  captureResult.appendChild(textSpan);
  captureResult.classList.remove('hidden');

  // Auto-hide success after 3 seconds, errors stay visible longer (5 seconds)
  const hideDelay = success ? 3000 : 5000;
  setTimeout(() => {
    captureResult.classList.add('hidden');
  }, hideDelay);
}

/**
 * Load meetings from backend (Story 38.2 - AC #3)
 */
async function loadMeetings() {
  // Check cache
  const now = Date.now();
  if (meetingsCache && (now - meetingsCacheTime) < CACHE_TTL) {
    populateMeetingSelect(meetingsCache);
    return;
  }

  meetingSelect.classList.add('loading');
  meetingSelect.innerHTML = '<option value="">Loading meetings...</option>';

  try {
    const response = await fetch(`${settings.custosUrl}/api/meetings?range=today`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (response.ok) {
      const data = await response.json();
      // API returns {meetings: [...]} format
      meetingsCache = data.meetings || [];
      meetingsCacheTime = now;
      populateMeetingSelect(meetingsCache);
    } else {
      meetingSelect.innerHTML = '<option value="">-- Failed to load --</option>';
    }
  } catch (error) {
    meetingSelect.innerHTML = '<option value="">-- Error loading --</option>';
  } finally {
    meetingSelect.classList.remove('loading');
  }
}

/**
 * Populate meeting select dropdown
 */
function populateMeetingSelect(meetings) {
  meetingSelect.innerHTML = '<option value="">-- No meeting --</option>';

  if (!meetings || meetings.length === 0) {
    return;
  }

  meetings.forEach((meeting) => {
    const option = document.createElement('option');
    option.value = meeting.id;

    // Format time if available
    let label = meeting.title || 'Untitled Meeting';
    if (meeting.starts_at) {
      const time = new Date(meeting.starts_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });
      label = `${time} - ${label}`;
    }

    option.textContent = label;
    meetingSelect.appendChild(option);
  });
}

/**
 * Load people from backend (Story 38.2 - AC #4)
 */
async function loadPeople() {
  // Check cache
  const now = Date.now();
  if (peopleCache && (now - peopleCacheTime) < CACHE_TTL) {
    populatePersonSelect(peopleCache);
    return;
  }

  personSelect.classList.add('loading');
  personSelect.innerHTML = '<option value="">Loading people...</option>';

  try {
    const response = await fetch(`${settings.custosUrl}/api/people`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (response.ok) {
      const data = await response.json();
      // API returns array directly, not wrapped in object
      peopleCache = Array.isArray(data) ? data : (data.people || []);
      peopleCacheTime = now;
      populatePersonSelect(peopleCache);
    } else {
      personSelect.innerHTML = '<option value="">-- Failed to load --</option>';
    }
  } catch (error) {
    personSelect.innerHTML = '<option value="">-- Error loading --</option>';
  } finally {
    personSelect.classList.remove('loading');
  }
}

/**
 * Populate person select dropdown
 */
function populatePersonSelect(people) {
  personSelect.innerHTML = '<option value="">-- No person --</option>';

  if (!people || people.length === 0) {
    return;
  }

  // Sort by name
  const sorted = [...people].sort((a, b) =>
    (a.name || '').localeCompare(b.name || '')
  );

  sorted.forEach((person) => {
    const option = document.createElement('option');
    option.value = person.id;
    option.textContent = person.name || 'Unknown';
    personSelect.appendChild(option);
  });
}

/**
 * Auto-suggest target mode based on available data
 * If no meetings exist but people do, switch to person mode
 */
function autoSuggestTargetMode() {
  // Only auto-switch if user hasn't already selected a meeting/person
  const hasMeetingSelected = meetingSelect.value !== '';
  const hasPersonSelected = personSelect.value !== '';

  if (hasMeetingSelected || hasPersonSelected) {
    return; // User has made a selection, don't override
  }

  const noMeetings = !meetingsCache || meetingsCache.length === 0;
  const hasPeople = peopleCache && peopleCache.length > 0;

  // Switch to person mode if no meetings but people exist
  if (noMeetings && hasPeople && targetMode === 'meeting') {
    targetMode = 'person';
    updateTargetUI();
  }
}

/**
 * Update target UI based on current mode
 */
function updateTargetUI() {
  if (targetMode === 'meeting') {
    targetMeetingBtn.classList.add('active');
    targetMeetingBtn.setAttribute('aria-pressed', 'true');
    targetPersonBtn.classList.remove('active');
    targetPersonBtn.setAttribute('aria-pressed', 'false');
    meetingSelectRow.classList.remove('hidden');
    personSelectRow.classList.add('hidden');
  } else {
    targetMeetingBtn.classList.remove('active');
    targetMeetingBtn.setAttribute('aria-pressed', 'false');
    targetPersonBtn.classList.add('active');
    targetPersonBtn.setAttribute('aria-pressed', 'true');
    meetingSelectRow.classList.add('hidden');
    personSelectRow.classList.remove('hidden');
  }
  // Update capture types for current mode
  updateCaptureTypes();
}

/**
 * Update capture type dropdown based on target mode
 */
function updateCaptureTypes() {
  const types = targetMode === 'meeting' ? MEETING_CAPTURE_TYPES : PERSON_CAPTURE_TYPES;
  const currentValue = captureType.value;

  // Build type labels
  const typeLabels = {
    notes: 'Notes',
    transcript: 'Transcript',
    decision: 'Decision',
    'follow-up': 'Follow-up',
    reflection: 'Reflection',
    observation: 'Observation',
    symptom: 'Symptom',
    mood: 'Mood',
    medication: 'Medication',
    intake: 'Intake',
  };

  captureType.innerHTML = '';
  types.forEach((type) => {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = typeLabels[type] || type;
    captureType.appendChild(option);
  });

  // Priority: pendingCaptureType (from storage) > currentValue > first option
  let valueToRestore = null;
  if (pendingCaptureType && types.includes(pendingCaptureType)) {
    valueToRestore = pendingCaptureType;
    pendingCaptureType = null; // Clear after use
  } else if (types.includes(currentValue)) {
    valueToRestore = currentValue;
  }

  captureType.value = valueToRestore || types[0];
}

/**
 * Submit capture to backend (Story 38.2 - AC #5, Story 38.3 - AC #3)
 */
async function submitCaptureToBackend() {
  const rawText = captureText.value.trim();
  if (!rawText) return;

  // Build payload with optional source URL (Story 38.3 - Task 4.3)
  const text = buildPayloadWithSourceUrl(rawText);

  submitCapture.disabled = true;
  submitCapture.textContent = 'Capturing...';

  try {
    let url;
    let payload;

    if (targetMode === 'person' && personSelect.value) {
      // Use person-specific notes endpoint
      url = `${settings.custosUrl}/api/people/${personSelect.value}/notes`;
      payload = {
        payload: text,
        capture_type: captureType.value,
      };
    } else if (targetMode === 'meeting' && meetingSelect.value) {
      // Use ingestion endpoint with meeting
      url = `${settings.custosUrl}/api/ingestion`;
      payload = {
        payload: text,
        capture_type: captureType.value,
        meeting_id: meetingSelect.value,
      };
    } else {
      // No target selected
      showCaptureResult(false, 'Select a meeting or person first');
      submitCapture.disabled = false;
      submitCapture.textContent = 'Capture';
      return;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      const data = await response.json();
      showCaptureResult(true, `Captured! Job: ${data.job_id?.slice(0, 8)}...`);

      // Story 38.5: Notify service worker of successful capture for badge update
      const targetName = targetMode === 'person'
        ? personSelect.options[personSelect.selectedIndex]?.text || 'Unknown'
        : meetingSelect.options[meetingSelect.selectedIndex]?.text || 'Unknown';

      notifyCaptureSubmitted({
        capture_type: captureType.value,
        target_type: targetMode,
        target_name: targetName,
        text_preview: rawText.substring(0, 100),
      });

      captureText.value = '';
      // Clear auto-filled state and hide page context indicator
      captureText.classList.remove('auto-filled');
      hidePageContextIndicator();
      // Refresh recent captures display
      loadRecentCaptures();
      // Save settings after successful capture
      await saveLastUsedSettings();
    } else {
      const error = await response.json();
      showCaptureResult(false, error.detail || 'Failed to capture');
    }
  } catch (error) {
    showCaptureResult(false, 'Network error');
  } finally {
    submitCapture.disabled = false;
    submitCapture.textContent = 'Capture';
    updateSubmitButton();
  }
}

/**
 * Update submit button state based on input
 */
function updateSubmitButton() {
  submitCapture.disabled = !captureText.value.trim();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Open settings
  document.getElementById('open-settings').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  document.getElementById('settings-link').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });

  // Retry connection
  document.getElementById('retry-connection').addEventListener('click', async () => {
    await loadSettings();
    await checkConnection();
  });

  // Capture text input - consolidated handler for efficiency
  captureText.addEventListener('input', () => {
    updateSubmitButton();

    // Auto-resize textarea
    captureText.style.height = 'auto';
    captureText.style.height = Math.min(captureText.scrollHeight, 200) + 'px';

    // Story 38.3: Clear auto-filled styling when user edits
    captureText.classList.remove('auto-filled');

    // Hide page context indicator if textarea is now empty (user cleared it)
    if (!captureText.value.trim()) {
      hidePageContextIndicator();
    }
  });

  // Submit capture
  submitCapture.addEventListener('click', submitCaptureToBackend);

  // Keyboard shortcut: Ctrl/Cmd + Enter to submit
  captureText.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      if (!submitCapture.disabled) {
        submitCaptureToBackend();
      }
    }
  });

  // Target toggle buttons (Story 38.2 - AC #4)
  // Click handlers
  targetMeetingBtn.addEventListener('click', () => {
    targetMode = 'meeting';
    updateTargetUI();
  });

  targetPersonBtn.addEventListener('click', () => {
    targetMode = 'person';
    updateTargetUI();
  });

  // Keyboard handlers for accessibility (Space/Enter to toggle)
  targetMeetingBtn.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      targetMode = 'meeting';
      updateTargetUI();
    }
  });

  targetPersonBtn.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      targetMode = 'person';
      updateTargetUI();
    }
  });

  // Save settings when capture type changes
  captureType.addEventListener('change', () => {
    saveLastUsedSettings();
  });

  // Story 38.3: Save source URL preference when checkbox changes (Task 4.2)
  if (includeSourceUrlCheckbox) {
    includeSourceUrlCheckbox.addEventListener('change', saveSourceUrlPreference);
  }

  // Story 38.5: Load recent captures on popup open
  loadRecentCaptures();
}

// =============================================================================
// Story 38.5: Recent Captures Management
// =============================================================================

/**
 * Notify service worker of successful capture (Story 38.5 - Task 1.5)
 */
function notifyCaptureSubmitted(capture) {
  chrome.runtime.sendMessage({
    type: 'CAPTURE_SUBMITTED',
    capture: capture,
  }).catch((error) => {
    // Service worker may not be ready, that's OK
    console.warn('Failed to notify service worker:', error.message);
  });
}

/**
 * Load and display recent captures (Story 38.5 - Task 3.1)
 */
async function loadRecentCaptures() {
  const recentCapturesContainer = document.getElementById('recent-captures');
  const recentCapturesList = document.getElementById('recent-captures-list');

  if (!recentCapturesContainer || !recentCapturesList) return;

  try {
    const data = await chrome.storage.local.get(['recentCaptures', 'captureDate']);
    const today = new Date().toISOString().split('T')[0];

    // Only show captures from today
    let captures = data.recentCaptures || [];
    if (data.captureDate !== today) {
      captures = [];
    }

    if (captures.length === 0) {
      recentCapturesContainer.classList.add('hidden');
      return;
    }

    // Clear existing items (use loop instead of innerHTML for consistency)
    while (recentCapturesList.firstChild) {
      recentCapturesList.removeChild(recentCapturesList.firstChild);
    }

    // Render each capture
    captures.forEach((capture) => {
      const item = createRecentCaptureItem(capture);
      recentCapturesList.appendChild(item);
    });

    recentCapturesContainer.classList.remove('hidden');
  } catch (error) {
    console.warn('Failed to load recent captures:', error.message);
    recentCapturesContainer?.classList.add('hidden');
  }
}

/**
 * Create a recent capture list item (Story 38.5 - Task 3.2, 3.3, 3.4)
 */
function createRecentCaptureItem(capture) {
  const item = document.createElement('div');
  item.className = 'recent-capture-item';

  // Get icon for capture type
  const typeIcons = {
    notes: '📝',
    transcript: '🎙️',
    decision: '✅',
    'follow-up': '📌',
    reflection: '💭',
    observation: '👁️',
    symptom: '🩺',
    mood: '😊',
    medication: '💊',
    intake: '📋',
  };
  const icon = typeIcons[capture.capture_type] || '📝';

  // Format relative time
  const relativeTime = formatRelativeTime(capture.timestamp);

  // Create header row
  const header = document.createElement('div');
  header.className = 'recent-capture-header';

  const typeSpan = document.createElement('span');
  typeSpan.className = 'capture-type-icon';
  typeSpan.textContent = icon;
  typeSpan.setAttribute('aria-label', capture.capture_type);

  const infoSpan = document.createElement('span');
  infoSpan.className = 'capture-info';
  // Use textContent for XSS safety
  const typeName = capture.capture_type.charAt(0).toUpperCase() + capture.capture_type.slice(1);
  infoSpan.textContent = `${typeName} • ${capture.target_name} • ${relativeTime}`;

  header.appendChild(typeSpan);
  header.appendChild(infoSpan);

  // Create preview row
  const preview = document.createElement('div');
  preview.className = 'capture-preview';
  // Truncate preview to 50 chars
  let previewText = capture.text_preview || '';
  if (previewText.length > 50) {
    previewText = previewText.substring(0, 47) + '...';
  }
  preview.textContent = previewText;

  item.appendChild(header);
  item.appendChild(preview);

  return item;
}

/**
 * Format timestamp as relative time (Story 38.5 - Task 3.4)
 */
function formatRelativeTime(timestamp) {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diff = now - then;

  // Handle future timestamps (clock skew) or invalid dates
  if (isNaN(then) || diff < 0) {
    return 'just now';
  }

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return 'yesterday';
}
