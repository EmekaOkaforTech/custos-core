import fs from 'node:fs';
import assert from 'node:assert/strict';
import { isSeedIdentifier } from '../ui-state.js';

const seedValues = [
  'seed://meeting/m_seed_001',
  'p_seed_org',
  'p_seed_person',
  'm_seed_001',
  'sr_seed_001',
  'c_seed_001',
];

for (const value of seedValues) {
  assert.equal(isSeedIdentifier(value), true, `Expected seed for ${value}`);
}

const nonSeedValues = ['p_real_001', 'meeting_123', 'http://example.com'];
for (const value of nonSeedValues) {
  assert.equal(isSeedIdentifier(value), false, `Expected non-seed for ${value}`);
}

const peopleHtml = fs.readFileSync(new URL('../people.html', import.meta.url), 'utf8');
assert.match(peopleHtml, /id="people-banner"/, 'people-banner container missing');

const appJs = fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8');
assert.match(appJs, /Showing example data from seeded fixtures\./, 'seed banner copy missing in app.js');

console.log('seed-awareness.test.mjs: ok');
