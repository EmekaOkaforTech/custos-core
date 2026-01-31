/**
 * People Page (Epic 32 Enhanced)
 *
 * Features:
 * - List all people with role/tag/type filters
 * - Person cards with profile links
 * - Timeline view for selected person
 * - Continuity view (open commitments)
 * - Context-aware terminology
 */

import {
  SEED_BANNER_COPY,
  apiUrl,
  formatDate,
  getApiHeaders,
  getTerminology,
  isSeedIdentifier,
  setDemoMode,
} from './ui-state.js';
import { initCapture } from './capture.js';

// DOM Elements
const peopleList = document.getElementById('people-list');
const timeline = document.getElementById('timeline');
const peopleStatus = document.getElementById('people-status');
const peopleBanner = document.getElementById('people-banner');
const demoBadge = document.getElementById('demo-badge');
const offlineBadge = document.getElementById('offline-badge');

// Filter elements
const filterRole = document.getElementById('filter-role');
const filterTag = document.getElementById('filter-tag');
const filterType = document.getElementById('filter-type');
const clearFiltersBtn = document.getElementById('clear-filters');

// Timeline/Continuity elements
const timelineSection = document.getElementById('timeline-section');
const timelineHeading = document.getElementById('timeline-heading');
const viewProfileLink = document.getElementById('view-profile-link');
const continuitySection = document.getElementById('continuity-section');
const continuityHeading = document.getElementById('continuity-heading');
const continuityList = document.getElementById('continuity-list');

// State
let currentPersonId = null;
let selectedCard = null;
let allPeople = [];
let allRoles = new Set();
let allTags = new Set();

// ============================================================================
// Utilities
// ============================================================================

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

function updateTerminology() {
  const terms = getTerminology();

  // Update page title
  const briefTitle = document.querySelector('.brief-title');
  if (briefTitle) {
    briefTitle.textContent = terms.people;
  }

  // Update headings
  if (continuityHeading) {
    continuityHeading.textContent = `Open ${terms.commitments}`;
  }
}

// ============================================================================
// Filter Management
// ============================================================================

function populateFilterOptions() {
  // Populate role filter
  if (filterRole) {
    const currentRole = filterRole.value;
    filterRole.innerHTML = '<option value="">All roles</option>';
    [...allRoles].sort().forEach(role => {
      const option = document.createElement('option');
      option.value = role;
      option.textContent = role;
      filterRole.appendChild(option);
    });
    filterRole.value = currentRole;
  }

  // Populate tag filter
  if (filterTag) {
    const currentTag = filterTag.value;
    filterTag.innerHTML = '<option value="">All tags</option>';
    [...allTags].sort().forEach(tag => {
      const option = document.createElement('option');
      option.value = tag;
      option.textContent = tag;
      filterTag.appendChild(option);
    });
    filterTag.value = currentTag;
  }
}

function getFilterParams() {
  const params = new URLSearchParams();

  if (filterRole?.value) {
    params.set('role', filterRole.value);
  }
  if (filterTag?.value) {
    params.set('tag', filterTag.value);
  }
  if (filterType?.value) {
    params.set('type', filterType.value);
  }

  return params.toString();
}

function clearFilters() {
  if (filterRole) filterRole.value = '';
  if (filterTag) filterTag.value = '';
  if (filterType) filterType.value = '';
  loadPeople();
}

// ============================================================================
// Person Card Rendering
// ============================================================================

function renderPerson(person) {
  const terms = getTerminology();
  const card = document.createElement('div');
  card.className = 'card person-card';
  card.dataset.personId = person.id;

  // Header row with name and profile link
  const header = document.createElement('div');
  header.className = 'person-card-header';

  const title = document.createElement('h2');
  title.className = 'person-name';
  title.textContent = person.name;

  const profileLink = document.createElement('a');
  profileLink.className = 'button-link profile-link';
  profileLink.href = `person.html?id=${encodeURIComponent(person.id)}`;
  profileLink.textContent = 'Profile →';
  profileLink.addEventListener('click', (e) => e.stopPropagation());

  header.appendChild(title);
  header.appendChild(profileLink);

  // Meta info (type, role, last interaction)
  const meta = document.createElement('div');
  meta.className = 'person-meta';

  const typeLabel = person.type === 'org' ? 'Organization' : terms.person;
  const typeBadge = document.createElement('span');
  typeBadge.className = 'type-badge';
  typeBadge.textContent = typeLabel;
  meta.appendChild(typeBadge);

  if (person.role) {
    const roleBadge = document.createElement('span');
    roleBadge.className = 'role-badge';
    roleBadge.textContent = person.role;
    meta.appendChild(roleBadge);
  }

  // Tags
  if (person.tags && person.tags.length > 0) {
    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'person-tags-inline';
    person.tags.forEach(tag => {
      const tagSpan = document.createElement('span');
      tagSpan.className = 'tag-chip-small';
      tagSpan.textContent = tag;
      tagsContainer.appendChild(tagSpan);
    });
    meta.appendChild(tagsContainer);
  }

  // Last interaction
  const lastInteraction = document.createElement('p');
  lastInteraction.className = 'muted last-interaction';
  if (person.last_interaction_at) {
    lastInteraction.textContent = `Last interaction: ${formatDate(person.last_interaction_at)}`;
  } else {
    lastInteraction.textContent = 'No interactions recorded';
  }

  // Type selector (inline editing)
  const controls = document.createElement('div');
  controls.className = 'person-controls';

  const typeSelect = document.createElement('select');
  typeSelect.className = 'type-select';
  typeSelect.innerHTML = `
    <option value="person">${terms.person}</option>
    <option value="org">Organization</option>
  `;
  typeSelect.value = person.type === 'org' ? 'org' : 'person';

  const saveButton = document.createElement('button');
  saveButton.type = 'button';
  saveButton.className = 'button-link';
  saveButton.textContent = 'Update type';

  controls.appendChild(typeSelect);
  controls.appendChild(saveButton);

  // Prevent click propagation on controls
  controls.addEventListener('click', e => e.stopPropagation());

  saveButton.addEventListener('click', async (e) => {
    e.stopPropagation();
    const newType = typeSelect.value;
    if (newType === person.type) return;

    saveButton.disabled = true;
    saveButton.textContent = 'Saving...';

    try {
      const response = await fetch(apiUrl(`/api/people/${person.id}`), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getApiHeaders(),
        },
        body: JSON.stringify({ type: newType }),
      });

      if (response.ok) {
        person.type = newType;
        typeBadge.textContent = newType === 'org' ? 'Organization' : terms.person;
        peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
      } else {
        peopleStatus.textContent = 'Unable to update type';
      }
    } catch (error) {
      console.error('Error updating type:', error);
      peopleStatus.textContent = 'Error updating type';
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = 'Update type';
    }
  });

  // Assemble card
  card.appendChild(header);
  card.appendChild(meta);
  card.appendChild(lastInteraction);
  card.appendChild(controls);

  // Click to load timeline
  card.addEventListener('click', () => selectPerson(person.id));

  return card;
}

// ============================================================================
// Timeline Rendering
// ============================================================================

function renderTimelineEntry(entry) {
  const terms = getTerminology();
  const card = document.createElement('div');
  card.className = 'card timeline-entry';

  // Distinguish direct notes from meeting-based entries
  if (entry.source_type === 'direct') {
    card.classList.add('direct-note');
  }

  const title = document.createElement('h4');
  if (entry.source_type === 'direct') {
    title.textContent = 'Direct note';
  } else {
    title.textContent = entry.meeting_title || terms.meeting;
  }

  const meta = document.createElement('p');
  meta.className = 'muted';

  if (entry.source_type === 'meeting' && entry.meeting_starts_at) {
    meta.textContent = `${terms.meeting} at ${formatDate(entry.meeting_starts_at)}`;
  } else {
    meta.textContent = `Captured at ${formatDate(entry.occurred_at)}`;
  }

  const typeInfo = document.createElement('p');
  typeInfo.className = 'muted capture-type';
  typeInfo.textContent = entry.capture_type || 'notes';

  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(typeInfo);

  // Remove from person button (only for meeting-based entries)
  if (entry.meeting_id && entry.source_type !== 'direct') {
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'button-link remove-entry';
    removeBtn.textContent = 'Remove from timeline';
    removeBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await removeTimelineEntry(entry.meeting_id);
    });
    card.appendChild(removeBtn);
  }

  return card;
}

async function removeTimelineEntry(meetingId) {
  if (!currentPersonId || !meetingId) return;

  try {
    const response = await fetch(
      apiUrl(`/api/people/${currentPersonId}/timeline/${meetingId}`),
      {
        method: 'DELETE',
        headers: getApiHeaders(),
      }
    );

    if (response.ok) {
      peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;
      loadTimeline(currentPersonId);
    } else {
      peopleStatus.textContent = 'Unable to remove entry';
    }
  } catch (error) {
    console.error('Error removing timeline entry:', error);
    peopleStatus.textContent = 'Error removing entry';
  }
}

// ============================================================================
// Continuity Rendering
// ============================================================================

function renderContinuityItem(item) {
  const terms = getTerminology();
  const card = document.createElement('div');
  card.className = 'card continuity-item';

  if (item.acknowledged) {
    card.classList.add('acknowledged');
  }

  const title = document.createElement('h4');
  title.textContent = item.text || `${terms.commitment}`;

  const meta = document.createElement('p');
  meta.className = 'muted';

  const parts = [];
  if (item.source_meeting_title) {
    parts.push(`From: ${item.source_meeting_title}`);
  }
  if (item.created_at) {
    parts.push(`Created: ${formatDate(item.created_at)}`);
  }
  if (item.relevant_by) {
    parts.push(`Due: ${formatDate(item.relevant_by)}`);
  }
  meta.textContent = parts.join(' · ');

  const status = document.createElement('span');
  status.className = item.acknowledged ? 'status-badge acknowledged' : 'status-badge open';
  status.textContent = item.acknowledged ? 'Acknowledged' : 'Open';

  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(status);

  return card;
}

// ============================================================================
// Data Loading
// ============================================================================

async function loadPeople() {
  try {
    const filterParams = getFilterParams();
    const url = filterParams
      ? apiUrl(`/api/people?${filterParams}`)
      : apiUrl('/api/people');

    const response = await fetch(url, { headers: getApiHeaders() });

    if (!response.ok) {
      throw new Error('Failed to load people');
    }

    const data = await response.json();
    allPeople = data;

    // Collect all roles and tags for filter dropdowns
    data.forEach(person => {
      if (person.role) allRoles.add(person.role);
      if (person.tags) person.tags.forEach(tag => allTags.add(tag));
    });

    populateFilterOptions();
    peopleStatus.textContent = `Updated ${formatDate(new Date().toISOString())}`;

    // Check for seed data
    const hasSeedPeople = data.some(person => isSeedIdentifier(person.id));
    setBanner(hasSeedPeople ? SEED_BANNER_COPY : '');
    setDemoMode(hasSeedPeople);
    setDemoBadge(hasSeedPeople);

    // Render people list
    if (!peopleList) return;
    peopleList.innerHTML = '';

    if (!data.length) {
      const terms = getTerminology();
      peopleList.innerHTML = `<div class="card"><p class="muted">No ${terms.people.toLowerCase()} found matching filters.</p></div>`;
      hideTimelineSection();
      return;
    }

    data.forEach(person => peopleList.appendChild(renderPerson(person)));

    // Auto-select first person if none selected or selected no longer exists
    const stillExists = currentPersonId && data.some(p => p.id === currentPersonId);
    if (!stillExists && data.length > 0) {
      selectPerson(data[0].id);
    } else if (stillExists) {
      selectPerson(currentPersonId);
    }
  } catch (error) {
    console.error('Error loading people:', error);
    peopleStatus.textContent = 'Error loading people';
  }
}

async function selectPerson(personId) {
  currentPersonId = personId;

  // Update card selection
  if (selectedCard) {
    selectedCard.classList.remove('selected');
  }
  const nextSelected = peopleList?.querySelector(`[data-person-id="${personId}"]`);
  if (nextSelected) {
    nextSelected.classList.add('selected');
    selectedCard = nextSelected;
  }

  // Update profile link
  if (viewProfileLink) {
    viewProfileLink.href = `person.html?id=${encodeURIComponent(personId)}`;
    viewProfileLink.classList.remove('hidden');
  }

  // Load timeline and continuity in parallel
  await Promise.all([
    loadTimeline(personId),
    loadContinuity(personId),
  ]);
}

async function loadTimeline(personId) {
  if (!timeline) return;

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/timeline`), {
      headers: getApiHeaders(),
    });

    if (!response.ok) {
      timeline.innerHTML = '<div class="card"><p class="muted">Unable to load timeline.</p></div>';
      return;
    }

    const data = await response.json();
    timeline.innerHTML = '';

    if (!data.timeline || !data.timeline.length) {
      timeline.innerHTML = '<div class="card"><p class="muted">No timeline entries yet.</p></div>';
      return;
    }

    // Render up to 10 most recent entries
    data.timeline.slice(0, 10).forEach(entry => {
      timeline.appendChild(renderTimelineEntry(entry));
    });
  } catch (error) {
    console.error('Error loading timeline:', error);
    timeline.innerHTML = '<div class="card"><p class="muted">Error loading timeline.</p></div>';
  }
}

async function loadContinuity(personId) {
  if (!continuitySection || !continuityList) return;

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/continuity`), {
      headers: getApiHeaders(),
    });

    if (!response.ok) {
      continuitySection.classList.add('hidden');
      return;
    }

    const data = await response.json();

    if (!data.commitments || data.commitments.length === 0) {
      continuitySection.classList.add('hidden');
      return;
    }

    continuityList.innerHTML = '';
    data.commitments.forEach(item => {
      continuityList.appendChild(renderContinuityItem(item));
    });
    continuitySection.classList.remove('hidden');
  } catch (error) {
    console.error('Error loading continuity:', error);
    continuitySection.classList.add('hidden');
  }
}

function hideTimelineSection() {
  if (timelineSection) {
    timelineSection.classList.add('hidden');
  }
  if (continuitySection) {
    continuitySection.classList.add('hidden');
  }
  if (viewProfileLink) {
    viewProfileLink.classList.add('hidden');
  }
}

// ============================================================================
// Event Listeners
// ============================================================================

filterRole?.addEventListener('change', loadPeople);
filterTag?.addEventListener('change', loadPeople);
filterType?.addEventListener('change', loadPeople);
clearFiltersBtn?.addEventListener('click', clearFilters);

// ============================================================================
// Offline Indicator
// ============================================================================

function updateOfflineIndicator() {
  if (!offlineBadge) return;
  const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
  offlineBadge.classList.toggle('hidden', !isOffline);
}

window.addEventListener('online', () => {
  updateOfflineIndicator();
  loadPeople().catch(() => {});
});

window.addEventListener('offline', updateOfflineIndicator);

// ============================================================================
// Initialize
// ============================================================================

updateTerminology();
updateOfflineIndicator();
loadPeople();
initCapture({ onSuccess: loadPeople });
