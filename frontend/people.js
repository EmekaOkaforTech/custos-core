import { formatDate } from './ui-state.js';

const peopleList = document.getElementById('people-list');
const timeline = document.getElementById('timeline');
const peopleStatus = document.getElementById('people-status');

function renderPerson(person) {
  const card = document.createElement('div');
  card.className = 'card';
  const title = document.createElement('h2');
  title.textContent = person.name;
  const meta = document.createElement('p');
  const last = person.last_interaction_at ? formatDate(person.last_interaction_at) : 'No interactions recorded yet.';
  meta.textContent = `${person.type} · ${last}`;
  meta.title = person.last_interaction_at ? formatDate(person.last_interaction_at) : '';
  card.appendChild(title);
  card.appendChild(meta);
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
  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(source);
  return card;
}

async function loadPeople() {
  const response = await fetch('/api/people');
  const data = await response.json();
  peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
  peopleList.innerHTML = '';
  if (!data.length) {
    peopleList.innerHTML = '<div class="card"><p class="muted">No interactions recorded yet.</p></div>';
    return;
  }
  data.forEach(person => peopleList.appendChild(renderPerson(person)));
  loadTimeline(data[0].id);
}

async function loadTimeline(personId) {
  const response = await fetch(`/api/people/${personId}/timeline`);
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
