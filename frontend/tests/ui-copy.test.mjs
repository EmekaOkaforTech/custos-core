import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const pages = ['index.html', 'people.html', 'status.html'];

for (const page of pages) {
  const html = readFileSync(join(ROOT, page), 'utf8');
  assert.ok(!html.includes('/api/'), `${page} contains raw /api/ string`);
}

console.log('ui-copy.test.mjs: ok');
