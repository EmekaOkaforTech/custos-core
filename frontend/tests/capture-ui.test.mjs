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
  assert.ok(/id="capture-open"/.test(html), `${page} missing Capture action`);
  assert.ok(/id="capture-quick"/.test(html), `${page} missing Quick Capture action`);
  assert.ok(/id="capture-modal"/.test(html), `${page} missing capture modal`);
  assert.ok(/id="capture-advanced-toggle"/.test(html), `${page} missing advanced toggle`);
  assert.ok(/id="capture-advanced"/.test(html), `${page} missing advanced section`);
  assert.ok(/id="capture-meeting"/.test(html), `${page} missing meeting selector`);
  assert.ok(/value="next"/.test(html), `${page} missing Next meeting option`);
  assert.ok(/value="today"/.test(html), `${page} missing Today option`);
  assert.ok(/value="create"/.test(html), `${page} missing Create new meeting option`);
  assert.ok(/id="capture-type"/.test(html), `${page} missing capture type`);
  assert.ok(/id="capture-notes"/.test(html), `${page} missing notes field`);
  assert.ok(/id="capture-people-input"/.test(html), `${page} missing people selector`);
  assert.ok(/id="capture-people-type"/.test(html), `${page} missing people type selector`);
  assert.ok(/id="capture-add-person"/.test(html), `${page} missing add person button`);
  assert.ok(/id="capture-meeting-title"/.test(html), `${page} missing meeting title input`);
  assert.ok(/id="capture-reset-defaults"/.test(html), `${page} missing reset defaults button`);
  assert.ok(!/meeting_id/i.test(html), `${page} exposes meeting_id`);
}

console.log('capture-ui.test.mjs: ok');
