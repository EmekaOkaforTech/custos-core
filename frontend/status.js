import { apiUrl, formatDate, getApiHeaders, getStoredApiKey } from './ui-state.js';

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
const backupAction = document.getElementById('backup-action');
const apiKeyForm = document.getElementById('api-key-form');
const apiKeyInput = document.getElementById('api-key-input');
const apiKeyClear = document.getElementById('api-key-clear');
const apiKeyStatus = document.getElementById('api-key-status');

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

statusToggle.addEventListener('click', () => {
  const next = statusDetails.classList.contains('hidden');
  statusDetails.classList.toggle('hidden', !next);
  statusToggle.textContent = next ? 'Hide details' : 'View details';
  statusToggle.setAttribute('aria-expanded', next ? 'true' : 'false');
});

async function loadStatus() {
  const healthResponse = await fetch(apiUrl('/api/health'), { headers: getApiHeaders() });
  const healthData = await healthResponse.json();

  const statusResponse = await fetch(apiUrl('/api/status'), { headers: getApiHeaders() });
  const statusData = await statusResponse.json();

  const updatedAt = formatDate(statusData.updated_at);
  statusSummary.textContent = `All systems healthy · Updated ${updatedAt}`;

  statusDb.textContent = `DB encrypted: ${statusData.db_encrypted ? 'yes' : 'no'}`;
  statusIngestion.textContent = `Ingestion last run: ${formatDate(statusData.ingestion_last_run)}`;
  statusBackup.textContent = `Backup: ${statusData.backup_last_status.status} (last attempt ${formatDate(statusData.backup_last_status.last_attempt)})`;
  statusRestore.textContent = `Restore: ${formatDate(statusData.backup_last_status.last_restore)}`;
  statusErrors.textContent = `Errors: ${statusData.error_count}`;
  statusStorage.textContent = `Storage: ${formatBytes(statusData.storage.used_bytes)} used of ${formatBytes(statusData.storage.total_bytes)} (${statusData.storage.used_percent}%)`;
  statusRecovery.textContent = `Recovery check: ${statusData.recovery_check.status} (last restore ${formatDate(statusData.recovery_check.last_restore)})`;

  const backupFailed = statusData.backup_last_status.status === 'failed';
  const storageAlert = statusData.storage_alert;
  const recoveryMissing = statusData.recovery_check.status !== 'ok';
  const needsAttention = statusData.error_count > 0 || !statusData.db_encrypted || healthData.status !== 'ok' || backupFailed || storageAlert || recoveryMissing;
  if (needsAttention) {
    statusHealth.textContent = 'Attention needed';
    statusSummary.textContent = `Action required · Updated ${updatedAt}`;
    if (storageAlert) {
      setBanner('error', 'Storage usage is high. Free space or expand storage.');
    } else if (backupFailed) {
      setBanner('error', 'Backup failed. Run backup now from Status.');
    } else if (recoveryMissing) {
      setBanner('error', 'No recovery drill recorded. Run a restore check.');
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
}

loadStatus().catch(() => {
  setBanner('error', 'Unable to load system status. Check local connectivity.');
});

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
