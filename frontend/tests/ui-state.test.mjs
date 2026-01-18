import assert from 'node:assert/strict';
import { computeBriefMeta } from '../ui-state.js';

function run() {
  const offline = computeBriefMeta({ cached: false, offline: true, updatedAt: '2026-01-17T10:37:00Z' });
  assert.equal(offline.showOffline, true);
  assert.match(offline.statusText, /Last updated: 2026-01-17 10:37/);

  const cached = computeBriefMeta({ cached: true, offline: false, updatedAt: '2026-01-17T10:00:00Z' });
  assert.equal(cached.showOffline, false);
  assert.match(cached.statusText, /Updated 2026-01-17 10:00 \(cached\)/);

  const normal = computeBriefMeta({ cached: false, offline: false, updatedAt: '2026-01-17T09:00:00Z' });
  assert.equal(normal.showOffline, false);
  assert.match(normal.statusText, /Updated 2026-01-17 09:00/);
}

run();
console.log('ui-state.test.mjs: pass');
