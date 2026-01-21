import fs from 'node:fs';
import assert from 'node:assert/strict';

const cssPath = new URL('../styles.css', import.meta.url);
const css = fs.readFileSync(cssPath, 'utf8');

const requiredVars = {
  '--space-1': '8px',
  '--space-2': '12px',
  '--space-3': '16px',
  '--space-4': '24px',
  '--space-5': '32px',
  '--text-xs': '11px',
  '--text-sm': '12px',
  '--text-md': '13px',
  '--text-lg': '14px',
  '--text-xl': '16px',
  '--text-xxl': '18px',
  '--line-tight': '1.2',
  '--line-compact': '1.4',
  '--line-base': '1.5',
};

for (const [name, value] of Object.entries(requiredVars)) {
  const pattern = new RegExp(`${name}\\s*:\\s*${value}`);
  assert.match(css, pattern, `Missing ${name}: ${value}`);
}

const selectorUses = [
  { selector: '.container', prop: 'padding', token: '--space-4' },
  { selector: '.section', prop: 'margin-top', token: '--space-4' },
  { selector: '.card', prop: 'padding', token: '--space-3' },
  { selector: '.brief-header', prop: 'margin-bottom', token: '--space-3' },
  { selector: '.site-header', prop: 'padding', token: '--space-4' },
  { selector: '.global-nav', prop: 'padding', token: '--space-1' },
  { selector: '.nav-link', prop: 'padding', token: '--space-1' },
];

for (const { selector, prop, token } of selectorUses) {
  const pattern = new RegExp(`${selector}[^}]*${prop}\\s*:\\s*[^;]*var\\(${token}\\)`);
  assert.match(css, pattern, `Expected ${selector} ${prop} to use ${token}`);
}

const typeUses = [
  { selector: 'body', token: '--text-xl' },
  { selector: '.site-header h1', token: '--text-xxl' },
  { selector: '.brief-title', token: '--text-xl' },
  { selector: '.card h2', token: '--text-lg' },
  { selector: '.section h3', token: '--text-md' },
  { selector: '.status', token: '--text-sm' },
  { selector: '.meta', token: '--text-xs' },
  { selector: '.commitment-meta', token: '--text-xs' },
];

for (const { selector, token } of typeUses) {
  const pattern = new RegExp(`${selector}[^}]*font-size\\s*:\\s*var\\(${token}\\)`);
  assert.match(css, pattern, `Expected ${selector} font-size to use ${token}`);
}

const lineUses = [
  { selector: 'body', token: '--line-base' },
  { selector: '.site-header h1', token: '--line-tight' },
  { selector: '.brief-title', token: '--line-tight' },
  { selector: '.card h2', token: '--line-tight' },
  { selector: '.section h3', token: '--line-tight' },
  { selector: '.nav-link', token: '--line-compact' },
  { selector: '.status', token: '--line-compact' },
  { selector: '.button-link', token: '--line-compact' },
  { selector: '.muted', token: '--line-compact' },
  { selector: '.summary-text', token: '--line-compact' },
];

for (const { selector, token } of lineUses) {
  const pattern = new RegExp(`${selector}[^}]*line-height\\s*:\\s*var\\(${token}\\)`);
  assert.match(css, pattern, `Expected ${selector} line-height to use ${token}`);
}

console.log('visual-consistency.test.mjs: ok');
