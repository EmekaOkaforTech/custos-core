import { formatDate } from './ui-state.js';

const statusHealth = document.getElementById('status-health');
const statusBanner = document.getElementById('status-banner');
const statusToggle = document.getElementById('status-toggle');
const statusDetails = document.getElementById('status-details');
const statusSummary = document.getElementById('status-summary-text');
const statusDb = document.getElementById('status-db');
const statusIngestion = document.getElementById('status-ingestion');
const statusBackup = document.getElementById('status-backup');
const statusRestore = document.getElementById('status-restore');
const statusErrors = document.getElementById('status-errors');
const backupAction = document.getElementById('backup-action');

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

statusToggle.addEventListener('click', () => {
  const next = statusDetails.classList.contains('hidden');
  statusDetails.classList.toggle('hidden', !next);
  statusToggle.textContent = next ? 'Hide details' : 'View details';
  statusToggle.setAttribute('aria-expanded', next ? 'true' : 'false');
});

async function loadStatus() {
  const healthResponse = await fetch('/api/health');
  const healthData = await healthResponse.json();

  const statusResponse = await fetch('/api/status');
  const statusData = await statusResponse.json();

  const updatedAt = formatDate(statusData.updated_at);
  statusSummary.textContent = `All systems healthy · Updated ${updatedAt}`;

  statusDb.textContent = `DB encrypted: ${statusData.db_encrypted ? 'yes' : 'no'}`;
  statusIngestion.textContent = `Ingestion last run: ${formatDate(statusData.ingestion_last_run)}`;
  statusBackup.textContent = `Backup: ${statusData.backup_last_status.status} (last attempt ${formatDate(statusData.backup_last_status.last_attempt)})`;
  statusRestore.textContent = `Restore: ${formatDate(statusData.backup_last_status.last_restore)}`;
  statusErrors.textContent = `Errors: ${statusData.error_count}`;

  const backupFailed = statusData.backup_last_status.status === 'failed';
  const needsAttention = statusData.error_count > 0 || !statusData.db_encrypted || healthData.status !== 'ok' || backupFailed;
  if (needsAttention) {
    statusHealth.textContent = 'Attention needed';
    statusSummary.textContent = `Action required · Updated ${updatedAt}`;
    if (backupFailed) {
      setBanner('error', 'Backup failed. Run backup now from Status.');
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
  await fetch('/api/status/actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'run_backup' }),
  });
  loadStatus();
});
