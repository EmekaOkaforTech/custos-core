/**
 * Custos Quick Capture - Options Script
 * Story 38.1: Browser Extension Scaffold
 * Story 38.4: Keyboard Shortcut Activation
 */

// DOM Elements
const form = document.getElementById('settings-form');
const custosUrlInput = document.getElementById('custos-url');
const apiKeyInput = document.getElementById('api-key');
const testConnectionBtn = document.getElementById('test-connection');
const statusMessage = document.getElementById('status-message');

// Story 38.4 elements
const shortcutDisplay = document.getElementById('shortcut-display');
const openShortcutsLink = document.getElementById('open-shortcuts');

// Initialize options page
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadShortcutInfo();
  setupShortcutLink();
});

/**
 * Load saved settings
 */
function loadSettings() {
  chrome.storage.sync.get(['custosUrl', 'custosApiKey'], (result) => {
    if (chrome.runtime.lastError) {
      console.warn('Failed to load settings:', chrome.runtime.lastError.message);
      return;
    }
    if (result.custosUrl) {
      custosUrlInput.value = result.custosUrl;
    }
    if (result.custosApiKey) {
      apiKeyInput.value = result.custosApiKey;
    }
  });
}

/**
 * Save settings
 */
function saveSettings(event) {
  event.preventDefault();

  const custosUrl = custosUrlInput.value.trim().replace(/\/+$/, ''); // Remove trailing slashes
  const custosApiKey = apiKeyInput.value.trim();

  if (!custosUrl) {
    showStatus('error', 'Please enter a valid Custos URL');
    return;
  }

  // Validate URL format
  try {
    new URL(custosUrl);
  } catch {
    showStatus('error', 'Please enter a valid URL (e.g., http://localhost:8000)');
    return;
  }

  chrome.storage.sync.set(
    {
      custosUrl,
      custosApiKey,
    },
    () => {
      showStatus('success', 'Settings saved successfully!');
    }
  );
}

/**
 * Test connection to backend
 */
async function testConnection() {
  const url = custosUrlInput.value.trim().replace(/\/+$/, '');
  const apiKey = apiKeyInput.value.trim();

  if (!url) {
    showStatus('error', 'Please enter a Custos URL first');
    return;
  }

  // Validate URL
  try {
    new URL(url);
  } catch {
    showStatus('error', 'Please enter a valid URL');
    return;
  }

  testConnectionBtn.disabled = true;
  testConnectionBtn.textContent = 'Testing...';
  showStatus('info', 'Testing connection...');

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
      showStatus('success', `Connected! Backend status: ${data.status || 'ok'}`);
    } else if (response.status === 401) {
      showStatus('error', 'Authentication failed. Check your API key.');
    } else if (response.status === 404) {
      showStatus('error', 'Health endpoint not found. Is this a Custos backend?');
    } else {
      showStatus('error', `Backend returned error: ${response.status}`);
    }
  } catch (error) {
    if (error.message.includes('Failed to fetch')) {
      showStatus(
        'error',
        'Cannot connect to backend. Check the URL and ensure Custos is running.'
      );
    } else {
      showStatus('error', `Connection error: ${error.message}`);
    }
  } finally {
    testConnectionBtn.disabled = false;
    testConnectionBtn.textContent = 'Test Connection';
  }
}

/**
 * Show status message
 * Note: Uses textContent to prevent XSS (consistent with Story 38-2 patterns)
 */
function showStatus(type, message) {
  statusMessage.className = `status-message ${type}`;

  const icons = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
  };

  // Clear existing content safely
  statusMessage.innerHTML = '';

  // Create icon element
  const iconSpan = document.createElement('span');
  iconSpan.className = 'status-icon';
  iconSpan.textContent = icons[type] || '';

  // Create text element (use textContent for XSS protection)
  const textSpan = document.createElement('span');
  textSpan.className = 'status-text';
  textSpan.textContent = message;

  statusMessage.appendChild(iconSpan);
  statusMessage.appendChild(textSpan);
}

// Event listeners
form.addEventListener('submit', saveSettings);
testConnectionBtn.addEventListener('click', testConnection);

// =============================================================================
// Story 38.4: Keyboard Shortcut Support
// =============================================================================

/**
 * Load and display current keyboard shortcut (Story 38.4 - Task 3.3)
 */
async function loadShortcutInfo() {
  if (!shortcutDisplay) return;

  try {
    // chrome.commands.getAll() returns all registered commands
    const commands = await chrome.commands.getAll();
    const captureCommand = commands.find(cmd => cmd.name === '_execute_action');

    if (captureCommand && captureCommand.shortcut) {
      // Display the actual configured shortcut
      shortcutDisplay.textContent = captureCommand.shortcut;
    } else {
      // No shortcut configured - show default or "not set"
      shortcutDisplay.textContent = 'Not configured';
      const helpText = document.getElementById('shortcut-help');
      if (helpText) {
        helpText.textContent = 'No keyboard shortcut is currently set. Click below to configure one.';
      }
    }
  } catch (error) {
    console.warn('Failed to load shortcut info:', error.message);
    // Fallback to showing default
    shortcutDisplay.textContent = 'Ctrl+Shift+C';
  }
}

/**
 * Setup link to open browser's keyboard shortcuts settings (Story 38.4 - Task 3.2)
 */
function setupShortcutLink() {
  if (!openShortcutsLink) return;

  openShortcutsLink.addEventListener('click', (e) => {
    e.preventDefault();

    // Open the browser's extension keyboard shortcuts page
    // Chrome: chrome://extensions/shortcuts
    // Firefox: about:addons → Extensions → Manage Extension Shortcuts
    const isFirefox = typeof browser !== 'undefined';

    if (isFirefox) {
      // Firefox doesn't support opening about: pages directly
      // Show inline instructions instead of alert (better UX)
      showFirefoxShortcutInstructions();
    } else {
      // Chrome/Edge - open the shortcuts page
      chrome.tabs.create({ url: 'chrome://extensions/shortcuts' });
    }
  });
}

/**
 * Show Firefox shortcut instructions inline (better UX than alert)
 */
function showFirefoxShortcutInstructions() {
  const helpText = document.getElementById('shortcut-help');
  if (!helpText) return;

  helpText.innerHTML = '';

  const instructions = document.createElement('div');
  instructions.className = 'firefox-instructions';
  instructions.innerHTML = `
    <p><strong>To change the keyboard shortcut in Firefox:</strong></p>
    <ol>
      <li>Go to <code>about:addons</code></li>
      <li>Click the gear icon (⚙)</li>
      <li>Select "Manage Extension Shortcuts"</li>
    </ol>
  `;
  helpText.appendChild(instructions);
}
