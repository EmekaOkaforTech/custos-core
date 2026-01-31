/**
 * Tests for Epic 34/35: Context Modes (Care and Professional)
 *
 * Tests for:
 * - Terminology based on context mode
 * - Capture types based on context mode
 * - Briefing mode functions
 */

import assert from 'node:assert/strict';

// Mock localStorage for testing
const mockStorage = {};
globalThis.localStorage = {
  getItem: (key) => mockStorage[key] ?? null,
  setItem: (key, value) => { mockStorage[key] = value; },
  removeItem: (key) => { delete mockStorage[key]; },
};

// Import functions under test
import {
  getBriefingMode,
  setBriefingMode,
  getCareMode,
  setCareMode,
  getProfessionalMode,
  setProfessionalMode,
  getTerminology,
  getCaptureTypes,
} from '../ui-state.js';

function clearStorage() {
  Object.keys(mockStorage).forEach(key => delete mockStorage[key]);
}

function run() {
  // Test 1: Default briefing mode is 'time'
  clearStorage();
  assert.equal(getBriefingMode(), 'time', 'Default briefing mode should be time');

  // Test 2: Setting briefing mode to 'person'
  clearStorage();
  setBriefingMode('person');
  assert.equal(getBriefingMode(), 'person', 'Briefing mode should be person after setting');

  // Test 3: Default context mode is standard (care=false, professional=false)
  clearStorage();
  assert.equal(getCareMode(), false, 'Care mode should default to false');
  assert.equal(getProfessionalMode(), false, 'Professional mode should default to false');

  // Test 4: Setting care mode disables professional mode
  clearStorage();
  setProfessionalMode(true);
  assert.equal(getProfessionalMode(), true, 'Professional mode should be enabled');
  setCareMode(true);
  assert.equal(getCareMode(), true, 'Care mode should be enabled');
  assert.equal(getProfessionalMode(), false, 'Professional mode should be disabled when care mode is enabled');

  // Test 5: Setting professional mode disables care mode
  clearStorage();
  setCareMode(true);
  assert.equal(getCareMode(), true, 'Care mode should be enabled');
  setProfessionalMode(true);
  assert.equal(getProfessionalMode(), true, 'Professional mode should be enabled');
  assert.equal(getCareMode(), false, 'Care mode should be disabled when professional mode is enabled');

  // Test 6: Standard mode terminology
  clearStorage();
  const standardTerms = getTerminology();
  assert.equal(standardTerms.meeting, 'Meeting', 'Standard meeting term');
  assert.equal(standardTerms.person, 'Person', 'Standard person term');
  assert.equal(standardTerms.commitment, 'Commitment', 'Standard commitment term');

  // Test 7: Care mode terminology
  clearStorage();
  setCareMode(true);
  const careTerms = getTerminology();
  assert.equal(careTerms.meeting, 'Visit', 'Care meeting term should be Visit');
  assert.equal(careTerms.person, 'Care recipient', 'Care person term should be Care recipient');
  assert.equal(careTerms.commitment, 'Follow-up', 'Care commitment term should be Follow-up');

  // Test 8: Professional mode terminology
  clearStorage();
  setProfessionalMode(true);
  const profTerms = getTerminology();
  assert.equal(profTerms.meeting, 'Session', 'Professional meeting term should be Session');
  assert.equal(profTerms.person, 'Client', 'Professional person term should be Client');
  assert.equal(profTerms.commitment, 'Action item', 'Professional commitment term should be Action item');

  // Test 9: Standard capture types
  clearStorage();
  const standardTypes = getCaptureTypes();
  const standardValues = standardTypes.map(t => t.value);
  assert.ok(standardValues.includes('notes'), 'Standard should have notes');
  assert.ok(standardValues.includes('transcript'), 'Standard should have transcript');
  assert.ok(standardValues.includes('decision'), 'Standard should have decision');
  assert.ok(standardValues.includes('reflection'), 'Standard should have reflection');
  assert.ok(!standardValues.includes('observation'), 'Standard should NOT have observation');
  assert.ok(!standardValues.includes('intake'), 'Standard should NOT have intake');

  // Test 10: Care mode capture types include care-specific types
  clearStorage();
  setCareMode(true);
  const careTypes = getCaptureTypes();
  const careValues = careTypes.map(t => t.value);
  assert.ok(careValues.includes('notes'), 'Care should have notes');
  assert.ok(careValues.includes('observation'), 'Care should have observation');
  assert.ok(careValues.includes('symptom'), 'Care should have symptom');
  assert.ok(careValues.includes('mood'), 'Care should have mood');
  assert.ok(careValues.includes('medication'), 'Care should have medication');
  assert.ok(!careValues.includes('intake'), 'Care should NOT have intake');

  // Test 11: Professional mode capture types include intake
  clearStorage();
  setProfessionalMode(true);
  const profTypes = getCaptureTypes();
  const profValues = profTypes.map(t => t.value);
  assert.ok(profValues.includes('notes'), 'Professional should have notes');
  assert.ok(profValues.includes('intake'), 'Professional should have intake');
  assert.ok(!profValues.includes('observation'), 'Professional should NOT have observation');
  assert.ok(!profValues.includes('symptom'), 'Professional should NOT have symptom');

  console.log('context-modes.test.mjs: all tests passed');
}

run();
