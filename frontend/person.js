/**
 * Person Profile Page (Epic 32)
 *
 * Features:
 * - View person profile with role and tags
 * - Edit role
 * - Add/remove tags
 * - Add direct notes
 * - View timeline
 */

import {
  apiUrl,
  formatDate,
  getApiHeaders,
  getCaptureTypes,
  getTerminology,
} from './ui-state.js';

// DOM Elements
const personName = document.getElementById('person-name');
const personType = document.getElementById('person-type');
const personRole = document.getElementById('person-role');
const lastInteraction = document.getElementById('last-interaction');
const personTags = document.getElementById('person-tags');
const recentNotes = document.getElementById('recent-notes');
const timelineStats = document.getElementById('timeline-stats');
const timelinePreview = document.getElementById('timeline-preview');
const editRoleBtn = document.getElementById('edit-role-btn');
const addNoteBtn = document.getElementById('add-note-btn');

// Role Modal
const roleModal = document.getElementById('role-modal');
const closeRoleModal = document.getElementById('close-role-modal');
const cancelRole = document.getElementById('cancel-role');
const submitRole = document.getElementById('submit-role');
const roleInput = document.getElementById('role-input');

// Tag Modal
const tagModal = document.getElementById('tag-modal');
const closeTagModal = document.getElementById('close-tag-modal');
const cancelTag = document.getElementById('cancel-tag');
const submitTag = document.getElementById('submit-tag');
const tagInput = document.getElementById('tag-input');

// Note Modal
const noteModal = document.getElementById('note-modal');
const closeNoteModal = document.getElementById('close-note-modal');
const cancelNote = document.getElementById('cancel-note');
const submitNote = document.getElementById('submit-note');
const noteType = document.getElementById('note-type');
const noteContent = document.getElementById('note-content');
const noteStatus = document.getElementById('note-status');

// Get person_id from URL
const urlParams = new URLSearchParams(window.location.search);
const personId = urlParams.get('id');

let currentPerson = null;

// ============================================================================
// Load Profile
// ============================================================================

async function loadProfile() {
  if (!personId) {
    personName.textContent = 'Error: No person ID provided';
    return;
  }

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}`), {
      headers: getApiHeaders(),
    });

    if (!response.ok) {
      if (response.status === 404) {
        personName.textContent = 'Person not found';
        return;
      }
      throw new Error('Failed to load profile');
    }

    const data = await response.json();
    currentPerson = data;
    renderProfile(data);
    await loadTimeline();
  } catch (error) {
    console.error('Error loading profile:', error);
    personName.textContent = 'Error loading profile';
  }
}

function renderProfile(person) {
  const terms = getTerminology();

  personName.textContent = person.name;
  document.title = `Custos — ${person.name}`;

  // Type with terminology
  const typeLabel = person.type === 'org' ? 'Organization' : terms.person;
  personType.textContent = typeLabel;

  // Role
  personRole.textContent = person.role ? `Role: ${person.role}` : 'No role set';

  // Last interaction
  lastInteraction.textContent = person.last_interaction_at
    ? `Last interaction: ${formatDate(person.last_interaction_at)}`
    : 'No interactions recorded';

  // Render tags
  renderTags(person.tags || []);

  // Render recent notes
  renderRecentNotes(person.recent_sources || []);

  // Timeline summary
  const summary = person.timeline_summary;
  timelineStats.textContent = `${summary.total_entries} entries (${summary.direct_count} direct, ${summary.meeting_count} ${terms.meetings.toLowerCase()})`;
}

function renderTags(tags) {
  personTags.innerHTML = '';

  tags.forEach(tag => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';

    const tagText = document.createElement('span');
    tagText.textContent = tag;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'tag-remove';
    removeBtn.type = 'button';
    removeBtn.innerHTML = '&times;';
    removeBtn.title = 'Remove tag';
    removeBtn.addEventListener('click', () => removeTag(tag));

    chip.appendChild(tagText);
    chip.appendChild(removeBtn);
    personTags.appendChild(chip);
  });

  // Add tag button
  const addBtn = document.createElement('button');
  addBtn.className = 'tag-add';
  addBtn.type = 'button';
  addBtn.textContent = '+ Add tag';
  addBtn.addEventListener('click', openTagModal);
  personTags.appendChild(addBtn);
}

function renderRecentNotes(sources) {
  recentNotes.innerHTML = '';

  if (!sources.length) {
    recentNotes.innerHTML = '<div class="card"><p class="muted">No direct notes captured yet.</p></div>';
    return;
  }

  sources.forEach(source => {
    const card = document.createElement('div');
    card.className = 'card direct-note';

    const title = document.createElement('h4');
    title.textContent = 'Direct note';

    const meta = document.createElement('p');
    meta.className = 'muted';
    meta.textContent = `Captured ${formatDate(source.captured_at)} · ${source.capture_type}`;

    card.appendChild(title);
    card.appendChild(meta);
    recentNotes.appendChild(card);
  });
}

async function loadTimeline() {
  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/timeline`), {
      headers: getApiHeaders(),
    });

    if (!response.ok) {
      return;
    }

    const data = await response.json();
    renderTimelinePreview(data.timeline.slice(0, 5));
  } catch (error) {
    console.error('Error loading timeline:', error);
  }
}

function renderTimelinePreview(entries) {
  const terms = getTerminology();
  timelinePreview.innerHTML = '';

  if (!entries.length) {
    timelinePreview.innerHTML = '<div class="card"><p class="muted">No timeline entries yet.</p></div>';
    return;
  }

  entries.forEach(entry => {
    const card = document.createElement('div');
    card.className = 'card';

    if (entry.source_type === 'direct') {
      card.classList.add('direct-note');
    }

    const title = document.createElement('h4');
    if (entry.source_type === 'direct') {
      title.textContent = 'Direct note';
    } else {
      title.textContent = entry.meeting_title || terms.meeting;
    }

    const when = formatDate(entry.occurred_at);
    const meta = document.createElement('p');
    meta.className = 'muted';

    if (entry.source_type === 'meeting') {
      meta.textContent = `${terms.meeting} at ${formatDate(entry.meeting_starts_at)}`;
    } else {
      meta.textContent = `Captured at ${when}`;
    }

    const typeInfo = document.createElement('p');
    typeInfo.className = 'muted';
    typeInfo.textContent = entry.capture_type || 'notes';

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(typeInfo);
    timelinePreview.appendChild(card);
  });
}

// ============================================================================
// Role Modal
// ============================================================================

function openRoleModal() {
  roleInput.value = currentPerson?.role || '';
  setModalOpen(roleModal, true);
  roleInput.focus();
}

function closeRoleModalFn() {
  setModalOpen(roleModal, false);
  roleInput.value = '';
}

async function submitRoleFn() {
  submitRole.disabled = true;
  submitRole.textContent = 'Saving...';

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}`), {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getApiHeaders(),
      },
      body: JSON.stringify({
        role: roleInput.value.trim() || null,
      }),
    });

    if (response.ok) {
      closeRoleModalFn();
      await loadProfile();
    } else {
      console.error('Failed to update role');
    }
  } catch (error) {
    console.error('Error updating role:', error);
  } finally {
    submitRole.disabled = false;
    submitRole.textContent = 'Save Role';
  }
}

// ============================================================================
// Tag Modal
// ============================================================================

function openTagModal() {
  tagInput.value = '';
  setModalOpen(tagModal, true);
  tagInput.focus();
}

function closeTagModalFn() {
  setModalOpen(tagModal, false);
  tagInput.value = '';
}

async function submitTagFn() {
  const tag = tagInput.value.trim();
  if (!tag) return;

  submitTag.disabled = true;
  submitTag.textContent = 'Adding...';

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/tags`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getApiHeaders(),
      },
      body: JSON.stringify({ tag }),
    });

    if (response.ok) {
      closeTagModalFn();
      await loadProfile();
    } else if (response.status === 409) {
      // Tag already exists
      closeTagModalFn();
    } else {
      console.error('Failed to add tag');
    }
  } catch (error) {
    console.error('Error adding tag:', error);
  } finally {
    submitTag.disabled = false;
    submitTag.textContent = 'Add Tag';
  }
}

async function removeTag(tag) {
  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/tags/${encodeURIComponent(tag)}`), {
      method: 'DELETE',
      headers: getApiHeaders(),
    });

    if (response.ok) {
      await loadProfile();
    } else {
      console.error('Failed to remove tag');
    }
  } catch (error) {
    console.error('Error removing tag:', error);
  }
}

// ============================================================================
// Note Modal
// ============================================================================

function populateNoteTypes() {
  const types = getCaptureTypes();
  noteType.innerHTML = '';

  types.forEach(type => {
    const option = document.createElement('option');
    option.value = type.value;
    option.textContent = type.label;
    noteType.appendChild(option);
  });
}

function openNoteModal() {
  populateNoteTypes();
  noteContent.value = '';
  noteStatus.textContent = '';
  setModalOpen(noteModal, true);
  noteContent.focus();
}

function closeNoteModalFn() {
  setModalOpen(noteModal, false);
  noteContent.value = '';
  noteStatus.textContent = '';
}

async function submitNoteFn() {
  const content = noteContent.value.trim();
  if (!content) {
    noteStatus.textContent = 'Please enter some content.';
    return;
  }

  submitNote.disabled = true;
  submitNote.textContent = 'Saving...';

  try {
    const response = await fetch(apiUrl(`/api/people/${personId}/notes`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getApiHeaders(),
      },
      body: JSON.stringify({
        capture_type: noteType.value,
        payload: content,
      }),
    });

    if (response.ok) {
      closeNoteModalFn();
      // Wait a bit for the worker to process, then reload
      setTimeout(() => {
        loadProfile();
      }, 500);
    } else {
      const error = await response.json();
      noteStatus.textContent = error.detail || 'Failed to save note.';
    }
  } catch (error) {
    console.error('Error saving note:', error);
    noteStatus.textContent = 'Error saving note.';
  } finally {
    submitNote.disabled = false;
    submitNote.textContent = 'Save Note';
  }
}

// ============================================================================
// Modal Utilities
// ============================================================================

function setModalOpen(modal, open) {
  if (!modal) return;
  modal.classList.toggle('open', open);
  modal.setAttribute('aria-hidden', open ? 'false' : 'true');
}

// ============================================================================
// Event Listeners
// ============================================================================

// Role modal
editRoleBtn?.addEventListener('click', openRoleModal);
closeRoleModal?.addEventListener('click', closeRoleModalFn);
cancelRole?.addEventListener('click', closeRoleModalFn);
submitRole?.addEventListener('click', submitRoleFn);

// Tag modal
closeTagModal?.addEventListener('click', closeTagModalFn);
cancelTag?.addEventListener('click', closeTagModalFn);
submitTag?.addEventListener('click', submitTagFn);

// Note modal
addNoteBtn?.addEventListener('click', openNoteModal);
closeNoteModal?.addEventListener('click', closeNoteModalFn);
cancelNote?.addEventListener('click', closeNoteModalFn);
submitNote?.addEventListener('click', submitNoteFn);

// Close modals on escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (roleModal?.classList.contains('open')) closeRoleModalFn();
    if (tagModal?.classList.contains('open')) closeTagModalFn();
    if (noteModal?.classList.contains('open')) closeNoteModalFn();
  }
});

// Submit on Enter for single-line inputs
roleInput?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !submitRole.disabled) {
    e.preventDefault();
    submitRoleFn();
  }
});

tagInput?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !submitTag.disabled) {
    e.preventDefault();
    submitTagFn();
  }
});

// Close modals on backdrop click
roleModal?.addEventListener('click', (e) => {
  if (e.target === roleModal || e.target?.hasAttribute('data-role-close')) {
    closeRoleModalFn();
  }
});

tagModal?.addEventListener('click', (e) => {
  if (e.target === tagModal || e.target?.hasAttribute('data-tag-close')) {
    closeTagModalFn();
  }
});

noteModal?.addEventListener('click', (e) => {
  if (e.target === noteModal || e.target?.hasAttribute('data-note-close')) {
    closeNoteModalFn();
  }
});

// Offline indicator
const offlineBadge = document.getElementById('offline-badge');

function updateOfflineIndicator() {
  if (!offlineBadge) return;
  const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
  offlineBadge.classList.toggle('hidden', !isOffline);
}

window.addEventListener('online', () => {
  updateOfflineIndicator();
  loadProfile().catch(() => {});
});

window.addEventListener('offline', updateOfflineIndicator);

updateOfflineIndicator();

// ============================================================================
// Initialize
// ============================================================================

loadProfile();
