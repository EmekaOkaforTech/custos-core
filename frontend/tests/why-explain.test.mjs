import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const html = readFileSync(join(ROOT, 'index.html'), 'utf8');
const js = readFileSync(join(ROOT, 'app.js'), 'utf8');

assert.ok(/id="why-modal"/.test(html), 'index.html missing why modal');
assert.ok(js.includes('Why am I seeing this?'), 'app.js missing why action text');
assert.ok(!js.includes('reason.meeting.id'), 'explanation UI should not display meeting id');
assert.ok(!js.includes('reason.people.id'), 'explanation UI should not display people ids');

console.log('why-explain.test.mjs: ok');
