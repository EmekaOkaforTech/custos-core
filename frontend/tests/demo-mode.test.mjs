import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const pages = ['index.html', 'people.html', 'status.html'];

function load(file) {
  return readFileSync(join(ROOT, file), 'utf8');
}

for (const page of pages) {
  const html = load(page);
  assert.ok(/id="demo-badge"/.test(html), `${page} missing demo badge`);
}

const statusHtml = load('status.html');
assert.ok(/id="demo-reset-card"/.test(statusHtml), 'status.html missing demo reset card');
assert.ok(/id="demo-reset"/.test(statusHtml), 'status.html missing demo reset button');

console.log('demo-mode.test.mjs: ok');
