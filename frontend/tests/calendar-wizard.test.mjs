import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const html = readFileSync(join(ROOT, 'status.html'), 'utf8');

assert.ok(/id="calendar-card"/.test(html), 'status.html missing calendar card');
assert.ok(/id="calendar-modal"/.test(html), 'status.html missing calendar modal');
assert.ok(/Connect calendar \(read-only\)/.test(html), 'missing read-only label');
assert.ok(/id="calendar-consent"/.test(html), 'missing consent checkbox');

console.log('calendar-wizard.test.mjs: ok');
