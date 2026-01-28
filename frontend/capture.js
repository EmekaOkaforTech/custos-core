import {
  apiUrl,
  formatDate,
  getApiBase,
  getApiHeaders,
  getBriefingCache,
  getCaptureDefaults,
  isSetupComplete,
  setCaptureDefaults,
  clearCaptureDefaults,
  setBriefingCache,
} from './ui-state.js';

export function initCapture({ onSuccess } = {}) {
  const modal = document.getElementById('capture-modal');
  const openButton = document.getElementById('capture-open');
  const quickButton = document.getElementById('capture-quick');
  const reflectionButton = document.getElementById('capture-reflection');
  if (!modal || !openButton) return;

  const meetingSelect = document.getElementById('capture-meeting');
  const meetingDetail = document.getElementById('capture-meeting-detail');
  const meetingTitleLabel = document.getElementById('capture-meeting-title-label');
  const meetingTitleInput = document.getElementById('capture-meeting-title');
  const meetingStartLabel = document.getElementById('capture-meeting-start-label');
  const meetingStartInput = document.getElementById('capture-meeting-start');
  const meetingCreateRow = document.getElementById('capture-meeting-create');
  const meetingHelp = document.getElementById('capture-meeting-help');
  const advancedToggle = document.getElementById('capture-advanced-toggle');
  const advancedSection = document.getElementById('capture-advanced');
  const peopleGroup = document.getElementById('capture-people-group');
  const captureType = document.getElementById('capture-type');
  const commitmentRelevantBy = document.getElementById('capture-commitment-relevant');
  const relevantWhen = document.getElementById('capture-relevant');
  const relevantDate = document.getElementById('capture-relevant-date');
  const indexInMemory = document.getElementById('capture-index-memory');
  const notes = document.getElementById('capture-notes');
  const status = document.getElementById('capture-status');
  const submitButton = document.getElementById('capture-submit');
  const peopleInput = document.getElementById('capture-people-input');
  const peopleOptions = document.getElementById('people-options');
  const peopleTags = document.getElementById('capture-people-tags');
  const addPerson = document.getElementById('capture-add-person');
  const peopleType = document.getElementById('capture-people-type');
  const resetDefaults = document.getElementById('capture-reset-defaults');
  const closeButtons = modal.querySelectorAll('[data-capture-close]');
  const closeButton = document.getElementById('capture-close');

  const selectedPeople = new Map();
  let meetingMap = { next: null, today: null };
  let peopleList = [];
  let meetingById = new Map();
  let quickMode = false;

  function setStatus(message) {
    if (!status) return;
    status.textContent = message || '';
  }

  function setModalOpen(open) {
    modal.classList.toggle('open', open);
    modal.setAttribute('aria-hidden', open ? 'false' : 'true');
    if (!open) {
      setStatus('');
      quickMode = false;
    }
  }

  function clearPeople() {
    selectedPeople.clear();
    if (peopleTags) {
      peopleTags.innerHTML = '';
    }
  }

  function renderPeopleTags() {
    if (!peopleTags) return;
    peopleTags.innerHTML = '';
    if (!selectedPeople.size) return;
    selectedPeople.forEach((name, id) => {
      const tag = document.createElement('button');
      tag.type = 'button';
      tag.className = 'tag';
      tag.textContent = name;
      tag.addEventListener('click', () => {
        selectedPeople.delete(id);
        renderPeopleTags();
      });
      peopleTags.appendChild(tag);
    });
  }

  function setAdvancedVisible(visible) {
    if (advancedSection) {
      advancedSection.classList.toggle('hidden', !visible);
    }
    if (peopleGroup) {
      peopleGroup.classList.toggle('hidden', !visible);
    }
    if (advancedToggle) {
      advancedToggle.textContent = visible ? 'Hide details' : 'Show details';
    }
  }

  function updatePeopleActionLabel() {
    if (!addPerson) return;
    const type = peopleType?.value || 'person';
    if (type === 'org') {
      addPerson.textContent = 'Add organization';
    } else {
      addPerson.textContent = 'Add person';
    }
  }

  function setRelevantDateVisible(visible) {
    if (relevantDate) {
      relevantDate.classList.toggle('hidden', !visible);
    }
  }

  function applyIndexDefault(type) {
    if (!indexInMemory) return;
    indexInMemory.checked = type === 'reflection';
  }

  function resolveRelevantAt() {
    if (!relevantWhen) return null;
    const value = relevantWhen.value;
    if (!value) return null;
    const now = new Date();
    if (value === 'date') {
      if (!relevantDate || !relevantDate.value) return null;
      const dateValue = new Date(`${relevantDate.value}T09:00:00`);
      return dateValue.toISOString();
    }
    const base = new Date(now.getTime());
    if (value === 'later-today') {
      base.setHours(23, 59, 0, 0);
      return base.toISOString();
    }
    if (value === 'this-week') {
      const day = base.getDay();
      const diff = 7 - day;
      base.setDate(base.getDate() + diff);
      base.setHours(23, 59, 0, 0);
      return base.toISOString();
    }
    if (value === 'next-week') {
      const day = base.getDay();
      const diff = 7 - day + 7;
      base.setDate(base.getDate() + diff);
      base.setHours(23, 59, 0, 0);
      return base.toISOString();
    }
    return null;
  }

  function applyQuickDefaults() {
    if (captureType) {
      captureType.value = 'notes';
      applyIndexDefault('notes');
    }
    if (meetingSelect) {
      if (meetingMap.next) {
        meetingSelect.value = 'next';
      } else if (meetingMap.today) {
        meetingSelect.value = 'today';
      } else {
        meetingSelect.value = 'create';
        if (meetingTitleInput && !meetingTitleInput.value.trim()) {
          const today = new Date().toISOString().slice(0, 10);
          meetingTitleInput.value = `Quick capture ${today}`;
        }
      }
    }
    updateMeetingDetail();
    if (notes) {
      notes.focus();
    }
  }

  updatePeopleActionLabel();

  function applyReflectionDefaults() {
    if (captureType) {
      captureType.value = 'reflection';
      applyIndexDefault('reflection');
    }
    if (meetingSelect) {
      meetingSelect.value = 'create';
    }
    if (meetingTitleInput) {
      const today = new Date().toISOString().slice(0, 10);
      meetingTitleInput.value = `Reflection ${today}`;
    }
    updateMeetingDetail();
    if (notes) {
      notes.focus();
    }
  }
  function setSelectedPeople(list) {
    selectedPeople.clear();
    if (!Array.isArray(list)) return;
    list.forEach(person => {
      if (person?.id && person?.name) {
        selectedPeople.set(person.id, person.name);
      }
    });
    renderPeopleTags();
  }

  async function createPersonByName(name) {
    const type = peopleType?.value || 'person';
    try {
      const response = await fetch(apiUrl('/api/people'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
        body: JSON.stringify({ name, type }),
      });
      if (!response.ok) {
        setStatus('Unable to create person. Check the name and try again.');
        return null;
      }
      return await response.json();
    } catch (err) {
      setStatus('Unable to create person. Check connectivity.');
      return null;
    }
  }

  async function addPersonTag(value) {
    const cleaned = value.trim();
    if (!cleaned) return;
    const match = peopleList.find(person => person.name.toLowerCase() === cleaned.toLowerCase());
    if (!match) {
      const created = await createPersonByName(cleaned);
      if (!created) {
        return;
      }
      peopleList = [...peopleList.filter(person => person.id !== created.id), created];
      if (peopleOptions) {
        const option = document.createElement('option');
        option.value = created.name;
        peopleOptions.appendChild(option);
      }
      selectedPeople.set(created.id, created.name);
      setStatus('');
      if (peopleInput) {
        peopleInput.value = '';
      }
      renderPeopleTags();
      return;
    }
    selectedPeople.set(match.id, match.name);
    setStatus('');
    if (peopleInput) {
      peopleInput.value = '';
    }
    renderPeopleTags();
  }

  function toggleMeetingCreate(visible) {
    if (meetingTitleLabel) {
      meetingTitleLabel.classList.toggle('hidden', !visible);
    }
    if (meetingCreateRow) {
      meetingCreateRow.classList.toggle('hidden', !visible);
    }
    if (meetingStartLabel) {
      meetingStartLabel.classList.toggle('hidden', !visible);
    }
    if (meetingStartInput) {
      meetingStartInput.classList.toggle('hidden', !visible);
    }
    if (meetingHelp) {
      meetingHelp.classList.toggle('hidden', !visible);
    }
  }

  function applyStoredDefaults() {
    const defaults = getCaptureDefaults();
    if (!defaults) return;
    if (captureType && defaults.captureType) {
      captureType.value = defaults.captureType;
      applyIndexDefault(defaults.captureType);
    }
    if (defaults.people && defaults.people.length) {
      setSelectedPeople(defaults.people);
    }
  }

  function updateMeetingDetail() {
    if (!meetingDetail || !meetingSelect || !submitButton) return;
    const value = meetingSelect.value;
    if (value === 'create') {
      toggleMeetingCreate(true);
      const title = meetingTitleInput?.value?.trim() || '';
      if (!title) {
        meetingDetail.textContent = 'Enter a title to create a meeting.';
        submitButton.disabled = true;
        return;
      }
      meetingDetail.textContent = `Create “${title}”`;
      submitButton.disabled = false;
      return;
    }
    toggleMeetingCreate(false);
    if (value.startsWith('meeting:')) {
      const meetingId = value.replace('meeting:', '');
      const meeting = meetingById.get(meetingId);
      if (!meeting) {
        meetingDetail.textContent = 'Meeting unavailable.';
        submitButton.disabled = true;
        return;
      }
      submitButton.disabled = false;
      const when = meeting.starts_at ? formatDate(meeting.starts_at) : 'time not set';
      meetingDetail.textContent = `${meeting.title} · ${when}`;
      return;
    }
    const meeting = meetingMap[value];
    if (!meeting) {
      meetingDetail.textContent = value === 'today'
        ? 'No meetings scheduled for today.'
        : 'No upcoming meeting found.';
      submitButton.disabled = true;
      return;
    }
    submitButton.disabled = false;
    const when = meeting.starts_at ? formatDate(meeting.starts_at) : 'time not set';
    meetingDetail.textContent = `${meeting.title} · ${when}`;
  }

  function guardSetupReady() {
    if (!getApiBase() || !isSetupComplete()) {
      setStatus('Connect to your backend to capture context.');
      if (submitButton) {
        submitButton.disabled = true;
      }
      return false;
    }
    return true;
  }

  function applyMeetingOptions() {
    if (!meetingSelect) return;
    const nextOption = meetingSelect.querySelector('option[value="next"]');
    const todayOption = meetingSelect.querySelector('option[value="today"]');
    if (nextOption) {
      nextOption.disabled = !meetingMap.next;
    }
    if (todayOption) {
      todayOption.disabled = !meetingMap.today;
    }
    if (meetingSelect.value === 'next' && !meetingMap.next && meetingMap.today) {
      meetingSelect.value = 'today';
    }
    if (meetingSelect.value === 'today' && !meetingMap.today && meetingMap.next) {
      meetingSelect.value = 'next';
    }
    meetingSelect.querySelectorAll('option[data-dynamic="true"]').forEach(option => option.remove());
    meetingById = new Map();
    const dynamic = [];
    const seen = new Set();
    if (meetingMap.next?.id) seen.add(meetingMap.next.id);
    if (meetingMap.today?.id) seen.add(meetingMap.today.id);
    if (Array.isArray(meetingMap.upcoming)) {
      meetingMap.upcoming.forEach(meeting => {
        if (!meeting?.id || seen.has(meeting.id)) return;
        dynamic.push(meeting);
        seen.add(meeting.id);
      });
    }
    if (dynamic.length) {
      dynamic.forEach(meeting => {
        meetingById.set(meeting.id, meeting);
        const option = document.createElement('option');
        option.value = `meeting:${meeting.id}`;
        option.textContent = meeting.title || 'Upcoming meeting';
        option.dataset.dynamic = 'true';
        meetingSelect.insertBefore(option, meetingSelect.querySelector('option[value="create"]'));
      });
    }
    updateMeetingDetail();
  }

  async function loadMeetings() {
    const cached = getBriefingCache();
    const cacheSnapshot = {
      next: cached?.next || null,
      today: cached?.today || null,
    };
    if (cached) {
      meetingMap = {
        next: cached.next?.meeting || null,
        today: cached.today?.meetings?.[0] || null,
      };
    }
    try {
      const [nextResponse, todayResponse, upcomingResponse] = await Promise.all([
        fetch(apiUrl('/api/briefings/next'), { headers: getApiHeaders() }),
        fetch(apiUrl('/api/briefings/today'), { headers: getApiHeaders() }),
        fetch(apiUrl('/api/meetings?range=upcoming'), { headers: getApiHeaders() }),
      ]);
      if (nextResponse.ok) {
        const nextData = await nextResponse.json();
        meetingMap.next = nextData.meeting || null;
        cacheSnapshot.next = nextData;
      }
      if (todayResponse.ok) {
        const todayData = await todayResponse.json();
        meetingMap.today = todayData.meetings?.[0] || null;
        cacheSnapshot.today = todayData;
      }
      if (upcomingResponse.ok) {
        const upcomingData = await upcomingResponse.json();
        if (Array.isArray(upcomingData)) {
          meetingMap.upcoming = upcomingData;
        } else {
          meetingMap.upcoming = Array.isArray(upcomingData?.meetings) ? upcomingData.meetings : [];
        }
      }
    } catch (err) {
      setStatus('Unable to refresh meetings right now.');
    }
    setBriefingCache(cacheSnapshot);
    applyMeetingOptions();
  }

  async function loadPeople() {
    if (!peopleOptions) return;
    try {
      const response = await fetch(apiUrl('/api/people'), { headers: getApiHeaders() });
      if (!response.ok) return;
      const data = await response.json();
      peopleList = Array.isArray(data) ? data : [];
      peopleOptions.innerHTML = '';
      peopleList.forEach(person => {
        const option = document.createElement('option');
        option.value = person.name;
        peopleOptions.appendChild(option);
      });
    } catch (err) {
      // Optional enhancement only; ignore errors.
    }
  }

  async function createMeetingFromInput() {
    const title = meetingTitleInput?.value?.trim();
    if (!title) {
      setStatus('Add a meeting title before saving.');
      return null;
    }
    const startsAt = meetingStartInput?.value ? new Date(meetingStartInput.value).toISOString() : null;
    try {
      const response = await fetch(apiUrl('/api/meetings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
        body: JSON.stringify({ title, starts_at: startsAt || undefined }),
      });
      if (!response.ok) {
        setStatus('Unable to create meeting. Please try again.');
        return null;
      }
      return await response.json();
    } catch (err) {
      setStatus('Unable to create meeting. Check connectivity.');
      return null;
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitButton) {
      submitButton.disabled = true;
    }
    const selection = meetingSelect?.value || 'next';
    let meeting = meetingMap[selection];
    if (selection === 'create') {
      meeting = await createMeetingFromInput();
      if (!meeting) {
        if (submitButton) {
          submitButton.disabled = false;
        }
        return;
      }
    }
    if (selection.startsWith('meeting:')) {
      const meetingId = selection.replace('meeting:', '');
      meeting = meetingById.get(meetingId) || null;
    }
    if (!meeting) {
      setStatus('Select a meeting that is available before capturing notes.');
      if (submitButton) {
        submitButton.disabled = false;
      }
      return;
    }
    const payload = notes?.value?.trim() || '';
    if (!payload) {
      setStatus('Add a short note before saving.');
      if (submitButton) {
        submitButton.disabled = false;
      }
      return;
    }
    const captureValue = captureType?.value || 'notes';
    const indexFlag = indexInMemory ? indexInMemory.checked : captureValue === 'reflection';
    const peopleIds = Array.from(selectedPeople.keys());
    const relevantAt = resolveRelevantAt();
    const commitmentRelevantAt = commitmentRelevantBy?.value
      ? new Date(`${commitmentRelevantBy.value}T09:00:00`).toISOString()
      : null;
    const body = {
      meeting_id: meeting.id,
      capture_type: captureValue,
      payload,
      people_ids: peopleIds.length ? peopleIds : undefined,
      relevant_at: relevantAt || undefined,
      commitment_relevant_by: commitmentRelevantAt || undefined,
      index_in_memory: indexFlag,
    };

    try {
      const response = await fetch(apiUrl('/api/ingestion'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getApiHeaders() },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setStatus('Capture failed. Please try again.');
        if (submitButton) {
          submitButton.disabled = false;
        }
        return;
      }
      setStatus('Captured. Briefing will refresh shortly.');
      notes.value = '';
      if (meetingTitleInput) {
        meetingTitleInput.value = '';
      }
      setCaptureDefaults({
        captureType: captureValue,
        people: Array.from(selectedPeople.entries()).map(([id, name]) => ({ id, name })),
      });
      clearPeople();
      if (commitmentRelevantBy) {
        commitmentRelevantBy.value = '';
      }
      if (relevantWhen) {
        relevantWhen.value = '';
      }
      if (relevantDate) {
        relevantDate.value = '';
        setRelevantDateVisible(false);
      }
      if (typeof onSuccess === 'function') {
        onSuccess();
      }
      setTimeout(() => setModalOpen(false), 300);
    } catch (err) {
      setStatus('Capture failed. Please check connectivity.');
      if (submitButton) {
        submitButton.disabled = false;
      }
    }
  }

  function openModal() {
    quickMode = false;
    setStatus('');
    setModalOpen(true);
    if (!guardSetupReady()) {
      return;
    }
    void loadMeetings();
    loadPeople();
    applyStoredDefaults();
    if (captureType) {
      applyIndexDefault(captureType.value);
    }
    updateMeetingDetail();
    setAdvancedVisible(true);
    if (meetingSelect) {
      meetingSelect.focus();
    }
  }

  function openQuickCapture() {
    quickMode = true;
    setStatus('');
    setModalOpen(true);
    if (!guardSetupReady()) {
      return;
    }
    loadPeople();
    loadMeetings().then(() => {
      if (quickMode) {
        applyQuickDefaults();
      }
    });
    applyStoredDefaults();
    if (captureType) {
      applyIndexDefault(captureType.value);
    }
    setAdvancedVisible(false);
  }

  function openReflectionCapture() {
    quickMode = false;
    setStatus('');
    setModalOpen(true);
    if (!guardSetupReady()) {
      return;
    }
    loadPeople();
    loadMeetings().then(() => {
      applyReflectionDefaults();
    });
    setAdvancedVisible(true);
  }

  openButton.addEventListener('click', openModal);
  if (quickButton) {
    quickButton.addEventListener('click', openQuickCapture);
  }
  if (reflectionButton) {
    reflectionButton.addEventListener('click', openReflectionCapture);
  }
  closeButtons.forEach(button => button.addEventListener('click', () => setModalOpen(false)));
  if (closeButton) {
    closeButton.addEventListener('click', () => setModalOpen(false));
  }
  if (meetingSelect) {
    meetingSelect.addEventListener('change', updateMeetingDetail);
  }
  if (advancedToggle) {
    advancedToggle.addEventListener('click', () => {
      const isHidden = advancedSection?.classList.contains('hidden');
      setAdvancedVisible(Boolean(isHidden));
    });
  }
  if (captureType) {
    captureType.addEventListener('change', () => {
      applyIndexDefault(captureType.value);
    });
  }
  if (resetDefaults) {
    resetDefaults.addEventListener('click', () => {
      clearCaptureDefaults();
      setStatus('Capture defaults cleared.');
      clearPeople();
      if (captureType) {
        captureType.value = 'notes';
      }
      if (relevantWhen) {
        relevantWhen.value = '';
      }
      if (relevantDate) {
        relevantDate.value = '';
        setRelevantDateVisible(false);
      }
    });
  }
  if (relevantWhen) {
    relevantWhen.addEventListener('change', () => {
      const showDate = relevantWhen.value === 'date';
      setRelevantDateVisible(showDate);
      if (!showDate && relevantDate) {
        relevantDate.value = '';
      }
    });
  }
  if (meetingTitleInput) {
    meetingTitleInput.addEventListener('input', updateMeetingDetail);
  }
  if (peopleType) {
    peopleType.addEventListener('change', updatePeopleActionLabel);
  }
  if (addPerson && peopleInput) {
    addPerson.addEventListener('click', () => {
      void addPersonTag(peopleInput.value);
    });
    peopleInput.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        void addPersonTag(peopleInput.value);
      }
      if (event.key === ',') {
        event.preventDefault();
        void addPersonTag(peopleInput.value.replace(',', ''));
      }
    });
  }
  if (modal) {
    modal.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        setModalOpen(false);
      }
    });
  }
  const form = document.getElementById('capture-form');
  if (form) {
    form.addEventListener('submit', handleSubmit);
  }
}
