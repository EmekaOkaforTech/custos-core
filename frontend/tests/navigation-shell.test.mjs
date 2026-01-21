import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const ROOT = new URL('..', import.meta.url).pathname;
const pages = [
  { file: 'index.html', label: 'Briefing' },
  { file: 'people.html', label: 'People' },
  { file: 'status.html', label: 'Status' },
];

function load(file) {
  return readFileSync(join(ROOT, file), 'utf8');
}

function hasNav(html) {
  return /<nav[^>]*class="global-nav"/.test(html);
}

function activeLabel(html) {
  const match = html.match(/<a[^>]*aria-current="page"[^>]*>([^<]+)<\/a>/);
  return match ? match[1].trim() : '';
}

for (const page of pages) {
  const html = load(page.file);
  assert.ok(hasNav(html), `${page.file} missing global nav`);
  assert.equal(activeLabel(html), page.label, `${page.file} active nav mismatch`);
}

console.log('navigation-shell.test.mjs: ok');
