import fs from 'node:fs';
import assert from 'node:assert/strict';
import { isSetupComplete, setSetupComplete } from '../ui-state.js';

setSetupComplete(false);
assert.equal(isSetupComplete(), false, 'setup should be false after reset');
setSetupComplete(true);
assert.equal(isSetupComplete(), true, 'setup should be true after set');

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
assert.match(html, /id="setup-banner"/, 'setup banner missing');
assert.match(html, /Connect Custos to your local backend\./, 'setup copy missing');
assert.match(html, /setup-api-base/, 'setup input missing');
assert.match(html, /setup-connect/, 'setup button missing');

console.log('setup-wizard.test.mjs: ok');
