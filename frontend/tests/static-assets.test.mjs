import fs from 'node:fs';
import assert from 'node:assert/strict';

const files = ['index.html', 'people.html', 'status.html'];

for (const file of files) {
  const html = fs.readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
  assert.match(html, /<link rel="icon" href="favicon\.svg"/, `${file}: favicon link missing`);
  assert.match(html, /<meta name="description" content="Custos — calm, local-first meeting briefings and context\." \/>/, `${file}: description meta missing`);
  assert.match(html, /<meta name="theme-color" content="#f5f1ea" \/>/, `${file}: theme-color meta missing`);
}

const titleChecks = {
  'index.html': /<title>Custos — Briefing<\/title>/,
  'people.html': /<title>Custos — People<\/title>/,
  'status.html': /<title>Custos — Status<\/title>/,
};

for (const [file, pattern] of Object.entries(titleChecks)) {
  const html = fs.readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
  assert.match(html, pattern, `${file}: title mismatch`);
}

console.log('static-assets.test.mjs: ok');
