import {
  apiUrl,
  formatDate,
  getApiBase,
  getApiHeaders,
  getBriefingMode,
  getCalendarConsent,
  getCareMode,
  getDemoMode,
  getProfessionalMode,
  getStoredApiKey,
  isSetupComplete,
  isSeedIdentifier,
  setBriefingMode,
  setCalendarConsent,
  setCareMode,
  setDemoMode,
  setProfessionalMode,
} from './ui-state.js';
import { initCapture } from './capture.js';

const statusHealth = document.getElementById('status-health');
const statusBanner = document.getElementById('status-banner');
const statusToggle = document.getElementById('status-toggle');
const statusDetails = document.getElementById('status-details');
const statusSummary = document.getElementById('status-summary-text');
const statusDb = document.getElementById('status-db');
const statusIngestion = document.getElementById('status-ingestion');
const statusBackup = document.getElementById('status-backup');
const statusRestore = document.getElementById('status-restore');
const statusStorage = document.getElementById('status-storage');
const statusRecovery = document.getElementById('status-recovery');
const statusErrors = document.getElementById('status-errors');
const acceleratorStatus = document.getElementById('accelerator-status');
const acceleratorDetail = document.getElementById('accelerator-detail');
const networkSettingsForm = document.getElementById("network-settings-form");
const networkDiscoveryEnabled = document.getElementById("network-discovery-enabled");
const networkScanInterval = document.getElementById("network-scan-interval");
const networkManualServices = document.getElementById("network-manual-services");
const networkAddService = document.getElementById("network-add-service");
const networkScanNow = document.getElementById("network-scan-now");
const networkSettingsStatus = document.getElementById("network-settings-status");
const networkSettingsSummary = document.getElementById("network-settings-summary");
const summarizationForm = document.getElementById("summarization-form");
const summarizationEnabled = document.getElementById("summarization-enabled");
const summarizationProvider = document.getElementById("summarization-provider");
const summarizationModel = document.getElementById("summarization-model");
const summarizationMaxTokens = document.getElementById("summarization-max-tokens");
const summarizationStatus = document.getElementById("summarization-status");
const emailForm = document.getElementById("email-form");
const emailStatus = document.getElementById("email-status");
const emailHost = document.getElementById("email-host");
const emailPort = document.getElementById("email-port");
const emailUsername = document.getElementById("email-username");
const emailPassword = document.getElementById("email-password");
const emailUseTls = document.getElementById("email-use-tls");
const emailInterval = document.getElementById("email-interval");
const emailEnabled = document.getElementById("email-enabled");
const emailTest = document.getElementById("email-test");
const emailPoll = document.getElementById("email-poll");
const emailMessage = document.getElementById("email-message");
const chatSlackForm = document.getElementById("chat-slack-form");
const chatSlackSecret = document.getElementById("chat-slack-secret");
const chatSlackEnabled = document.getElementById("chat-slack-enabled");
const chatSlackStatus = document.getElementById("chat-slack-status");
const chatSlackUrl = document.getElementById("chat-slack-url");
const chatTeamsForm = document.getElementById("chat-teams-form");
const chatTeamsSecret = document.getElementById("chat-teams-secret");
const chatTeamsEnabled = document.getElementById("chat-teams-enabled");
const chatTeamsStatus = document.getElementById("chat-teams-status");
const chatTeamsUrl = document.getElementById("chat-teams-url");
const chatDiscordForm = document.getElementById("chat-discord-form");
const chatDiscordSecret = document.getElementById("chat-discord-secret");
const chatDiscordEnabled = document.getElementById("chat-discord-enabled");
const chatDiscordStatus = document.getElementById("chat-discord-status");
const chatDiscordUrl = document.getElementById("chat-discord-url");

const backupAction = document.getElementById('backup-action');
const apiKeyForm = document.getElementById('api-key-form');
const apiKeyInput = document.getElementById('api-key-input');
const apiKeyClear = document.getElementById('api-key-clear');
const apiKeyStatus = document.getElementById('api-key-status');
const demoBadge = document.getElementById('demo-badge');
const demoResetCard = document.getElementById('demo-reset-card');
const demoResetButton = document.getElementById('demo-reset');
const demoResetStatus = document.getElementById('demo-reset-status');
const calendarCard = document.getElementById('calendar-card');
const calendarStatus = document.getElementById('calendar-status');
const calendarConnect = document.getElementById('calendar-connect');
const calendarImport = document.getElementById('calendar-import');
const calendarImportStatus = document.getElementById('calendar-import-status');
const calendarModal = document.getElementById('calendar-modal');
const calendarClose = document.getElementById('calendar-close');
const calendarForm = document.getElementById('calendar-form');
const calendarStatusText = document.getElementById('calendar-current-status');
const calendarConsent = document.getElementById('calendar-consent');
const calendarConsentError = document.getElementById('calendar-consent-error');
const calendarCompleteStatus = document.getElementById('calendar-complete-status');
const calendarProviderError = document.getElementById('calendar-provider-error');
const calendarAuthStatus = document.getElementById('calendar-auth-status');
const providerGoogle = document.getElementById('provider-google');
const providerMicrosoft = document.getElementById('provider-microsoft');
const providerDemo = document.getElementById('provider-demo');
const googleStatus = document.getElementById('google-status');
const microsoftStatus = document.getElementById('microsoft-status');
const closureSection = document.getElementById('closure-section');
const closureCards = document.getElementById('closure-cards');
const closureGroupMeeting = document.getElementById('closure-group-meeting');
const closureGroupPerson = document.getElementById('closure-group-person');
const threadsSection = document.getElementById('threads-section');
const threadsCards = document.getElementById('threads-cards');
const decisionSection = document.getElementById('decision-section');
const decisionCards = document.getElementById('decision-cards');
const contextGapsSection = document.getElementById('context-gaps-section');
const contextGapsCards = document.getElementById('context-gaps-cards');
const relationshipSignalsSection = document.getElementById('relationship-signals-section');
const relationshipSignalsCards = document.getElementById('relationship-signals-cards');

let closureGroup = 'meeting';

function formatBytes(value) {
  if (value === null || value === undefined) return 'unknown';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = Number(value);
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(1)} ${units[idx]}`;
}

function setBanner(kind, message) {
  if (!message) {
    statusBanner.style.display = 'none';
    statusBanner.textContent = '';
    return;
  }
  statusBanner.style.display = 'block';
  statusBanner.dataset.kind = kind;
  statusBanner.textContent = message;
}

function updateApiKeyStatus() {
  const stored = getStoredApiKey();
  if (stored) {
    apiKeyStatus.textContent = 'API key stored in this browser.';
  } else {
    apiKeyStatus.textContent = 'No API key stored in browser.';
  }
}

function setDemoBadge(show) {
  if (!demoBadge) return;
  demoBadge.classList.toggle('hidden', !show);
}

function setDemoResetVisibility(show) {
  if (!demoResetCard) return;
  demoResetCard.classList.toggle('hidden', !show);
}

function setCalendarModalOpen(open) {
  if (!calendarModal) return;
  calendarModal.classList.toggle('open', open);
  calendarModal.setAttribute('aria-hidden', open ? 'false' : 'true');
}

function setWizardStep(step) {
  if (!calendarForm) return;
  calendarForm.querySelectorAll('.wizard-step').forEach(node => {
    node.classList.toggle('hidden', node.dataset.step !== String(step));
  });
  if (calendarConsentError) {
    calendarConsentError.textContent = '';
  }
}

function updateCalendarStatus(statusData, connectionData) {
  if (!calendarStatus) return;
  const calendar = statusData?.calendar_status || {};
  const enabled = Boolean(calendar.enabled);
  const provider = calendar.provider || connectionData?.provider || null;

  // Use connection data for sync info if available (Story 37.2)
  const lastSyncAt = connectionData?.last_sync_at;
  const syncError = connectionData?.sync_error;
  const lastSuccess = lastSyncAt ? formatDate(lastSyncAt) : (calendar.last_success ? formatDate(calendar.last_success) : null);

  if (enabled && provider) {
    const providerName = provider === 'google' ? 'Google Calendar' :
                        provider === 'microsoft' ? 'Microsoft Outlook' :
                        provider === 'demo' ? 'Demo Calendar' : provider;

    // Build status text with sync info
    let statusText = `${providerName} connected`;
    if (syncError) {
      statusText += ` · Sync error: ${syncError}`;
    } else if (lastSuccess) {
      statusText += ` · Last sync ${lastSuccess}`;
    } else {
      statusText += ' · No recent sync';
    }
    calendarStatus.textContent = statusText;

    if (calendarConnect) {
      calendarConnect.textContent = 'Disconnect calendar';
    }
  } else {
    calendarStatus.textContent = 'Calendar not connected yet.';
    if (calendarConnect) {
      calendarConnect.textContent = 'Connect calendar (read-only)';
    }
  }

  if (calendarImport) {
    calendarImport.disabled = !enabled;
    // Update button text based on state
    if (syncError && enabled) {
      calendarImport.textContent = 'Retry sync';
    } else {
      calendarImport.textContent = 'Sync now';
    }
  }
  if (calendarStatusText) {
    let statusDetail = 'Current status: not connected';
    if (enabled) {
      statusDetail = `Current status: ${provider || 'connected'}`;
      if (syncError) {
        statusDetail += ` (error: ${syncError})`;
      } else if (lastSuccess) {
        statusDetail += ` (last sync ${lastSuccess})`;
      }
    }
    calendarStatusText.textContent = statusDetail;
  }
}

// OAuth provider status tracking
let oauthStatus = { google_configured: false, microsoft_configured: false };
let oauthPopup = null;

async function checkOAuthStatus() {
  try {
    const response = await fetch(apiUrl('/api/calendar/oauth/status'), { headers: getApiHeaders() });
    if (response.ok) {
      oauthStatus = await response.json();
    }
  } catch (err) {
    // Silently fail - OAuth may not be configured
  }
  updateProviderButtons();
}

function updateProviderButtons() {
  if (googleStatus) {
    if (oauthStatus.google_configured) {
      googleStatus.textContent = 'Available';
      googleStatus.classList.add('available');
      googleStatus.classList.remove('unavailable');
      if (providerGoogle) providerGoogle.disabled = false;
    } else {
      googleStatus.textContent = 'Not configured';
      googleStatus.classList.add('unavailable');
      googleStatus.classList.remove('available');
      if (providerGoogle) providerGoogle.disabled = true;
    }
  }
  if (microsoftStatus) {
    if (oauthStatus.microsoft_configured) {
      microsoftStatus.textContent = 'Available';
      microsoftStatus.classList.add('available');
      microsoftStatus.classList.remove('unavailable');
      if (providerMicrosoft) providerMicrosoft.disabled = false;
    } else {
      microsoftStatus.textContent = 'Not configured';
      microsoftStatus.classList.add('unavailable');
      microsoftStatus.classList.remove('available');
      if (providerMicrosoft) providerMicrosoft.disabled = true;
    }
  }
}

async function startOAuthFlow(provider) {
  if (calendarAuthStatus) {
    calendarAuthStatus.textContent = `Connecting to ${provider}...`;
  }
  setWizardStep(4);

  try {
    const response = await fetch(apiUrl(`/api/calendar/oauth/authorize?provider=${encodeURIComponent(provider)}`), {
      method: 'GET',
      headers: { ...getApiHeaders(), "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const data = await response.json();
      if (calendarProviderError) {
        calendarProviderError.textContent = data.detail || 'Failed to start authorization';
      }
      setWizardStep(3);
      return;
    }

    const data = await response.json();
    if (calendarAuthStatus) {
      calendarAuthStatus.textContent = 'Opening authorization window...';
    }

    // Open OAuth popup
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    oauthPopup = window.open(
      data.authorization_url,
      'custos_oauth',
      `width=${width},height=${height},left=${left},top=${top},popup=yes`
    );

    if (!oauthPopup) {
      if (calendarProviderError) {
        calendarProviderError.textContent = 'Popup was blocked. Please allow popups for this site.';
      }
      setWizardStep(3);
    }
  } catch (err) {
    if (calendarProviderError) {
      calendarProviderError.textContent = 'Network error. Please try again.';
    }
    setWizardStep(3);
  }
}

async function connectDemoCalendar() {
  try {
    const response = await fetch(apiUrl('/api/calendar/connection'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
      body: JSON.stringify({
        provider: 'demo',
        scopes: ['read'],
        token: 'demo-token',
        enabled: true,
      }),
    });

    if (response.ok) {
      if (calendarCompleteStatus) {
        calendarCompleteStatus.textContent = 'Demo calendar connected.';
      }
      setWizardStep(5);
      loadStatus();
    } else {
      const data = await response.json();
      if (calendarProviderError) {
        calendarProviderError.textContent = data.detail || 'Failed to connect demo calendar';
      }
    }
  } catch (err) {
    if (calendarProviderError) {
      calendarProviderError.textContent = 'Network error. Please try again.';
    }
  }
}

async function disconnectCalendar() {
  try {
    const response = await fetch(apiUrl('/api/calendar/connection'), {
      method: 'DELETE',
      headers: { ...getApiHeaders(), "Content-Type": "application/json" },
    });

    if (response.ok) {
      if (calendarStatus) {
        calendarStatus.textContent = 'Calendar disconnected.';
      }
      loadStatus();
    }
  } catch (err) {
    // Silently fail
  }
}

// Listen for OAuth callback messages
window.addEventListener('message', (event) => {
  if (event.origin !== window.location.origin) return;

  if (event.data?.type === 'oauth-success') {
    if (calendarCompleteStatus) {
      calendarCompleteStatus.textContent = `${event.data.provider} calendar connected successfully!`;
    }
    setWizardStep(5);
    loadStatus();
    if (oauthPopup) {
      oauthPopup.close();
      oauthPopup = null;
    }
  } else if (event.data?.type === 'oauth-error') {
    if (calendarProviderError) {
      calendarProviderError.textContent = event.data.error || 'Authorization failed';
    }
    setWizardStep(3);
    if (oauthPopup) {
      oauthPopup.close();
      oauthPopup = null;
    }
  }
});

function statusLabelForCommitment(item) {
  if (item.needs_attention) {
    return 'Needs attention';
  }
  return item.acknowledged ? 'Completed' : 'Still pending';
}

function renderClosure(items) {
  if (!closureCards) return;
  closureCards.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    closureCards.innerHTML = '<div class="card"><p class="muted">No commitments to close out.</p></div>';
    return;
  }

  const groups = new Map();
  items.forEach(item => {
    if (closureGroup === 'person') {
      const people = item.people?.length ? item.people : [{ id: 'none', name: 'Unassigned', type: 'person' }];
      people.forEach(person => {
        const key = `person:${person.id}`;
        if (!groups.has(key)) {
          groups.set(key, { title: person.name, items: [] });
        }
        groups.get(key).items.push(item);
      });
    } else {
      const meetingTitle = item.meeting?.title || 'Meeting';
      const key = `meeting:${item.meeting?.id || meetingTitle}`;
      if (!groups.has(key)) {
        groups.set(key, { title: meetingTitle, items: [] });
      }
      groups.get(key).items.push(item);
    }
  });

  groups.forEach(group => {
    const section = document.createElement('div');
    section.className = 'card';
    const title = document.createElement('h4');
    title.textContent = group.title;
    section.appendChild(title);
    group.items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'commitment-row';
      const text = document.createElement('div');
      text.textContent = item.text;
      const relevant = document.createElement('span');
      relevant.className = 'muted';
      relevant.textContent = item.due_at ? `Relevant by ${formatDate(item.due_at)}` : 'No time intent set';
      const status = document.createElement('span');
      status.className = 'status-pill';
      status.dataset.state = item.needs_attention ? 'attention' : (item.acknowledged ? 'ok' : 'missing');
      status.textContent = statusLabelForCommitment(item);
      const editButton = document.createElement('button');
      editButton.className = 'button-link';
      editButton.type = 'button';
      editButton.textContent = 'Relevant by';
      const contextButton = document.createElement('button');
      contextButton.className = 'button-link';
      contextButton.type = 'button';
      contextButton.textContent = 'View context';
      const context = document.createElement('div');
      context.className = 'status-details hidden';
      const meetingLine = document.createElement('p');
      meetingLine.className = 'muted';
      meetingLine.textContent = `${item.meeting?.title || 'Meeting'} · ${formatDate(item.meeting?.starts_at) || 'time unknown'}`;
      const captureLine = document.createElement('p');
      captureLine.className = 'muted';
      const captureType = item.source?.capture_type || 'context';
      captureLine.textContent = `Captured via ${captureType}.`;
      const excerpt = document.createElement('p');
      excerpt.textContent = item.source?.excerpt || 'No capture excerpt available.';
      context.appendChild(meetingLine);
      context.appendChild(captureLine);
      context.appendChild(excerpt);
      contextButton.addEventListener('click', () => {
        const isHidden = context.classList.contains('hidden');
        context.classList.toggle('hidden', !isHidden);
        contextButton.textContent = isHidden ? 'Hide context' : 'View context';
      });
      const button = document.createElement('button');
      button.className = 'button-link';
      button.type = 'button';
      button.textContent = item.acknowledged ? 'Mark still pending' : 'Mark completed';
      button.addEventListener('click', async () => {
        const response = await fetch(apiUrl(`/api/commitments/${item.id}/ack`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
          body: JSON.stringify({ acknowledged: !item.acknowledged }),
        });
        if (response.ok) {
          item.acknowledged = !item.acknowledged;
          item.needs_attention = Boolean(item.due_at && new Date(item.due_at) < new Date() && !item.acknowledged);
          renderClosure(items);
        }
      });
      row.appendChild(text);
      row.appendChild(relevant);
      row.appendChild(editButton);
      row.appendChild(status);
      row.appendChild(contextButton);
      row.appendChild(button);
      section.appendChild(row);
      section.appendChild(context);

      const editRow = document.createElement('div');
      editRow.className = 'status-details hidden';
      const editInput = document.createElement('input');
      editInput.type = 'date';
      editInput.value = item.due_at ? item.due_at.slice(0, 10) : '';
      const editSave = document.createElement('button');
      editSave.className = 'button-link';
      editSave.type = 'button';
      editSave.textContent = 'Save';
      const editStatus = document.createElement('span');
      editStatus.className = 'muted';
      editStatus.textContent = '';
      editSave.addEventListener('click', async () => {
        const value = editInput.value ? new Date(`${editInput.value}T09:00:00`).toISOString() : null;
        const response = await fetch(apiUrl(`/api/commitments/${item.id}`), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
          body: JSON.stringify({ relevant_by: value }),
        });
        if (response.ok) {
          item.due_at = value;
          relevant.textContent = item.due_at ? `Relevant by ${formatDate(item.due_at)}` : 'No time intent set';
          editStatus.textContent = 'Saved.';
        } else {
          editStatus.textContent = 'Unable to save.';
        }
      });
      editButton.addEventListener('click', () => {
        editRow.classList.toggle('hidden');
      });
      editRow.appendChild(editInput);
      editRow.appendChild(editSave);
      editRow.appendChild(editStatus);
      section.appendChild(editRow);
    });
    closureCards.appendChild(section);
  });
}

async function loadClosure() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  const response = await fetch(apiUrl('/api/commitments/closure'), { headers: getApiHeaders() });
  if (!response.ok) {
    if (closureCards) {
      closureCards.innerHTML = '<div class="card"><p class="muted">Unable to load commitment closure.</p></div>';
    }
    return;
  }
  const data = await response.json();
  renderClosure(data.items || []);
}

function renderThreads(threads) {
  if (!threadsCards) return;
  threadsCards.innerHTML = '';
  if (!Array.isArray(threads) || !threads.length) {
    threadsCards.innerHTML = '<div class="card"><p class="muted">No unresolved threads right now.</p></div>';
    return;
  }
  threads.forEach(thread => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = document.createElement('h4');
    title.textContent = thread.meeting?.title || 'Context';
    const meta = document.createElement('p');
    meta.className = 'muted';
    meta.textContent = thread.meeting?.starts_at
      ? `Last updated ${formatDate(thread.meeting.starts_at)}`
      : 'Last updated unknown';
    const commitments = document.createElement('div');
    commitments.className = 'status-details';
    thread.commitments?.forEach(item => {
      const row = document.createElement('p');
      row.textContent = item.text;
      commitments.appendChild(row);
    });
    const viewSource = document.createElement('button');
    viewSource.className = 'button-link';
    viewSource.type = 'button';
    viewSource.textContent = 'View source';
    const sourceBlock = document.createElement('div');
    sourceBlock.className = 'status-details hidden';
    const excerpts = Array.isArray(thread.excerpts) ? thread.excerpts : [];
    if (excerpts.length) {
      const first = excerpts[0];
      const row = document.createElement('p');
      row.className = 'muted';
      row.textContent = first.excerpt || 'No capture excerpt available.';
      sourceBlock.appendChild(row);
    } else {
      const row = document.createElement('p');
      row.className = 'muted';
      row.textContent = 'No capture excerpt available.';
      sourceBlock.appendChild(row);
    }
    viewSource.addEventListener('click', () => {
      const isHidden = sourceBlock.classList.contains('hidden');
      sourceBlock.classList.toggle('hidden', !isHidden);
      viewSource.textContent = isHidden ? 'Hide source' : 'View source';
    });
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(commitments);
    card.appendChild(viewSource);
    card.appendChild(sourceBlock);
    threadsCards.appendChild(card);
  });
}

async function loadThreads() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  const response = await fetch(apiUrl('/api/commitments/threads'), { headers: getApiHeaders() });
  if (!response.ok) {
    if (threadsCards) {
      threadsCards.innerHTML = '<div class="card"><p class="muted">Unable to load unresolved threads.</p></div>';
    }
    return;
  }
  const data = await response.json();
  renderThreads(data.threads || []);
}

function renderDecisions(items) {
  if (!decisionCards) return;
  decisionCards.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    decisionCards.innerHTML = '<div class="card"><p class="muted">No decisions captured yet.</p></div>';
    return;
  }
  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = document.createElement('h4');
    title.textContent = item.meeting?.title || 'Context';
    const meta = document.createElement('p');
    meta.className = 'muted';
    meta.textContent = item.captured_at ? `Captured ${formatDate(item.captured_at)}` : 'Captured time unknown';
    const excerpt = document.createElement('p');
    const text = item.payload?.trim() || 'No capture excerpt available.';
    excerpt.textContent = text.length > 160 ? `${text.slice(0, 157)}…` : text;
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(excerpt);
    decisionCards.appendChild(card);
  });
}

async function loadDecisionSurfaces() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  const response = await fetch(apiUrl('/api/ingestion/recent?limit=20'), { headers: getApiHeaders() });
  if (!response.ok) {
    if (decisionCards) {
      decisionCards.innerHTML = '<div class="card"><p class="muted">Unable to load decision surfaces.</p></div>';
    }
    return;
  }
  const data = await response.json();
  const decisions = Array.isArray(data) ? data.filter(item => item.capture_type === 'decision') : [];
  renderDecisions(decisions);
}

function renderGaps(data) {
  if (!contextGapsCards) return;
  contextGapsCards.innerHTML = '';
  const meetings = Array.isArray(data?.meetings) ? data.meetings : [];
  const people = Array.isArray(data?.people) ? data.people : [];
  if (!meetings.length && !people.length) {
    contextGapsCards.innerHTML = '<div class="card"><p class="muted">No context gaps to show.</p></div>';
    return;
  }
  if (meetings.length) {
    const section = document.createElement('div');
    section.className = 'card';
    const title = document.createElement('h4');
    title.textContent = 'Contexts';
    section.appendChild(title);
    meetings.forEach(item => {
      const row = document.createElement('p');
      row.className = 'muted';
      if (item.last_updated) {
        row.textContent = `${item.title} · Last updated ${formatDate(item.last_updated)} · ${item.days_since} days since`;
      } else {
        row.textContent = `${item.title} · No recent context recorded.`;
      }
      section.appendChild(row);
    });
    contextGapsCards.appendChild(section);
  }
  if (people.length) {
    const section = document.createElement('div');
    section.className = 'card';
    const title = document.createElement('h4');
    title.textContent = 'People';
    section.appendChild(title);
    people.forEach(item => {
      const row = document.createElement('p');
      row.className = 'muted';
      if (item.last_updated) {
        row.textContent = `${item.name} · Last updated ${formatDate(item.last_updated)} · ${item.days_since} days since`;
      } else {
        row.textContent = `${item.name} · No recent context recorded.`;
      }
      section.appendChild(row);
    });
    contextGapsCards.appendChild(section);
  }
}

async function loadContextGaps() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  const response = await fetch(apiUrl('/api/status/context-gaps'), { headers: getApiHeaders() });
  if (!response.ok) {
    if (contextGapsCards) {
      contextGapsCards.innerHTML = '<div class="card"><p class="muted">Unable to load context gaps.</p></div>';
    }
    return;
  }
  const data = await response.json();
  renderGaps(data);
}

function presenceLabel(item) {
  if (item.days_since === null || item.days_since === undefined) {
    return 'No recent context';
  }
  if (item.days_since <= 7) {
    return 'Recently present';
  }
  return 'Quiet';
}

function renderRelationshipSignals(data) {
  if (!relationshipSignalsCards) return;
  relationshipSignalsCards.innerHTML = '';
  const items = Array.isArray(data?.items) ? data.items : [];
  if (!items.length) {
    relationshipSignalsCards.innerHTML = '<div class="card"><p class="muted">No relationship signals to show.</p></div>';
    return;
  }
  const card = document.createElement('div');
  card.className = 'card';
  items.forEach(item => {
    const row = document.createElement('p');
    row.className = 'muted';
    const last = item.last_updated ? formatDate(item.last_updated) : 'unknown';
    const since = item.days_since === null || item.days_since === undefined ? 'unknown' : `${item.days_since} days since`;
    row.textContent = `${item.name} · ${presenceLabel(item)} · Last updated ${last} · ${since} · ${item.recent_context_count} context notes (30d)`;
    card.appendChild(row);
  });
  relationshipSignalsCards.appendChild(card);
}

async function loadRelationshipSignals() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  const response = await fetch(apiUrl('/api/status/relationship-signals'), { headers: getApiHeaders() });
  if (!response.ok) {
    if (relationshipSignalsCards) {
      relationshipSignalsCards.innerHTML = '<div class="card"><p class="muted">Unable to load relationship signals.</p></div>';
    }
    return;
  }
  const data = await response.json();
  renderRelationshipSignals(data);
}

async function refreshDemoMode() {
  if (!getApiBase() || !isSetupComplete()) {
    return;
  }
  if (getDemoMode()) {
    setDemoBadge(true);
    setDemoResetVisibility(true);
    return;
  }
  try {
    const response = await fetch(apiUrl('/api/people'), { headers: getApiHeaders() });
    if (!response.ok) return;
    const data = await response.json();
    const hasSeed = Array.isArray(data) && data.some(person => isSeedIdentifier(person.id));
    setDemoMode(hasSeed);
    setDemoBadge(hasSeed);
    setDemoResetVisibility(hasSeed);
  } catch (err) {
    // ignore
  }
}

statusToggle.addEventListener('click', () => {
  const next = statusDetails.classList.contains('hidden');
  statusDetails.classList.toggle('hidden', !next);
  statusToggle.textContent = next ? 'Hide details' : 'View details';
  statusToggle.setAttribute('aria-expanded', next ? 'true' : 'false');
});

function updateNasBackupStatus(statusData) {
  if (!nasBackupStatus) return;
  const nas = statusData?.nas_backup_status || {};
  if (!nas.status || nas.status === "unknown") {
    nasBackupStatus.textContent = "NAS backup not configured.";
    return;
  }
  const lastAttempt = formatDate(nas.last_attempt);
  nasBackupStatus.textContent = "NAS backup: " + nas.status + " (last attempt " + lastAttempt + ")";
}

async function loadNasTarget() {
  if (!nasBackupForm) return;
  try {
    const response = await fetch(apiUrl("/api/backup/target"), { headers: getApiHeaders() });
    if (!response.ok) return;
    const data = await response.json();
    if (nasBackupProtocol) nasBackupProtocol.value = data.protocol || "smb";
    if (nasBackupHost) nasBackupHost.value = data.host || "";
    if (nasBackupShare) nasBackupShare.value = data.share || "";
    if (nasBackupMount) nasBackupMount.value = data.mount_path || "";
    if (nasBackupUsername) nasBackupUsername.value = data.username || "";
    if (nasBackupEnabled) nasBackupEnabled.checked = Boolean(data.enabled);
  } catch (err) {
    // ignore
  }
}

function updateInferenceStatus(data) {
  if (!inferenceStatus) return;
  const status = data?.inference_status || "disabled";
  const lastChecked = formatDate(data?.inference_last_checked);
  if (!data?.inference_enabled) {
    inferenceStatus.textContent = "Inference delegation not configured.";
    return;
  }
  inferenceStatus.textContent = "Inference server: " + status + " (last checked " + lastChecked + ")";
}

async function loadInferenceSettings() {
  if (!inferenceForm) return;
  try {
    const response = await fetch(apiUrl("/api/inference/settings"), { headers: getApiHeaders() });
    if (!response.ok) return;
    const data = await response.json();
    if (inferenceUrl) inferenceUrl.value = data.inference_url || "";
    if (inferenceEnabled) inferenceEnabled.checked = Boolean(data.inference_enabled);
    updateInferenceStatus(data);
  } catch (err) {
    // ignore
  }
}

function updateSyncStatus(data) {
  if (!syncStatus) return;
  if (!data?.enabled) {
    syncStatus.textContent = "Home sync not configured.";
    return;
  }
  const lastSync = formatDate(data?.last_sync_at);
  syncStatus.textContent = "Home sync enabled (last sync " + lastSync + ")";
}

async function loadSyncSettings() {
  if (!syncForm) return;
  try {
    const response = await fetch(apiUrl("/api/sync/settings"), { headers: getApiHeaders() });
    if (!response.ok) return;
    const data = await response.json();
    if (syncMount) syncMount.value = data.mount_path || "";
    if (syncEnabled) syncEnabled.checked = Boolean(data.enabled);
    updateSyncStatus(data);
  } catch (err) {
    // ignore
  }
}


function buildManualServiceRow(data = {}) {
  if (!networkManualServices) return null;
  const row = document.createElement("div");
  row.className = "manual-service-row";

  const name = document.createElement("input");
  name.type = "text";
  name.placeholder = "Name";
  name.value = data.name || "";

  const type = document.createElement("select");
  ["nas", "inference", "http", "other"].forEach(optionValue => {
    const opt = document.createElement("option");
    opt.value = optionValue;
    opt.textContent = optionValue;
    if ((data.type || "").toLowerCase() == optionValue) {
      opt.selected = true;
    }
    type.appendChild(opt);
  });

  const protocol = document.createElement("select");
  ["http", "smb", "nfs"].forEach(optionValue => {
    const opt = document.createElement("option");
    opt.value = optionValue;
    opt.textContent = optionValue;
    if ((data.protocol || "").toLowerCase() == optionValue) {
      opt.selected = true;
    }
    protocol.appendChild(opt);
  });

  const host = document.createElement("input");
  host.type = "text";
  host.placeholder = "Host";
  host.value = data.host || "";

  const port = document.createElement("input");
  port.type = "number";
  port.min = "1";
  port.max = "65535";
  port.placeholder = "Port";
  port.value = data.port ? String(data.port) : "";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button-link";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => row.remove());

  row.appendChild(name);
  row.appendChild(type);
  row.appendChild(protocol);
  row.appendChild(host);
  row.appendChild(port);
  row.appendChild(remove);
  networkManualServices.appendChild(row);
  return row;
}

function readManualServices() {
  if (!networkManualServices) return [];
  const rows = Array.from(networkManualServices.querySelectorAll(".manual-service-row"));
  const services = [];
  rows.forEach(row => {
    const inputs = row.querySelectorAll("input, select");
    const name = inputs[0]?.value?.trim() || "";
    const type = inputs[1]?.value || "";
    const protocol = inputs[2]?.value || "";
    const host = inputs[3]?.value?.trim() || "";
    const portValue = inputs[4]?.value ? Number(inputs[4].value) : null;
    if (!host || !portValue) return;
    services.push({
      name: name,
      type: type,
      protocol: protocol,
      host: host,
      port: portValue,
    });
  });
  return services;
}

async function loadNetworkSettings() {
  if (!networkSettingsForm) return;
  try {
    const response = await fetch(apiUrl("/api/network/settings"), { headers: getApiHeaders() });
    if (!response.ok) return;
    const data = await response.json();
    if (networkDiscoveryEnabled) networkDiscoveryEnabled.checked = Boolean(data.discovery_enabled);
    if (networkScanInterval) networkScanInterval.value = data.scan_interval_minutes || 15;
    if (networkSettingsSummary) {
      const lastScan = formatDate(data.last_scan_at);
      networkSettingsSummary.textContent = data.discovery_enabled
        ? "Scanning local services · Last scan " + lastScan
        : "Discovery disabled";
    }
    if (networkManualServices) networkManualServices.innerHTML = "";
    const manual = Array.isArray(data.manual_services) ? data.manual_services : [];
    manual.forEach(item => buildManualServiceRow(item));
  } catch (err) {
    if (networkSettingsSummary) networkSettingsSummary.textContent = "Unable to load network settings.";
  }
}


async function loadSummarizationSettings() {
  if (!summarizationForm) return;
  try {
    const response = await fetch(apiUrl("/api/summarization/settings"), { headers: getApiHeaders() });
    if (!response.ok) {
      if (summarizationStatus) summarizationStatus.textContent = "Unable to load summarization settings.";
      return;
    }
    const data = await response.json();
    if (summarizationEnabled) summarizationEnabled.checked = Boolean(data.enabled);
    if (summarizationProvider && data.provider) summarizationProvider.value = data.provider;
    if (summarizationModel) summarizationModel.value = data.model || "";
    if (summarizationMaxTokens) summarizationMaxTokens.value = data.max_input_tokens || "";
    updateSummarizationStatus(data);
  } catch (err) {
    if (summarizationStatus) summarizationStatus.textContent = "Unable to load summarization settings.";
  }
}

function updateSummarizationStatus(data) {
  if (!summarizationStatus) return;
  if (!data || !data.enabled) {
    summarizationStatus.textContent = "Summaries are off by default.";
    return;
  }
  const providerLabel = data.provider === "home-server" ? "Home server" : "Hailo 8";
  const modelLabel = data.model ? " · Model " + data.model : "";
  const tokenLabel = data.max_input_tokens ? " · Max " + data.max_input_tokens + " tokens" : "";
  summarizationStatus.textContent = "Summaries enabled · " + providerLabel + modelLabel + tokenLabel;
}

function setChatUrl(el, provider) {
  if (!el) return;
  const base = getApiBase();
  el.textContent = base ? `${base}/api/integrations/chat/webhook/${provider}` : "Connect to backend to view";
}

async function loadChatProvider(provider, statusEl, enabledEl, urlEl) {
  if (!statusEl) return;
  setChatUrl(urlEl, provider);
  try {
    const response = await fetch(apiUrl(`/api/integrations/chat/connection/${provider}`), { headers: getApiHeaders() });
    if (!response.ok) {
      statusEl.textContent = `${provider} ingestion unavailable.`;
      return;
    }
    const data = await response.json();
    if (enabledEl) enabledEl.checked = Boolean(data.enabled);
    if (!data.configured) {
      statusEl.textContent = `${provider} ingestion not configured.`;
    } else if (data.enabled) {
      statusEl.textContent = `${provider} ingestion enabled.`;
    } else {
      statusEl.textContent = `${provider} ingestion disabled.`;
    }
  } catch (err) {
    statusEl.textContent = `${provider} ingestion unavailable.`;
  }
}

async function loadChatProviders() {
  await loadChatProvider("slack", chatSlackStatus, chatSlackEnabled, chatSlackUrl);
  await loadChatProvider("teams", chatTeamsStatus, chatTeamsEnabled, chatTeamsUrl);
  await loadChatProvider("discord", chatDiscordStatus, chatDiscordEnabled, chatDiscordUrl);
}

async function loadEmailConnection() {
  if (!emailForm) return;
  try {
    const response = await fetch(apiUrl("/api/email/connection"), { headers: getApiHeaders() });
    if (!response.ok) {
      if (emailStatus) emailStatus.textContent = "Email connection unavailable.";
      return;
    }
    const data = await response.json();
    if (emailHost) emailHost.value = data.host || "";
    if (emailPort) emailPort.value = data.port || 993;
    if (emailUsername) emailUsername.value = data.username || "";
    if (emailUseTls) emailUseTls.checked = data.use_tls !== false;
    if (emailInterval) emailInterval.value = data.poll_interval_minutes || 30;
    if (emailEnabled) emailEnabled.checked = Boolean(data.enabled);
    if (emailStatus) {
      if (!data.configured) {
        emailStatus.textContent = "Email polling not configured.";
      } else if (data.enabled) {
        const last = data.last_success ? formatDate(data.last_success) : "never";
        emailStatus.textContent = "Email polling enabled · Last success " + last;
      } else {
        emailStatus.textContent = "Email polling disabled.";
      }
    }
  } catch (err) {
    if (emailStatus) emailStatus.textContent = "Unable to load email settings.";
  }
}

async function loadTopology() {
  if (!topologyCards) return;
  try {
    const response = await fetch(apiUrl("/api/network/topology"), { headers: getApiHeaders() });
    if (!response.ok) {
      topologyCards.innerHTML = "";
      return;
    }
    const data = await response.json();
    const counts = data.counts || {};
    const summary = "NAS " + (counts.nas || 0) + " · Inference " + (counts.inference || 0) + " · HTTP " + (counts.http || 0) + " · Other " + (counts.other || 0);
    const nasLabel = data.nas_backup_enabled ? "enabled" : "disabled";
    const syncLabel = data.sync_enabled ? "enabled" : "disabled";
    const infLabel = data.inference_enabled ? "enabled" : "disabled";
    topologyCards.innerHTML = ""
      + "<div class=\"card\">"
      + "<h4>Discovered services</h4>"
      + "<p class=\"muted\">Last scan " + formatDate(data.last_scan) + " · " + summary + "</p>"
      + "</div>"
      + "<div class=\"card\">"
      + "<h4>Configured resources</h4>"
      + "<p class=\"muted\">NAS backup: " + nasLabel + "</p>"
      + "<p class=\"muted\">Home sync: " + syncLabel + "</p>"
      + "<p class=\"muted\">Inference: " + infLabel + "</p>"
      + "</div>";
  } catch (err) {
    topologyCards.innerHTML = "";
  }
}

async function loadStatus() {
  const healthResponse = await fetch(apiUrl('/api/health'), { headers: getApiHeaders() });
  const healthData = await healthResponse.json();

  const statusResponse = await fetch(apiUrl('/api/status'), { headers: getApiHeaders() });
  const statusData = await statusResponse.json();

  // Fetch calendar connection for sync status (Story 37.2)
  let connectionData = null;
  try {
    const connectionResponse = await fetch(apiUrl('/api/calendar/connection'), { headers: getApiHeaders() });
    if (connectionResponse.ok) {
      connectionData = await connectionResponse.json();
    }
  } catch (err) {
    // Silently fail - connection may not exist
  }

  const backupStatus = statusData.backup_last_status || {};
  const storageStatus = statusData.storage || {};
  const recoveryStatus = statusData.recovery_check || { status: 'unknown', last_restore: null };

  const updatedAt = formatDate(statusData.updated_at);
  statusSummary.textContent = `All systems healthy · Updated ${updatedAt}`;

  statusDb.textContent = `DB encrypted: ${statusData.db_encrypted ? 'yes' : 'no'}`;
  statusIngestion.textContent = `Ingestion last run: ${formatDate(statusData.ingestion_last_run)}`;
  statusBackup.textContent = `Backup: ${backupStatus.status || 'unknown'} (last attempt ${formatDate(backupStatus.last_attempt)})`;
  statusRestore.textContent = `Restore: ${formatDate(backupStatus.last_restore)}`;
  statusErrors.textContent = `Errors: ${statusData.error_count}`;
  statusStorage.textContent = `Storage: ${formatBytes(storageStatus.used_bytes)} used of ${formatBytes(storageStatus.total_bytes)} (${storageStatus.used_percent ?? 'unknown'}%)`;
  statusRecovery.textContent = `Recovery check: ${recoveryStatus.status} (last restore ${formatDate(recoveryStatus.last_restore)})`;

  const accelerator = statusData.accelerator_status || {};
  if (acceleratorStatus) {
    const type = accelerator.type || "unknown";
    const status = accelerator.status || "unknown";
    acceleratorStatus.textContent = "Accelerator: " + type + " · " + status;
  }
  if (acceleratorDetail) {
    const detailParts = [];
    if (accelerator.detail) detailParts.push(accelerator.detail);
    if (accelerator.temperature_c !== undefined && accelerator.temperature_c !== null) detailParts.push("Temp " + accelerator.temperature_c + "°C");
    if (accelerator.utilization_pct !== undefined && accelerator.utilization_pct !== null) detailParts.push("Util " + accelerator.utilization_pct + "%");
    if (accelerator.memory_pct !== undefined && accelerator.memory_pct !== null) detailParts.push("Mem " + accelerator.memory_pct + "%");
    if (accelerator.throttled) detailParts.push("Throttling");
    acceleratorDetail.textContent = detailParts.join(" · ");
  }

  const backupFailed = backupStatus.status === 'failed';
  const storageAlert = Boolean(statusData.storage_alert);
  const recoveryFailed = recoveryStatus.status === 'failed';
  const needsAttention = statusData.error_count > 0 || !statusData.db_encrypted || healthData.status !== 'ok' || backupFailed || storageAlert || recoveryFailed;
  if (needsAttention) {
    statusHealth.textContent = 'Attention needed';
    statusSummary.textContent = `Action required · Updated ${updatedAt}`;
    if (storageAlert) {
      setBanner('error', 'Storage usage is high. Free space or expand storage.');
    } else if (backupFailed) {
      setBanner('error', 'Backup failed. Run backup now from Status.');
    } else if (recoveryFailed) {
      setBanner('error', 'Recovery drill failed. Run a restore check.');
    } else {
      setBanner('error', 'System needs attention. Review status details.');
    }
    statusDetails.classList.remove('hidden');
    statusToggle.textContent = 'Hide details';
    statusToggle.setAttribute('aria-expanded', 'true');
  } else {
    statusHealth.textContent = 'Healthy';
    setBanner('', '');
  }

  backupAction.classList.toggle('hidden', !backupFailed);
  updateCalendarStatus(statusData, connectionData);
  loadEmailConnection();
}

loadStatus().catch(() => {
  setBanner('error', 'Unable to load system status. Check local connectivity.');
});

// Check OAuth provider availability on load
checkOAuthStatus();

backupAction.addEventListener('click', async () => {
  await fetch(apiUrl('/api/status/actions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
    body: JSON.stringify({ action: 'run_backup' }),
  });
  loadStatus();
});

apiKeyForm.addEventListener('submit', event => {
  event.preventDefault();
  const value = apiKeyInput.value.trim();
  if (!value) {
    apiKeyStatus.textContent = 'Enter an API key to save.';
    return;
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('custos_api_key', value);
  }
  apiKeyInput.value = '';
  updateApiKeyStatus();
});

apiKeyClear.addEventListener('click', () => {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('custos_api_key');
  }
  updateApiKeyStatus();
});

updateApiKeyStatus();

initCapture({ onSuccess: loadStatus });
refreshDemoMode();
loadClosure();
loadThreads();
loadDecisionSurfaces();
loadContextGaps();
loadRelationshipSignals();
loadTopology();
loadNetworkSettings();
loadSummarizationSettings();
loadChatProviders();
if (networkAddService) {
  networkAddService.addEventListener('click', () => buildManualServiceRow({}));
}

if (emailForm) {
  emailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!getApiBase() || !isSetupComplete()) {
      if (emailMessage) emailMessage.textContent = "Connect to your backend before saving.";
      return;
    }
    if (emailMessage) emailMessage.textContent = "Saving email settings…";
    const payload = {
      host: emailHost ? emailHost.value.trim() : "",
      port: emailPort && emailPort.value ? Number(emailPort.value) : 993,
      username: emailUsername ? emailUsername.value.trim() : "",
      password: emailPassword ? emailPassword.value : null,
      use_tls: emailUseTls ? emailUseTls.checked : true,
      enabled: emailEnabled ? emailEnabled.checked : false,
      poll_interval_minutes: emailInterval && emailInterval.value ? Number(emailInterval.value) : 30,
    };
    try {
      const response = await fetch(apiUrl("/api/email/connection"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getApiHeaders() },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        if (emailMessage) emailMessage.textContent = "Unable to save email settings.";
        return;
      }
      if (emailMessage) emailMessage.textContent = "Email settings saved.";
      loadEmailConnection();
    } catch (err) {
      if (emailMessage) emailMessage.textContent = "Unable to save email settings.";
    }
  });
}

if (emailTest) {
  emailTest.addEventListener("click", async () => {
    if (emailMessage) emailMessage.textContent = "Testing email connection…";
    const payload = {
      host: emailHost ? emailHost.value.trim() : "",
      port: emailPort && emailPort.value ? Number(emailPort.value) : 993,
      username: emailUsername ? emailUsername.value.trim() : "",
      password: emailPassword ? emailPassword.value : null,
      use_tls: emailUseTls ? emailUseTls.checked : true,
      enabled: emailEnabled ? emailEnabled.checked : false,
      poll_interval_minutes: emailInterval && emailInterval.value ? Number(emailInterval.value) : 30,
    };
    try {
      const response = await fetch(apiUrl("/api/email/connection/test"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getApiHeaders() },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const detail = error.detail || "Unable to connect.";
        if (emailMessage) emailMessage.textContent = detail;
        return;
      }
      if (emailMessage) emailMessage.textContent = "Email connection ok.";
    } catch (err) {
      if (emailMessage) emailMessage.textContent = "Unable to test email connection.";
    }
  });
}

if (chatSlackForm) {
  chatSlackForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      secret: chatSlackSecret ? chatSlackSecret.value.trim() : null,
      enabled: chatSlackEnabled ? chatSlackEnabled.checked : false,
    };
    const response = await fetch(apiUrl("/api/integrations/chat/connection/slack"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getApiHeaders() },
      body: JSON.stringify(payload),
    });
    if (chatSlackStatus) {
      chatSlackStatus.textContent = response.ok ? "Slack settings saved." : "Unable to save Slack settings.";
    }
    loadChatProviders();
  });
}

if (chatTeamsForm) {
  chatTeamsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      secret: chatTeamsSecret ? chatTeamsSecret.value.trim() : null,
      enabled: chatTeamsEnabled ? chatTeamsEnabled.checked : false,
    };
    const response = await fetch(apiUrl("/api/integrations/chat/connection/teams"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getApiHeaders() },
      body: JSON.stringify(payload),
    });
    if (chatTeamsStatus) {
      chatTeamsStatus.textContent = response.ok ? "Teams settings saved." : "Unable to save Teams settings.";
    }
    loadChatProviders();
  });
}

if (chatDiscordForm) {
  chatDiscordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      secret: chatDiscordSecret ? chatDiscordSecret.value.trim() : null,
      enabled: chatDiscordEnabled ? chatDiscordEnabled.checked : false,
    };
    const response = await fetch(apiUrl("/api/integrations/chat/connection/discord"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getApiHeaders() },
      body: JSON.stringify(payload),
    });
    if (chatDiscordStatus) {
      chatDiscordStatus.textContent = response.ok ? "Discord settings saved." : "Unable to save Discord settings.";
    }
    loadChatProviders();
  });
}

if (emailPoll) {
  emailPoll.addEventListener("click", async () => {
    if (emailMessage) emailMessage.textContent = "Polling inbox…";
    try {
      const response = await fetch(apiUrl("/api/email/poll"), {
        method: "POST",
        headers: { ...getApiHeaders(), "Content-Type": "application/json" },
      });
      if (!response.ok) {
        if (emailMessage) emailMessage.textContent = "Unable to poll inbox.";
        return;
      }
      if (emailMessage) emailMessage.textContent = "Inbox polled.";
      loadEmailConnection();
    } catch (err) {
      if (emailMessage) emailMessage.textContent = "Unable to poll inbox.";
    }
  });
}

if (summarizationForm) {
  summarizationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      enabled: Boolean(summarizationEnabled && summarizationEnabled.checked),
      provider: summarizationProvider ? summarizationProvider.value : null,
      model: summarizationModel ? summarizationModel.value.trim() || null : null,
      max_input_tokens: summarizationMaxTokens && summarizationMaxTokens.value
        ? Number(summarizationMaxTokens.value)
        : null,
    };
    try {
      const response = await fetch(apiUrl("/api/summarization/settings"), {
        method: "POST",
        headers: { ...getApiHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        if (summarizationStatus) summarizationStatus.textContent = "Unable to save summarization settings.";
        return;
      }
      const data = await response.json();
      updateSummarizationStatus(data);
    } catch (err) {
      if (summarizationStatus) summarizationStatus.textContent = "Unable to save summarization settings.";
    }
  });
}

if (networkSettingsForm) {
  networkSettingsForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!getApiBase() || !isSetupComplete()) {
      if (networkSettingsStatus) {
        networkSettingsStatus.textContent = 'Connect to your backend before saving.';
      }
      return;
    }
    if (networkSettingsStatus) {
      networkSettingsStatus.textContent = 'Saving network settings…';
    }
    const payload = {
      discovery_enabled: networkDiscoveryEnabled ? networkDiscoveryEnabled.checked : true,
      scan_interval_minutes: networkScanInterval ? Number(networkScanInterval.value || 15) : 15,
      manual_services: readManualServices(),
    };
    const response = await fetch(apiUrl('/api/network/settings'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      if (networkSettingsStatus) {
        networkSettingsStatus.textContent = 'Unable to save network settings.';
      }
      return;
    }
    if (networkSettingsStatus) {
      networkSettingsStatus.textContent = 'Network settings saved.';
    }
    loadNetworkSettings();
    loadTopology();
  });
}

if (networkScanNow) {
  networkScanNow.addEventListener('click', async () => {
    if (!getApiBase() || !isSetupComplete()) {
      if (networkSettingsStatus) {
        networkSettingsStatus.textContent = 'Connect to your backend before scanning.';
      }
      return;
    }
    if (networkSettingsStatus) {
      networkSettingsStatus.textContent = 'Scanning local services…';
    }
    const response = await fetch(apiUrl('/api/network/services'), { headers: getApiHeaders() });
    if (!response.ok) {
      if (networkSettingsStatus) {
        networkSettingsStatus.textContent = 'Network scan failed.';
      }
      return;
    }
    const data = await response.json();
    const count = Array.isArray(data.services) ? data.services.length : 0;
    if (networkSettingsStatus) {
      networkSettingsStatus.textContent = 'Scan complete. ' + count + ' services detected.';
    }
    loadNetworkSettings();
    loadTopology();
  });
}


if (closureGroupMeeting) {
  closureGroupMeeting.addEventListener('click', () => {
    closureGroup = 'meeting';
    loadClosure();
  });
}
if (closureGroupPerson) {
  closureGroupPerson.addEventListener('click', () => {
    closureGroup = 'person';
    loadClosure();
  });
}

if (calendarConnect && calendarModal) {
  calendarConnect.addEventListener('click', async () => {
    // Check if already connected (button text indicates disconnect)
    if (calendarConnect.textContent.toLowerCase().includes('disconnect')) {
      if (confirm('Are you sure you want to disconnect your calendar?')) {
        await disconnectCalendar();
      }
      return;
    }

    // Start connection wizard
    setWizardStep(1);
    if (calendarConsent) {
      calendarConsent.checked = getCalendarConsent();
    }
    if (calendarConsentError) {
      calendarConsentError.textContent = '';
    }
    if (calendarProviderError) {
      calendarProviderError.textContent = '';
    }
    // Pre-check OAuth status
    checkOAuthStatus();
    setCalendarModalOpen(true);
  });
}

if (calendarImport) {
  calendarImport.addEventListener('click', async () => {
    if (!getApiBase() || !isSetupComplete()) {
      if (calendarImportStatus) {
        calendarImportStatus.textContent = 'Connect to your backend before importing.';
      }
      return;
    }
    if (calendarImport.disabled) {
      if (calendarImportStatus) {
        calendarImportStatus.textContent = 'Calendar not connected yet.';
      }
      return;
    }
    if (calendarImportStatus) {
      calendarImportStatus.textContent = 'Running calendar import…';
    }
    const response = await fetch(apiUrl('/api/calendar/ingest'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
    });
    if (!response.ok) {
      if (calendarImportStatus) {
        calendarImportStatus.textContent = 'Calendar import failed. Check connection.';
      }
      return;
    }
    const data = await response.json();
    if (calendarImportStatus) {
      calendarImportStatus.textContent = `Imported ${data.events || 0} events.`;
    }
    loadStatus();
  });
}

if (calendarModal) {
  calendarModal.addEventListener('click', event => {
    if (event.target && event.target.hasAttribute('data-calendar-close')) {
      setCalendarModalOpen(false);
    }
  });
}

if (calendarClose) {
  calendarClose.addEventListener('click', () => setCalendarModalOpen(false));
}

if (calendarForm) {
  calendarForm.addEventListener('click', event => {
    const target = event.target;
    if (!target) return;

    // Handle provider button clicks
    const providerButton = target.closest('.provider-button');
    if (providerButton && !providerButton.disabled) {
      const provider = providerButton.dataset.provider;
      if (calendarProviderError) {
        calendarProviderError.textContent = '';
      }
      if (provider === 'demo') {
        connectDemoCalendar();
      } else if (provider === 'google' || provider === 'microsoft') {
        startOAuthFlow(provider);
      }
      return;
    }

    if (target.hasAttribute('data-calendar-next')) {
      const current = calendarForm.querySelector('.wizard-step:not(.hidden)');
      const step = Number(current?.dataset?.step || 1);
      if (step === 2) {
        if (!calendarConsent?.checked) {
          if (calendarConsentError) {
            calendarConsentError.textContent = 'Please confirm read-only consent to continue.';
          }
          return;
        }
        setCalendarConsent(true);
        // Check OAuth status before showing provider selection
        checkOAuthStatus();
      }
      setWizardStep(step + 1);
    }
    if (target.hasAttribute('data-calendar-back')) {
      const current = calendarForm.querySelector('.wizard-step:not(.hidden)');
      const step = Number(current?.dataset?.step || 1);
      // Skip step 4 (authorization) when going back
      const nextStep = step === 4 ? 3 : Math.max(step - 1, 1);
      setWizardStep(nextStep);
    }
    if (target.hasAttribute('data-calendar-finish')) {
      setCalendarModalOpen(false);
    }
  });
}

if (demoResetButton) {
  demoResetButton.addEventListener('click', async () => {
    if (!getStoredApiKey()) {
      if (demoResetStatus) {
        demoResetStatus.textContent = 'Add an admin API key to reset demo data.';
      }
      return;
    }
    if (demoResetStatus) {
      demoResetStatus.textContent = 'Resetting demo data…';
    }
    const response = await fetch(apiUrl('/api/admin/demo/reset'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
    });
    if (!response.ok) {
      if (demoResetStatus) {
        demoResetStatus.textContent = 'Reset failed. Check admin key and dev mode.';
      }
      return;
    }
    if (demoResetStatus) {
      demoResetStatus.textContent = 'Demo data reset. Refreshing views…';
    }
    setDemoMode(true);
    setDemoBadge(true);
    setDemoResetVisibility(true);
    loadStatus();
  });
}

// Offline indicator management
const offlineBadge = document.getElementById('offline-badge');

function updateOfflineIndicator() {
  if (!offlineBadge) return;
  const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
  offlineBadge.classList.toggle('hidden', !isOffline);
}

window.addEventListener('online', () => {
  updateOfflineIndicator();
  loadStatus().catch(() => {});
});

window.addEventListener('offline', updateOfflineIndicator);

updateOfflineIndicator();

// PWA Install prompt management
const pwaInstallCard = document.getElementById('pwa-install-card');
const pwaInstallButton = document.getElementById('pwa-install');
const pwaInstallStatus = document.getElementById('pwa-install-status');

let deferredInstallPrompt = null;

// Debug mode: add ?pwa-debug=1 to URL to force-show install card
const urlParams = new URLSearchParams(window.location.search);
const pwaDebugMode = urlParams.get('pwa-debug') === '1';

function updatePwaInstallVisibility() {
  if (!pwaInstallCard) return;

  // Debug mode: always show the card for testing
  if (pwaDebugMode) {
    pwaInstallCard.classList.remove('hidden');
    if (pwaInstallStatus) {
      pwaInstallStatus.textContent = 'Debug mode: Install requires HTTPS or localhost.';
    }
    return;
  }

  // Hide if already installed (running in standalone mode)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                       window.navigator.standalone === true;

  if (isStandalone) {
    pwaInstallCard.classList.add('hidden');
    return;
  }

  // Show only if we have a deferred install prompt
  if (deferredInstallPrompt) {
    pwaInstallCard.classList.remove('hidden');
  }
}

// Capture the install prompt event
window.addEventListener('beforeinstallprompt', (event) => {
  // Prevent the default browser prompt
  event.preventDefault();
  // Store for later use
  deferredInstallPrompt = event;
  // Show our custom install UI
  updatePwaInstallVisibility();
  console.log('[Custos] PWA install prompt available');
});

// Handle install button click
if (pwaInstallButton) {
  pwaInstallButton.addEventListener('click', async () => {
    if (!deferredInstallPrompt) {
      if (pwaInstallStatus) {
        pwaInstallStatus.textContent = 'Install not available. Try adding to home screen manually.';
      }
      return;
    }

    // Show the install prompt
    deferredInstallPrompt.prompt();

    // Wait for the user's response
    const { outcome } = await deferredInstallPrompt.userChoice;

    if (outcome === 'accepted') {
      if (pwaInstallStatus) {
        pwaInstallStatus.textContent = 'Installing Custos...';
      }
      console.log('[Custos] User accepted PWA install');
    } else {
      if (pwaInstallStatus) {
        pwaInstallStatus.textContent = 'Installation cancelled.';
      }
      console.log('[Custos] User dismissed PWA install');
    }

    // Clear the deferred prompt - it can only be used once
    deferredInstallPrompt = null;
    updatePwaInstallVisibility();
  });
}

// Listen for successful installation
window.addEventListener('appinstalled', () => {
  console.log('[Custos] PWA installed successfully');
  deferredInstallPrompt = null;
  if (pwaInstallCard) {
    pwaInstallCard.classList.add('hidden');
  }
  if (pwaInstallStatus) {
    pwaInstallStatus.textContent = 'Custos installed successfully!';
  }
});

// Check initial PWA state
updatePwaInstallVisibility();

// ============================================================================
// Settings Modal (Epics 33, 34, 35)
// ============================================================================

const settingsCard = document.getElementById('settings-card');
const settingsOpen = document.getElementById('settings-open');
const settingsModal = document.getElementById('settings-modal');
const settingsClose = document.getElementById('settings-close');
const settingsSave = document.getElementById('settings-save');
const settingsSummary = document.getElementById('settings-summary');

// Radio buttons
const briefingModeTime = document.getElementById('briefing-mode-time');
const briefingModePerson = document.getElementById('briefing-mode-person');
const contextModeStandard = document.getElementById('context-mode-standard');
const contextModeCare = document.getElementById('context-mode-care');
const contextModeProfessional = document.getElementById('context-mode-professional');

function getSettingsSummaryText() {
  const briefing = getBriefingMode();
  const care = getCareMode();
  const professional = getProfessionalMode();

  const parts = [];

  // Briefing mode
  if (briefing === 'person') {
    parts.push('Person-first briefing');
  } else {
    parts.push('Time-first briefing');
  }

  // Context mode
  if (care) {
    parts.push('Care mode');
  } else if (professional) {
    parts.push('Professional mode');
  } else {
    parts.push('Standard mode');
  }

  return parts.join(' · ');
}

function updateSettingsSummary() {
  if (settingsSummary) {
    settingsSummary.textContent = getSettingsSummaryText();
  }
}

function loadSettingsToModal() {
  // Load current briefing mode
  const briefing = getBriefingMode();
  if (briefingModeTime) briefingModeTime.checked = briefing !== 'person';
  if (briefingModePerson) briefingModePerson.checked = briefing === 'person';

  // Load current context mode
  const care = getCareMode();
  const professional = getProfessionalMode();
  if (contextModeStandard) contextModeStandard.checked = !care && !professional;
  if (contextModeCare) contextModeCare.checked = care;
  if (contextModeProfessional) contextModeProfessional.checked = professional;
}

function saveSettingsFromModal() {
  // Save briefing mode
  if (briefingModePerson?.checked) {
    setBriefingMode('person');
  } else {
    setBriefingMode('time');
  }

  // Save context mode (mutually exclusive)
  if (contextModeCare?.checked) {
    setCareMode(true);
    setProfessionalMode(false);
  } else if (contextModeProfessional?.checked) {
    setCareMode(false);
    setProfessionalMode(true);
  } else {
    setCareMode(false);
    setProfessionalMode(false);
  }

  updateSettingsSummary();
}

function setSettingsModalOpen(open) {
  if (!settingsModal) return;
  settingsModal.classList.toggle('open', open);
  settingsModal.setAttribute('aria-hidden', open ? 'false' : 'true');

  if (open) {
    loadSettingsToModal();
  }
}

// Initialize settings summary
updateSettingsSummary();

// Settings modal event listeners
if (settingsOpen) {
  settingsOpen.addEventListener('click', () => {
    setSettingsModalOpen(true);
  });
}

if (settingsClose) {
  settingsClose.addEventListener('click', () => {
    setSettingsModalOpen(false);
  });
}

if (settingsSave) {
  settingsSave.addEventListener('click', () => {
    saveSettingsFromModal();
    setSettingsModalOpen(false);
    // Reload page to apply terminology changes throughout
    window.location.reload();
  });
}

if (settingsModal) {
  settingsModal.addEventListener('click', (event) => {
    if (event.target?.hasAttribute('data-settings-close')) {
      setSettingsModalOpen(false);
    }
  });

  // Close on Escape key
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && settingsModal.classList.contains('open')) {
      setSettingsModalOpen(false);
    }
  });
}

const analyticsSummary = document.getElementById("analytics-summary");
const relationshipHealth = document.getElementById("relationship-health");
const commitmentAnalytics = document.getElementById("commitment-analytics");
const contextCoverage = document.getElementById("context-coverage");
const analyticsExport = document.getElementById("analytics-export");
const analyticsExportStatus = document.getElementById("analytics-export-status");

function renderAnalyticsSummary(metrics) {
  if (!analyticsSummary) return;
  analyticsSummary.innerHTML = "";
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <strong>Totals</strong>
    <p class="muted">Meetings: ${metrics.total_meetings || 0}</p>
    <p class="muted">People: ${metrics.total_people || 0}</p>
    <p class="muted">Captures: ${metrics.total_sources || 0}</p>
    <p class="muted">Open commitments: ${metrics.open_commitments || 0}</p>
  `;
  analyticsSummary.appendChild(card);
}

function renderRelationshipHealth(items) {
  if (!relationshipHealth) return;
  relationshipHealth.innerHTML = "";
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <strong>${item.name}</strong>
      <p class="muted">Interactions (last ${item.window_days} days): ${item.count}</p>
    `;
    relationshipHealth.appendChild(card);
  });
}

function renderCommitmentAnalytics(data) {
  if (!commitmentAnalytics) return;
  commitmentAnalytics.innerHTML = "";
  const card = document.createElement("div");
  card.className = "card";
  const completionPct = Math.round((data.completion_rate || 0) * 100);
  card.innerHTML = `
    <strong>Commitments</strong>
    <p class="muted">Total: ${data.total || 0}</p>
    <p class="muted">Acknowledged: ${data.acknowledged || 0}</p>
    <p class="muted">Open: ${data.open || 0}</p>
    <p class="muted">Completion: ${completionPct}%</p>
  `;
  commitmentAnalytics.appendChild(card);
}

function renderContextCoverage(data) {
  if (!contextCoverage) return;
  contextCoverage.innerHTML = "";
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <strong>Context coverage</strong>
    <p class="muted">Meetings with captures: ${data.meetings_with_sources || 0}</p>
    <p class="muted">Meetings without captures: ${data.meetings_without_sources || 0}</p>
    <p class="muted">Stale people: ${(data.stale_people || []).length}</p>
  `;
  contextCoverage.appendChild(card);
}

async function loadAnalytics() {
  if (!analyticsSummary) return;
  try {
    const refresh = await fetch(apiUrl("/api/analytics/refresh"), { method: "POST", headers: getApiHeaders() });
    if (refresh.ok) {
      const data = await refresh.json();
      renderAnalyticsSummary(data.metrics || {});
    }
    const relationship = await fetch(apiUrl("/api/analytics/relationship-health?window_days=30"));
    if (relationship.ok) {
      const data = await relationship.json();
      renderRelationshipHealth(data.items || []);
    }
    const commitments = await fetch(apiUrl("/api/analytics/commitments"));
    if (commitments.ok) {
      renderCommitmentAnalytics(await commitments.json());
    }
    const coverage = await fetch(apiUrl("/api/analytics/context-coverage"));
    if (coverage.ok) {
      renderContextCoverage(await coverage.json());
    }
  } catch (err) {
    // ignore
  }
}

if (analyticsExport) {
  analyticsExport.addEventListener("click", async () => {
    if (analyticsExportStatus) analyticsExportStatus.textContent = "Exporting...";
    const response = await fetch(apiUrl("/api/analytics/export"), { method: "POST", headers: getApiHeaders() });
    if (!response.ok) {
      if (analyticsExportStatus) analyticsExportStatus.textContent = "Export failed.";
      return;
    }
    const data = await response.json();
    const blob = new Blob([data.csv || ""], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "custos-analytics.csv";
    link.click();
    URL.revokeObjectURL(url);
    if (analyticsExportStatus) analyticsExportStatus.textContent = "Export ready.";
  });
}

loadAnalytics();

const exportForm = document.getElementById("export-form");
const exportFormat = document.getElementById("export-format");
const exportStatus = document.getElementById("export-status");
const exportIcs = document.getElementById("export-ics");
const exportIcsStatus = document.getElementById("export-ics-status");

if (exportForm) {
  exportForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (exportStatus) exportStatus.textContent = "Exporting...";
    const response = await fetch(apiUrl("/api/export/run"), {
      method: "POST",
      headers: { ...getApiHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ format: exportFormat.value }),
    });
    if (!response.ok) {
      if (exportStatus) exportStatus.textContent = "Export failed.";
      return;
    }
    const data = await response.json();
    const content = data.format === "json" ? JSON.stringify(data.content, null, 2) : data.content;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = data.format === "json" ? "custos-export.json" : "custos-export.md";
    link.click();
    URL.revokeObjectURL(url);
    if (exportStatus) exportStatus.textContent = "Export ready.";
  });
}

if (exportIcs) {
  exportIcs.addEventListener("click", async () => {
    if (exportIcsStatus) exportIcsStatus.textContent = "Exporting...";
    const response = await fetch(apiUrl("/api/export/ics"));
    if (!response.ok) {
      if (exportIcsStatus) exportIcsStatus.textContent = "Export failed.";
      return;
    }
    const data = await response.json();
    const blob = new Blob([data.ics || ""], { type: "text/calendar" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "custos-calendar.ics";
    link.click();
    URL.revokeObjectURL(url);
    if (exportIcsStatus) exportIcsStatus.textContent = "Export ready.";
  });
}


const userStatus = document.getElementById("user-status");
const userCreateForm = document.getElementById("user-create-form");
const userCreateName = document.getElementById("user-create-name");
const userCreateEmail = document.getElementById("user-create-email");
const userCreatePassword = document.getElementById("user-create-password");
const userLoginForm = document.getElementById("user-login-form");
const userLoginIdentifier = document.getElementById("user-login-identifier");
const userLoginPassword = document.getElementById("user-login-password");
const householdToggle = document.getElementById("household-mode");
const householdStatus = document.getElementById("household-status");

function updateUserStatus() {
  if (!userStatus) return;
  const userId = localStorage.getItem("custos_user_id");
  const userName = localStorage.getItem("custos_user_name");
  if (userId) {
    userStatus.textContent = "Active user: " + (userName || userId);
  } else {
    userStatus.textContent = "No user selected.";
  }
}

function updateHouseholdStatus() {
  if (!householdStatus) return;
  const mode = localStorage.getItem("custos_default_visibility") || "personal";
  if (householdToggle) householdToggle.checked = mode === "shared";
  householdStatus.textContent = mode === "shared"
    ? "Shared captures are the default."
    : "Personal captures are the default.";
}

updateUserStatus();
updateHouseholdStatus();

if (householdToggle) {
  householdToggle.addEventListener("change", () => {
    const mode = householdToggle.checked ? "shared" : "personal";
    localStorage.setItem("custos_default_visibility", mode);
    updateHouseholdStatus();
  });
}

if (userCreateForm) {
  userCreateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = userCreateName ? userCreateName.value.trim() : "";
    const email = userCreateEmail ? userCreateEmail.value.trim() : "";
    const password = userCreatePassword ? userCreatePassword.value : "";
    if (!name || !password) {
      if (userStatus) userStatus.textContent = "Name and password are required.";
      return;
    }
    try {
      const response = await fetch(apiUrl("/api/users"), {
        method: "POST",
        headers: { ...getApiHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ name, email: email || null, password }),
      });
      if (!response.ok) {
        if (userStatus) userStatus.textContent = "Unable to create user.";
        return;
      }
      const data = await response.json();
      localStorage.setItem("custos_user_id", data.id);
      localStorage.setItem("custos_user_name", data.name || data.id);
      updateUserStatus();
      if (userCreatePassword) userCreatePassword.value = "";
    } catch (err) {
      if (userStatus) userStatus.textContent = "Unable to create user.";
    }
  });
}

if (userLoginForm) {
  userLoginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const identifier = userLoginIdentifier ? userLoginIdentifier.value.trim() : "";
    const password = userLoginPassword ? userLoginPassword.value : "";
    if (!identifier || !password) {
      if (userStatus) userStatus.textContent = "Email/name and password are required.";
      return;
    }
    try {
      const response = await fetch(apiUrl("/api/users/login"), {
        method: "POST",
        headers: { ...getApiHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ email: identifier, name: identifier, password }),
      });
      if (!response.ok) {
        if (userStatus) userStatus.textContent = "Unable to authenticate user.";
        return;
      }
      const data = await response.json();
      localStorage.setItem("custos_user_id", data.id);
      localStorage.setItem("custos_user_name", data.name || data.id);
      updateUserStatus();
      if (userLoginPassword) userLoginPassword.value = "";
    } catch (err) {
      if (userStatus) userStatus.textContent = "Unable to authenticate user.";
    }
  });
}
