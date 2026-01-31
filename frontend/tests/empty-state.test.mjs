import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const appJs = readFileSync(join(ROOT, 'app.js'), 'utf8');

assert.ok(appJs.includes('empty-create'), 'empty state missing Create meeting CTA');
assert.ok(appJs.includes('empty-import'), 'empty state missing Import calendar CTA');

console.log('empty-state.test.mjs: ok');
