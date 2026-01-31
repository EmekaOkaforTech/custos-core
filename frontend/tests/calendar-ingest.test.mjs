import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const html = readFileSync(join(ROOT, 'status.html'), 'utf8');

assert.ok(/id="calendar-import"/.test(html), 'status.html missing calendar import button');

console.log('calendar-ingest.test.mjs: ok');
