import { apiUrl, computeBriefMeta, formatDate, getApiHeaders, statusLabel } from './ui-state.js';

const briefTitle = document.getElementById('brief-title');
const briefTimer = document.getElementById('brief-timer');
const briefStatus = document.getElementById('brief-status');
const briefOffline = document.getElementById('brief-offline');
const briefAttention = document.getElementById('brief-attention');
const statusLink = document.getElementById('status-link');
const briefBanner = document.getElementById('brief-banner');
const briefCards = document.getElementById('brief-cards');
const commitmentsSection = document.getElementById('commitments');
const todaySection = document.getElementById('today');

function setBanner(kind, message) {
  if (!message) {
    briefBanner.style.display = 'none';
    briefBanner.textContent = '';
    return;
  }
  briefBanner.style.display = 'block';
  briefBanner.dataset.kind = kind;
  briefBanner.textContent = message;
}

function renderCommitment(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const row = document.createElement('div');
  row.className = 'commitment-row';

  const text = document.createElement('div');
  text.textContent = item.text;

  const button = document.createElement('button');
  button.className = 'button-link';
  button.textContent = item.acknowledged ? 'Undo' : 'Acknowledge';
  button.addEventListener('click', async () => {
    const next = !item.acknowledged;
    const response = await fetch(apiUrl(`/api/commitments/${item.id}/ack`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
      body: JSON.stringify({ acknowledged: next }),
    });
    if (response.ok) {
      item.acknowledged = next;
      button.textContent = next ? 'Undo' : 'Acknowledge';
    }
  });

  const meta = document.createElement('div');
  meta.className = 'commitment-meta';
  const created = formatDate(item.created_at) || 'unknown';
  const due = item.due_at ? formatDate(item.due_at) : 'no due date';
  meta.textContent = `Created ${created} · Due ${due}`;

  row.appendChild(text);
  row.appendChild(button);
  card.appendChild(row);
  card.appendChild(meta);
  return card;
}

function renderTodayMeeting(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const title = document.createElement('h2');
  title.textContent = item.title;
  const time = document.createElement('p');
  time.textContent = `Starts ${formatDate(item.starts_at)}`;
  const statusRow = document.createElement('div');
  statusRow.className = 'status-row';
  const pill = document.createElement('span');
  pill.className = 'status-pill';
  pill.dataset.state = item.status;
  pill.title = item.last_source_at ? formatDate(item.last_source_at) : 'No source available';
  pill.textContent = statusLabel(item.status, item.last_source_at);
  statusRow.appendChild(pill);
  card.appendChild(title);
  card.appendChild(time);
  card.appendChild(statusRow);
  return card;
}

async function loadBriefings() {
  const nextResponse = await fetch(apiUrl('/api/briefings/next'), { headers: getApiHeaders() });
  const nextData = await nextResponse.json();

  const meta = computeBriefMeta({
    cached: nextData.cached,
    offline: nextData.offline,
    updatedAt: nextData.updated_at,
  });
  briefStatus.textContent = meta.statusText;
  briefOffline.classList.toggle('hidden', !meta.showOffline);

  if (!nextData.meeting) {
    briefCards.innerHTML = '<div class="card"><h2>No upcoming meetings</h2><p class="muted">Custos will update when a meeting is scheduled.</p></div>';
  } else {
    briefTitle.textContent = `Pre‑Meeting Brief — ${nextData.meeting.title}`;
    briefTimer.textContent = `Starts ${formatDate(nextData.meeting.starts_at)}`;
    briefCards.innerHTML = '';
    nextData.cards.forEach(card => {
      const container = document.createElement('article');
      container.className = 'card';
      const title = document.createElement('h2');
      title.textContent = nextData.meeting.title;
      const summary = document.createElement('p');
      summary.textContent = card.summary;
      const statusRow = document.createElement('div');
      statusRow.className = 'status-row';
      const pill = document.createElement('span');
      pill.className = 'status-pill';
      pill.dataset.state = card.status;
      pill.title = card.last_source_at ? formatDate(card.last_source_at) : 'No source available';
      pill.textContent = statusLabel(card.status, card.last_source_at);
      statusRow.appendChild(pill);
      container.appendChild(title);
      container.appendChild(summary);
      container.appendChild(statusRow);
      briefCards.appendChild(container);
    });
  }

  commitmentsSection.innerHTML = '';
  if (nextData.commitments && nextData.commitments.length) {
    nextData.commitments.forEach(item => commitmentsSection.appendChild(renderCommitment(item)));
  } else {
    commitmentsSection.innerHTML = '<div class="card"><p class="muted">No open commitments.</p></div>';
  }

  const todayResponse = await fetch(apiUrl('/api/briefings/today'), { headers: getApiHeaders() });
  const todayData = await todayResponse.json();
  todaySection.innerHTML = '';
  if (todayData.meetings.length) {
    todayData.meetings.forEach(item => todaySection.appendChild(renderTodayMeeting(item)));
  } else {
    todaySection.innerHTML = '<div class="card"><p class="muted">No meetings scheduled for today.</p></div>';
  }

  const healthResponse = await fetch(apiUrl('/api/health'), { headers: getApiHeaders() });
  const healthData = await healthResponse.json();
  const statusResponse = await fetch(apiUrl('/api/status'), { headers: getApiHeaders() });
  const statusData = await statusResponse.json();
  const needsAttention = statusData.error_count > 0 || !statusData.db_encrypted || healthData.status !== 'ok';
  if (needsAttention) {
    briefAttention.classList.remove('hidden');
    briefAttention.classList.add('attention');
    statusLink.textContent = 'Status';
  } else {
    briefAttention.classList.add('hidden');
    briefAttention.classList.remove('attention');
  }
}

loadBriefings().catch(() => {
  setBanner('error', 'Unable to load briefings. Check local connectivity.');
});
