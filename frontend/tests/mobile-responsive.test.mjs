/**
 * Mobile Responsive Tests
 * Verify CSS has proper mobile-responsive media queries
 */

import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(__dirname, '..');

// Test styles.css exists
const cssPath = join(frontendDir, 'styles.css');
assert.ok(existsSync(cssPath), 'styles.css should exist');

// Read CSS content
const cssContent = readFileSync(cssPath, 'utf8');

// Check for mobile breakpoint
assert.ok(cssContent.includes('@media (max-width: 600px)'),
  'should have mobile breakpoint at 600px');

// Check for tablet breakpoint
assert.ok(cssContent.includes('@media (max-width: 900px)'),
  'should have tablet breakpoint at 900px');

// Check for safe area support
assert.ok(cssContent.includes('env(safe-area-inset'),
  'should support safe area insets for notched devices');

// Check for touch target sizing (44px minimum per WCAG)
assert.ok(cssContent.includes('min-height: 44px'),
  'should have 44px minimum touch targets');

// Check for modal responsiveness
assert.ok(cssContent.includes('.modal-panel') && cssContent.includes('width: 100%'),
  'should have full-width modal on mobile');

// Check for flex-wrap for navigation
assert.ok(cssContent.includes('.global-nav') && cssContent.includes('flex-wrap'),
  'should allow navigation to wrap on small screens');

// Check for reduced motion support
assert.ok(cssContent.includes('prefers-reduced-motion'),
  'should respect prefers-reduced-motion');

// Check for high contrast support
assert.ok(cssContent.includes('prefers-contrast'),
  'should support high contrast mode');

// Check for print styles
assert.ok(cssContent.includes('@media print'),
  'should have print styles');

// Check for offline badge styles
assert.ok(cssContent.includes('.offline-badge'),
  'should have offline badge styles');

// Check for pending badge styles
assert.ok(cssContent.includes('.pending-badge'),
  'should have pending badge styles');

// Check for touch device optimizations
assert.ok(cssContent.includes('@media (hover: none)'),
  'should have touch device optimizations');

console.log('mobile-responsive.test.mjs: pass');
