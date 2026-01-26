import {
  SEED_BANNER_COPY,
  apiUrl,
  computeBriefMeta,
  formatDate,
  getApiHeaders,
  getApiBase,
  getReflectionCloseout,
  isSeedIdentifier,
  isSetupComplete,
  setBriefingCache,
  setApiBase,
  setDemoMode,
  setReflectionCloseout,
  setSetupComplete,
  statusLabel,
} from './ui-state.js';
import { initCapture } from './capture.js';

const briefTitle = document.getElementById('brief-title');
const briefTimer = document.getElementById('brief-timer');
const briefStatus = document.getElementById('brief-status');
const briefOffline = document.getElementById('brief-offline');
const briefAttention = document.getElementById('brief-attention');
const statusLink = document.getElementById('status-link');
const briefBanner = document.getElementById('brief-banner');
const setupBanner = document.getElementById('setup-banner');
const setupApiBase = document.getElementById('setup-api-base');
const setupConnect = document.getElementById('setup-connect');
const setupError = document.getElementById('setup-error');
const briefCards = document.getElementById('brief-cards');
const commitmentsSection = document.getElementById('commitments');
const decisionLogSection = document.getElementById('decision-log-section');
const decisionLogCards = document.getElementById('decision-log');
const futureRelevantSection = document.getElementById('future-relevant-section');
const futureRelevantList = document.getElementById('future-relevant');
const memorySection = document.getElementById('memory-section');
const memoryCards = document.getElementById('memory-cards');
const memoryToggle = document.getElementById('memory-toggle');
const memoryCollapsedNote = document.getElementById('memory-collapsed-note');
const recentCapturesSection = document.getElementById('recent-captures');
const todaySection = document.getElementById('today');
const demoBadge = document.getElementById('demo-badge');
const whyModal = document.getElementById('why-modal');
const whyClose = document.getElementById('why-close');
const whyMeeting = document.getElementById('why-meeting');
const whySource = document.getElementById('why-source');
const whyPeople = document.getElementById('why-people');
const whyRule = document.getElementById('why-rule');
const reflectionSummary = document.getElementById('reflection-summary');
const reflectionCloseout = document.getElementById('reflection-closeout');
const reflectionClosed = document.getElementById('reflection-closed');
const reflectionCards = document.getElementById('reflection-cards');
const meetingRenameOpen = document.getElementById('meeting-rename-open');
const meetingRenameModal = document.getElementById('meeting-rename-modal');
const meetingRenameClose = document.getElementById('meeting-rename-close');
const meetingRenameForm = document.getElementById('meeting-rename-form');
const meetingRenameInput = document.getElementById('meeting-rename-input');
const meetingRenameStatus = document.getElementById('meeting-rename-status');
const recentCapturesToggle = document.getElementById('recent-captures-toggle');
const captureMoveModal = document.getElementById('capture-move-modal');
const captureMoveClose = document.getElementById('capture-move-close');
const captureMoveForm = document.getElementById('capture-move-form');
const captureMoveSelect = document.getElementById('capture-move-select');
const captureMoveStatus = document.getElementById('capture-move-status');

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

function setDemoBadge(show) {
  if (!demoBadge) return;
  demoBadge.classList.toggle('hidden', !show);
}

let currentMeeting = null;
let showAllCaptures = false;
let captureToMove = null;
let memoryCollapsed = false;

function renderCommitment(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const row = document.createElement('div');
  row.className = 'commitment-row';

  const text = document.createElement('div');
  text.textContent = item.text;

  const editButton = document.createElement('button');
  editButton.className = 'button-link';
  editButton.type = 'button';
  editButton.textContent = 'Relevant by';

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
  const relevantBy = item.due_at ? formatDate(item.due_at) : 'No time intent set';
  meta.textContent = `Created ${created} · Relevant by ${relevantBy}`;

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
      const next = item.due_at ? formatDate(item.due_at) : 'No time intent set';
      meta.textContent = `Created ${created} · Relevant by ${next}`;
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

  row.appendChild(text);
  row.appendChild(editButton);
  row.appendChild(button);
  card.appendChild(row);
  card.appendChild(meta);
  card.appendChild(editRow);
  return card;
}

function renderDecisionLog(items) {
  if (!decisionLogCards) return;
  decisionLogCards.innerHTML = '';
  const now = Date.now();
  const cutoff = new Date(now - 7 * 24 * 60 * 60 * 1000);
  const decisions = (items || [])
    .filter(item => item.capture_type === 'decision')
    .filter(item => !item.captured_at || new Date(item.captured_at) >= cutoff)
    .sort((a, b) => new Date(b.captured_at) - new Date(a.captured_at))
    .slice(0, 5);

  if (!decisions.length) {
    decisionLogCards.innerHTML = '<div class="card"><p class="muted">No decision records yet.</p></div>';
    return;
  }

  const grouped = new Map();
  decisions.forEach(item => {
    const title = item.meeting?.title || 'Context';
    if (!grouped.has(title)) grouped.set(title, []);
    grouped.get(title).push(item);
  });

  grouped.forEach((group, title) => {
    const card = document.createElement('article');
    card.className = 'card';
    const heading = document.createElement('h4');
    heading.textContent = title;
    card.appendChild(heading);
    group.forEach(entry => {
      const payload = entry.payload || entry.excerpt || 'Decision captured.';
      const excerpt = document.createElement('p');
      excerpt.textContent = payload.length > 200 ? `${payload.slice(0, 197)}…` : payload;
      const meta = document.createElement('p');
      meta.className = 'muted';
      meta.textContent = entry.captured_at ? formatDate(entry.captured_at) : 'Date unavailable';
      card.appendChild(excerpt);
      card.appendChild(meta);
    });
    decisionLogCards.appendChild(card);
  });
}

function renderRecentCapture(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const header = document.createElement('div');
  header.className = 'commitment-row';
  const title = document.createElement('h4');
  title.textContent = `${item.meeting?.title || 'Meeting'} · ${item.capture_type}`;
  const moveButton = document.createElement('button');
  moveButton.className = 'button-link';
  moveButton.type = 'button';
  moveButton.textContent = 'Move';
  moveButton.addEventListener('click', () => {
    if (!item.source_id) return;
    openMoveModal(item);
  });
  if (!item.source_id) {
    moveButton.disabled = true;
  }
  header.appendChild(title);
  header.appendChild(moveButton);
  const when = document.createElement('p');
  when.className = 'muted';
  when.textContent = formatDate(item.captured_at) || 'recent';
  const body = document.createElement('p');
  body.textContent = item.payload;
  card.appendChild(header);
  card.appendChild(when);
  card.appendChild(body);
  return card;
}

function renderRecentCaptures(items) {
  if (!recentCapturesSection) return;
  recentCapturesSection.innerHTML = '';
  if (Array.isArray(items) && items.length) {
    const list = showAllCaptures ? items : items.slice(0, 2);
    list.forEach(item => recentCapturesSection.appendChild(renderRecentCapture(item)));
  } else {
    recentCapturesSection.innerHTML = '<div class="card"><p class="muted">No recent captures yet.</p></div>';
  }
}

function renderReflections(items) {
  if (!reflectionCards) return;
  reflectionCards.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    reflectionCards.innerHTML = '<div class="card"><p class="muted">No reflections captured yet.</p></div>';
    return;
  }
  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = document.createElement('h4');
    title.textContent = item.meeting?.title || 'Reflection';
    const when = document.createElement('p');
    when.className = 'muted';
    when.textContent = item.captured_at ? `Captured ${formatDate(item.captured_at)}` : 'Captured recently';
    const text = document.createElement('p');
    const payload = item.payload?.trim() || 'No reflection text available.';
    text.textContent = payload.length > 200 ? `${payload.slice(0, 197)}…` : payload;
    card.appendChild(title);
    card.appendChild(when);
    card.appendChild(text);
    reflectionCards.appendChild(card);
  });
}

function renderFutureRelevant(items) {
  if (!futureRelevantSection || !futureRelevantList) return;
  futureRelevantList.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    futureRelevantSection.classList.add('hidden');
    return;
  }
  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = document.createElement('h4');
    title.textContent = item.meeting?.title || 'Context';
    const meta = document.createElement('p');
    meta.className = 'muted';
    const relevant = item.relevant_at ? formatDate(item.relevant_at) : 'unspecified';
    const captured = item.captured_at ? formatDate(item.captured_at) : 'unknown';
    meta.textContent = `Relevant when: ${relevant} · Marked on ${captured}`;
    const note = document.createElement('p');
    note.className = 'muted';
    note.textContent = 'Shown because there is no upcoming context.';
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(note);
    futureRelevantList.appendChild(card);
  });
  futureRelevantSection.classList.remove('hidden');
}

function renderMemory(items) {
  if (!memoryCards) return;
  memoryCards.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    memoryCards.innerHTML = '<div class="card"><p class="muted">No memory surfaced yet.</p></div>';
    return;
  }
  const list = items.slice(0, 3);
  list.forEach(item => {
    const card = document.createElement('div');
    card.className = 'card';
    const title = document.createElement('h4');
    title.textContent = item.meeting_title || 'Context';
    const meta = document.createElement('p');
    meta.className = 'muted';
    const captured = item.captured_at ? formatDate(item.captured_at) : 'unknown';
    meta.textContent = `Captured ${captured} · ${item.capture_type || 'context'}`;
    const why = document.createElement('p');
    why.className = 'muted';
    why.textContent = 'Why: matched your most recent reflection.';
    const excerpt = document.createElement('p');
    excerpt.textContent = item.excerpt || 'No capture excerpt available.';
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(why);
    card.appendChild(excerpt);
    memoryCards.appendChild(card);
  });
}

function applyMemoryCollapseState(hasNextContext) {
  if (!memoryCards || !memoryToggle || !memoryCollapsedNote) return;
  memoryCollapsed = hasNextContext ? true : false;
  memoryCards.classList.toggle('hidden', memoryCollapsed);
  memoryCollapsedNote.classList.toggle('hidden', !hasNextContext || !memoryCollapsed);
  memoryToggle.textContent = memoryCollapsed ? 'Show' : 'Hide';
}

function openWhyModal(reason) {
  if (!whyModal || !reason) return;
  const meetingTitle = reason.meeting?.title || 'Meeting';
  const meetingTime = reason.meeting?.starts_at ? formatDate(reason.meeting.starts_at) : 'time unknown';
  if (whyMeeting) {
    whyMeeting.textContent = `${meetingTitle} · ${meetingTime}`;
  }
  if (whySource) {
    if (reason.source) {
      whySource.textContent = `Source: ${reason.source.capture_type || 'notes'} captured ${formatDate(reason.source.captured_at)}`;
    } else {
      whySource.textContent = 'Source: none yet';
    }
  }
  if (whyPeople) {
    const names = (reason.people || []).map(person => person.name).filter(Boolean);
    whyPeople.textContent = names.length ? `People: ${names.join(', ')}` : 'People: none linked';
  }
  if (whyRule) {
    const ruleId = reason.rule?.id || 'unknown';
    const ruleType = reason.rule?.type || 'unknown';
    whyRule.textContent = `Rule: ${ruleId} (${ruleType})`;
  }
  whyModal.classList.add('open');
  whyModal.setAttribute('aria-hidden', 'false');
}

function closeWhyModal() {
  if (!whyModal) return;
  whyModal.classList.remove('open');
  whyModal.setAttribute('aria-hidden', 'true');
}

function renderTodayMeeting(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const title = document.createElement('h2');
  title.textContent = item.title;
  const rename = document.createElement('button');
  rename.className = 'button-link';
  rename.type = 'button';
  rename.textContent = 'Rename';
  rename.addEventListener('click', () => openMeetingRename(item));
  const time = document.createElement('p');
  time.textContent = `Context starts ${formatDate(item.starts_at)}`;
  const statusRow = document.createElement('div');
  statusRow.className = 'status-row';
  const pill = document.createElement('span');
  pill.className = 'status-pill';
  pill.dataset.state = item.status;
  pill.title = item.last_source_at ? formatDate(item.last_source_at) : 'No source available';
  pill.textContent = statusLabel(item.status, item.last_source_at);
  statusRow.appendChild(pill);
  const row = document.createElement('div');
  row.className = 'commitment-row';
  row.appendChild(title);
  row.appendChild(rename);
  card.appendChild(row);
  card.appendChild(time);
  card.appendChild(statusRow);
  return card;
}

function renderEmptyState() {
  const card = document.createElement('div');
  card.className = 'card';
  const title = document.createElement('h2');
  title.textContent = 'No upcoming context';
  const text = document.createElement('p');
  text.className = 'muted';
  text.textContent = 'Create a context entry to start capturing notes or connect your calendar.';
  const actions = document.createElement('div');
  actions.className = 'empty-actions';

  const createButton = document.createElement('button');
  createButton.className = 'button-link';
  createButton.id = 'empty-create';
  createButton.type = 'button';
  createButton.setAttribute('aria-label', 'Create a new context entry');
  createButton.textContent = 'Create context';
  createButton.addEventListener('click', () => {
    const captureButton = document.getElementById('capture-open');
    if (captureButton) {
      captureButton.click();
    } else {
      window.location.href = 'status.html';
    }
  });

  const importLink = document.createElement('a');
  importLink.className = 'button-link';
  importLink.id = 'empty-import';
  importLink.href = 'status.html';
  importLink.setAttribute('aria-label', 'Import calendar');
  importLink.textContent = 'Import calendar';

  actions.appendChild(createButton);
  actions.appendChild(importLink);
  card.appendChild(title);
  card.appendChild(text);
  card.appendChild(actions);
  return card;
}

function showSetupBanner(show) {
  if (!setupBanner) return;
  setupBanner.style.display = show ? 'block' : 'none';
  if (!show) {
    setupError.textContent = '';
  }
}

if (whyClose) {
  whyClose.addEventListener('click', closeWhyModal);
}
if (whyModal) {
  whyModal.addEventListener('click', event => {
    if (event.target && event.target.hasAttribute('data-why-close')) {
      closeWhyModal();
    }
  });
}

async function verifySetup(apiBase) {
  try {
    const response = await fetch(`${apiBase}/api/health`);
    if (!response.ok) {
      throw new Error('Health check failed');
    }
    setApiBase(apiBase);
    setSetupComplete(true);
    showSetupBanner(false);
    loadBriefings();
  } catch (err) {
    showSetupBanner(true);
    setupError.textContent = 'Unable to connect. Please check the URL and try again.';
  }
}

function renderReflection(todayData) {
  if (!reflectionSummary) return;
  const meetings = Array.isArray(todayData?.meetings) ? todayData.meetings : [];
  const commitments = Array.isArray(todayData?.commitments) ? todayData.commitments : [];
  const meetingCount = meetings.length;
  const commitmentCount = commitments.length;
  reflectionSummary.textContent = `Today: ${meetingCount} meeting${meetingCount === 1 ? '' : 's'}, ${commitmentCount} commitment${commitmentCount === 1 ? '' : 's'}.`;
  const closed = getReflectionCloseout();
  const today = new Date().toISOString().slice(0, 10);
  const isClosed = closed === today;
  if (reflectionClosed && reflectionCloseout) {
    reflectionClosed.classList.toggle('hidden', !isClosed);
    reflectionCloseout.classList.toggle('hidden', isClosed);
  }
}

if (reflectionCloseout) {
  reflectionCloseout.addEventListener('click', () => {
    const today = new Date().toISOString().slice(0, 10);
    setReflectionCloseout(today);
    if (reflectionClosed) {
      reflectionClosed.classList.remove('hidden');
    }
    reflectionCloseout.classList.add('hidden');
  });
}

function setMeetingRenameOpen(open) {
  if (!meetingRenameModal) return;
  meetingRenameModal.classList.toggle('open', open);
  meetingRenameModal.setAttribute('aria-hidden', open ? 'false' : 'true');
  if (!open && meetingRenameStatus) {
    meetingRenameStatus.textContent = '';
  }
}

function openMeetingRename(meeting) {
  currentMeeting = meeting;
  if (meetingRenameInput) {
    meetingRenameInput.value = meeting?.title || '';
    meetingRenameInput.focus();
  }
  setMeetingRenameOpen(true);
}

async function submitMeetingRename(event) {
  event.preventDefault();
  if (!currentMeeting) return;
  const title = meetingRenameInput?.value?.trim() || '';
  if (!title) {
    if (meetingRenameStatus) {
      meetingRenameStatus.textContent = 'Enter a meeting name to continue.';
    }
    return;
  }
  const response = await fetch(apiUrl(`/api/meetings/${currentMeeting.id}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    if (meetingRenameStatus) {
      meetingRenameStatus.textContent = 'Unable to rename meeting. Try again.';
    }
    return;
  }
  setMeetingRenameOpen(false);
  await loadBriefings();
}

function setMoveModalOpen(open) {
  if (!captureMoveModal) return;
  captureMoveModal.classList.toggle('open', open);
  captureMoveModal.setAttribute('aria-hidden', open ? 'false' : 'true');
  if (!open && captureMoveStatus) {
    captureMoveStatus.textContent = '';
  }
}

async function loadMoveMeetingOptions(currentId) {
  if (!captureMoveSelect) return;
  const [todayRes, upcomingRes] = await Promise.all([
    fetch(apiUrl('/api/meetings?range=today'), { headers: getApiHeaders() }),
    fetch(apiUrl('/api/meetings?range=upcoming'), { headers: getApiHeaders() }),
  ]);
  const options = [];
  if (todayRes.ok) {
    const data = await todayRes.json();
    options.push(...(data.meetings || []));
  }
  if (upcomingRes.ok) {
    const data = await upcomingRes.json();
    options.push(...(data.meetings || []));
  }
  const seen = new Set();
  captureMoveSelect.innerHTML = '';
  options.forEach(meeting => {
    if (!meeting?.id || seen.has(meeting.id)) return;
    seen.add(meeting.id);
    const option = document.createElement('option');
    option.value = meeting.id;
    option.textContent = meeting.title;
    captureMoveSelect.appendChild(option);
  });
  if (currentId) {
    captureMoveSelect.value = currentId;
  }
}

function openMoveModal(capture) {
  captureToMove = capture;
  void loadMoveMeetingOptions(capture.meeting?.id);
  setMoveModalOpen(true);
}

async function submitMoveCapture(event) {
  event.preventDefault();
  if (!captureToMove || !captureMoveSelect) return;
  const meetingId = captureMoveSelect.value;
  if (!meetingId) {
    if (captureMoveStatus) {
      captureMoveStatus.textContent = 'Select a meeting to move this capture.';
    }
    return;
  }
  const response = await fetch(apiUrl(`/api/sources/${captureToMove.source_id}/move`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
    body: JSON.stringify({ meeting_id: meetingId }),
  });
  if (!response.ok) {
    if (captureMoveStatus) {
      captureMoveStatus.textContent = 'Unable to move capture. Try again.';
    }
    return;
  }
  setMoveModalOpen(false);
  await loadBriefings();
}

async function loadBriefings() {
  const base = getApiBase();
  if (!base || !isSetupComplete()) {
    showSetupBanner(true);
    return;
  }
  const nextResponse = await fetch(apiUrl('/api/briefings/next'), { headers: getApiHeaders() });
  const nextData = await nextResponse.json();
  setBriefingCache({ next: nextData, today: null });
  const hasSeedSource = nextData.cards?.some(card => card.source && isSeedIdentifier(card.source.uri));
  setBanner('info', hasSeedSource ? SEED_BANNER_COPY : '');
  setDemoMode(Boolean(hasSeedSource));
  setDemoBadge(Boolean(hasSeedSource));

  const meta = computeBriefMeta({
    cached: nextData.cached,
    offline: nextData.offline,
    updatedAt: nextData.updated_at,
  });
  briefStatus.textContent = meta.statusText;
  briefOffline.classList.toggle('hidden', !meta.showOffline);

  if (!nextData.meeting) {
    briefCards.innerHTML = '';
    briefCards.appendChild(renderEmptyState());
    currentMeeting = null;
    if (meetingRenameOpen) {
      meetingRenameOpen.disabled = true;
    }
    renderFutureRelevant(nextData.future_relevant || []);
  } else {
    currentMeeting = nextData.meeting;
    if (meetingRenameOpen) {
      meetingRenameOpen.disabled = false;
    }
    briefTitle.textContent = `Context brief — ${nextData.meeting.title}`;
    briefTimer.textContent = `Next context ${formatDate(nextData.meeting.starts_at)}`;
    briefCards.innerHTML = '';
    nextData.cards.forEach(card => {
      const container = document.createElement('article');
      container.className = 'card';
      const title = document.createElement('h2');
      title.textContent = nextData.meeting.title;
      const summary = document.createElement('p');
      summary.textContent = card.summary;
      const whyButton = document.createElement('button');
      whyButton.className = 'button-link';
      whyButton.type = 'button';
      whyButton.textContent = 'Why am I seeing this?';
      whyButton.addEventListener('click', () => openWhyModal(card.reason));
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
      container.appendChild(whyButton);
      container.appendChild(statusRow);
      briefCards.appendChild(container);
    });
    if (futureRelevantSection) {
      futureRelevantSection.classList.add('hidden');
    }
  }

  commitmentsSection.innerHTML = '';
  if (nextData.commitments && nextData.commitments.length) {
    nextData.commitments.forEach(item => commitmentsSection.appendChild(renderCommitment(item)));
  } else {
    commitmentsSection.innerHTML = '<div class="card"><p class="muted">No open commitments.</p></div>';
  }

  const todayResponse = await fetch(apiUrl('/api/briefings/today'), { headers: getApiHeaders() });
  const todayData = await todayResponse.json();
  setBriefingCache({ next: nextData, today: todayData });
  todaySection.innerHTML = '';
  if (todayData.meetings.length) {
    todayData.meetings.forEach(item => todaySection.appendChild(renderTodayMeeting(item)));
  } else {
    todaySection.innerHTML = '<div class="card"><p class="muted">No meetings scheduled for today.</p></div>';
  }
  renderReflection(todayData);

  const recentResponse = await fetch(apiUrl('/api/ingestion/recent?limit=10'), { headers: getApiHeaders() });
  if (recentResponse.ok) {
    const recentData = await recentResponse.json();
    renderRecentCaptures(recentData);
    renderReflections((recentData || []).filter(item => item.capture_type === 'reflection'));
    const decisionResponse = await fetch(apiUrl('/api/ingestion/recent?limit=50'), { headers: getApiHeaders() });
    if (decisionResponse.ok) {
      const decisionData = await decisionResponse.json();
      renderDecisionLog(decisionData);
    } else {
      renderDecisionLog(recentData);
    }
    if (recentCapturesToggle) {
      recentCapturesToggle.classList.toggle('hidden', recentData.length <= 2);
      recentCapturesToggle.textContent = showAllCaptures ? 'Show less' : 'View all';
    }
  } else {
    renderRecentCaptures([]);
    renderReflections([]);
    renderDecisionLog([]);
    if (recentCapturesToggle) {
      recentCapturesToggle.classList.add('hidden');
    }
  }

  const memoryResponse = await fetch(apiUrl('/api/memory/surface'), { headers: getApiHeaders() });
  if (memoryResponse.ok) {
    const memoryData = await memoryResponse.json();
    renderMemory(memoryData.items || []);
  } else {
    renderMemory([]);
  }
  applyMemoryCollapseState(Boolean(nextData.meeting));

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

if (setupConnect) {
  setupConnect.addEventListener('click', () => {
    const value = setupApiBase?.value?.trim() || '';
    if (!value) {
      setupError.textContent = 'Enter the backend URL to continue.';
      showSetupBanner(true);
      return;
    }
    verifySetup(value);
  });
}

if (setupApiBase) {
  const storedBase = getApiBase();
  if (storedBase) {
    setupApiBase.value = storedBase;
  }
}

loadBriefings().catch(() => {
  setBanner('error', 'Unable to load briefings. Check local connectivity.');
  renderReflection({ meetings: [], commitments: [] });
  renderRecentCaptures([]);
  renderReflections([]);
  renderMemory([]);
  if (recentCapturesToggle) {
    recentCapturesToggle.classList.add('hidden');
  }
});

initCapture({ onSuccess: loadBriefings });

if (meetingRenameOpen) {
  meetingRenameOpen.addEventListener('click', () => {
    if (currentMeeting) {
      openMeetingRename(currentMeeting);
    }
  });
}
if (meetingRenameForm) {
  meetingRenameForm.addEventListener('submit', submitMeetingRename);
}
if (meetingRenameModal) {
  meetingRenameModal.addEventListener('click', event => {
    if (event.target && event.target.hasAttribute('data-meeting-close')) {
      setMeetingRenameOpen(false);
    }
  });
}
if (meetingRenameClose) {
  meetingRenameClose.addEventListener('click', () => setMeetingRenameOpen(false));
}
if (recentCapturesToggle) {
  recentCapturesToggle.addEventListener('click', () => {
    showAllCaptures = !showAllCaptures;
    recentCapturesToggle.textContent = showAllCaptures ? 'Show less' : 'View all';
    loadBriefings();
  });
}
if (memoryToggle) {
  memoryToggle.addEventListener('click', () => {
    memoryCollapsed = !memoryCollapsed;
    applyMemoryCollapseState(Boolean(currentMeeting));
  });
}
if (captureMoveForm) {
  captureMoveForm.addEventListener('submit', submitMoveCapture);
}
if (captureMoveModal) {
  captureMoveModal.addEventListener('click', event => {
    if (event.target && event.target.hasAttribute('data-move-close')) {
      setMoveModalOpen(false);
    }
  });
}
if (captureMoveClose) {
  captureMoveClose.addEventListener('click', () => setMoveModalOpen(false));
}
