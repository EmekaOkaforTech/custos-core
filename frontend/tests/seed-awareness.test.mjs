import fs from 'node:fs';
import assert from 'node:assert/strict';
import { SEED_BANNER_COPY, isSeedIdentifier } from '../ui-state.js';

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

assert.equal(
  SEED_BANNER_COPY,
  'Showing example data from seeded fixtures.',
  'seed banner copy constant changed'
);

const appJs = fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8');
assert.match(appJs, /SEED_BANNER_COPY/, 'seed banner copy constant not used in app.js');

const peopleJs = fs.readFileSync(new URL('../people.js', import.meta.url), 'utf8');
assert.match(peopleJs, /SEED_BANNER_COPY/, 'seed banner copy constant not used in people.js');

console.log('seed-awareness.test.mjs: ok');
