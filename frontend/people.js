import { SEED_BANNER_COPY, apiUrl, formatDate, getApiHeaders, isSeedIdentifier, setDemoMode } from './ui-state.js';
import { initCapture } from './capture.js';

const peopleList = document.getElementById('people-list');
const timeline = document.getElementById('timeline');
const peopleStatus = document.getElementById('people-status');
const peopleBanner = document.getElementById('people-banner');
const demoBadge = document.getElementById('demo-badge');
let currentPersonId = null;
let selectedCard = null;

function setBanner(message) {
  if (!peopleBanner) return;
  if (!message) {
    peopleBanner.style.display = 'none';
    peopleBanner.textContent = '';
    return;
  }
  peopleBanner.style.display = 'block';
  peopleBanner.textContent = message;
}

function setDemoBadge(show) {
  if (!demoBadge) return;
  demoBadge.classList.toggle('hidden', !show);
}

function renderPerson(person) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.personId = person.id;
  const title = document.createElement('h2');
  title.textContent = person.name;
  const meta = document.createElement('p');
  const last = person.last_interaction_at ? formatDate(person.last_interaction_at) : 'No interactions recorded yet.';
  const typeLabel = person.type === 'org' ? 'organization' : 'person';
  meta.textContent = `${typeLabel} · ${last}`;
  meta.title = person.last_interaction_at ? formatDate(person.last_interaction_at) : '';
  const controls = document.createElement('div');
  controls.className = 'tag-input';
  const typeSelect = document.createElement('select');
  const personOption = document.createElement('option');
  personOption.value = 'person';
  personOption.textContent = 'Person';
  const orgOption = document.createElement('option');
  orgOption.value = 'org';
  orgOption.textContent = 'Organization';
  typeSelect.appendChild(personOption);
  typeSelect.appendChild(orgOption);
  typeSelect.value = person.type === 'org' ? 'org' : 'person';
  const saveButton = document.createElement('button');
  saveButton.type = 'button';
  saveButton.className = 'button-link';
  saveButton.textContent = 'Save type';
  controls.appendChild(typeSelect);
  controls.appendChild(saveButton);
  controls.addEventListener('click', event => {
    event.stopPropagation();
  });
  typeSelect.addEventListener('click', event => {
    event.stopPropagation();
  });
  saveButton.addEventListener('click', async event => {
    event.stopPropagation();
    const newType = typeSelect.value;
    if (newType === person.type) {
      return;
    }
    const response = await fetch(apiUrl(`/api/people/${person.id}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: newType }),
    });
    if (!response.ok) {
      peopleStatus.textContent = 'Unable to update person type.';
      return;
    }
    person.type = newType;
    const updatedTypeLabel = newType === 'org' ? 'organization' : 'person';
    meta.textContent = `${updatedTypeLabel} · ${last}`;
    peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
  });
  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(controls);
  card.addEventListener('click', () => loadTimeline(person.id));
  return card;
}

function renderTimelineEntry(entry) {
  const card = document.createElement('div');
  card.className = 'card';
  const title = document.createElement('h2');
  title.textContent = entry.meeting_title;
  const meta = document.createElement('p');
  const when = formatDate(entry.meeting_starts_at);
  meta.textContent = `Occurred at ${when}`;
  meta.title = when;
  const source = document.createElement('div');
  source.className = 'meta';
  if (entry.source_missing) {
    source.textContent = 'Source missing for this interaction.';
  } else {
    source.textContent = `Source: ${entry.source_id}`;
  }
  const controls = document.createElement('div');
  controls.className = 'tag-input';
  const removeButton = document.createElement('button');
  removeButton.type = 'button';
  removeButton.className = 'button-link';
  removeButton.textContent = 'Remove from person';
  removeButton.addEventListener('click', async event => {
    event.stopPropagation();
    if (!currentPersonId || !entry.meeting_id) {
      return;
    }
    const response = await fetch(
      apiUrl(`/api/people/${currentPersonId}/timeline/${entry.meeting_id}`),
      { method: 'DELETE', headers: { ...getApiHeaders() } },
    );
    if (!response.ok) {
      peopleStatus.textContent = 'Unable to remove link.';
      return;
    }
    peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
    loadTimeline(currentPersonId);
  });
  controls.appendChild(removeButton);
  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(source);
  card.appendChild(controls);
  return card;
}

async function loadPeople() {
  const response = await fetch(apiUrl('/api/people'));
  const data = await response.json();
  peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
  const hasSeedPeople = data.some(person => isSeedIdentifier(person.id));
  setBanner(hasSeedPeople ? SEED_BANNER_COPY : '');
  setDemoMode(hasSeedPeople);
  setDemoBadge(hasSeedPeople);
  peopleList.innerHTML = '';
  if (!data.length) {
    peopleList.innerHTML = '<div class="card"><p class="muted">No interactions recorded yet.</p></div>';
    return;
  }
  data.forEach(person => peopleList.appendChild(renderPerson(person)));
  loadTimeline(data[0].id);
}

async function loadTimeline(personId) {
  currentPersonId = personId;
  if (selectedCard) {
    selectedCard.classList.remove('selected');
  }
  const nextSelected = peopleList?.querySelector(`[data-person-id="${personId}"]`);
  if (nextSelected) {
    nextSelected.classList.add('selected');
    selectedCard = nextSelected;
  }
  const response = await fetch(apiUrl(`/api/people/${personId}/timeline`));
  if (!response.ok) {
    timeline.innerHTML = '<div class="card"><p class="muted">No source records available for this period.</p></div>';
    return;
  }
  const data = await response.json();
  timeline.innerHTML = '';
  if (!data.timeline.length) {
    timeline.innerHTML = '<div class="card"><p class="muted">No interactions recorded yet.</p></div>';
    return;
  }
  data.timeline.forEach(entry => timeline.appendChild(renderTimelineEntry(entry)));
}

loadPeople();

initCapture({ onSuccess: loadPeople });
