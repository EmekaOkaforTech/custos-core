/**
 * PWA Manifest Tests
 * Verify manifest.json exists and has required fields for PWA compliance
 */

import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(__dirname, '..');

// Test manifest.json exists
const manifestPath = join(frontendDir, 'manifest.json');
assert.ok(existsSync(manifestPath), 'manifest.json should exist');

// Parse and validate manifest
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

// Required fields per W3C Web App Manifest spec
assert.ok(manifest.name, 'manifest should have name');
assert.ok(manifest.short_name, 'manifest should have short_name');
assert.ok(manifest.start_url, 'manifest should have start_url');
assert.ok(manifest.display, 'manifest should have display');
assert.ok(manifest.background_color, 'manifest should have background_color');
assert.ok(manifest.theme_color, 'manifest should have theme_color');
assert.ok(Array.isArray(manifest.icons), 'manifest should have icons array');
assert.ok(manifest.icons.length >= 2, 'manifest should have at least 2 icons');

// Validate icon entries
manifest.icons.forEach((icon, index) => {
  assert.ok(icon.src, `icon ${index} should have src`);
  assert.ok(icon.sizes, `icon ${index} should have sizes`);
  assert.ok(icon.type, `icon ${index} should have type`);
});

// Check for required icon sizes (192 and 512)
const sizes = manifest.icons.map(i => i.sizes);
assert.ok(sizes.some(s => s.includes('192')), 'manifest should have 192x192 icon');
assert.ok(sizes.some(s => s.includes('512')), 'manifest should have 512x512 icon');

// Validate display mode
const validDisplayModes = ['fullscreen', 'standalone', 'minimal-ui', 'browser'];
assert.ok(validDisplayModes.includes(manifest.display), 'display should be valid mode');

// Validate colors are valid hex or named colors
const colorPattern = /^#[0-9a-fA-F]{6}$|^#[0-9a-fA-F]{3}$/;
assert.ok(colorPattern.test(manifest.background_color), 'background_color should be valid hex');
assert.ok(colorPattern.test(manifest.theme_color), 'theme_color should be valid hex');

console.log('pwa-manifest.test.mjs: pass');
