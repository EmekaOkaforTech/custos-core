/**
 * Service Worker Tests
 * Verify service-worker.js exists and has correct structure
 */

import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(__dirname, '..');

// Test service-worker.js exists
const swPath = join(frontendDir, 'service-worker.js');
assert.ok(existsSync(swPath), 'service-worker.js should exist');

// Read and validate content
const swContent = readFileSync(swPath, 'utf8');

// Check for required cache configuration
assert.ok(swContent.includes('CACHE_NAME'), 'should define CACHE_NAME');
assert.ok(swContent.includes('STATIC_ASSETS'), 'should define STATIC_ASSETS array');

// Check for required event listeners
assert.ok(swContent.includes("addEventListener('install'"), 'should have install listener');
assert.ok(swContent.includes("addEventListener('activate'"), 'should have activate listener');
assert.ok(swContent.includes("addEventListener('fetch'"), 'should have fetch listener');

// Check for caching strategies
assert.ok(swContent.includes('caches.open'), 'should use Cache API');
assert.ok(swContent.includes('caches.match'), 'should check cache for matches');

// Check for offline support
assert.ok(swContent.includes('networkFirstWithCache') || swContent.includes('network-first'),
  'should implement network-first strategy for API');
assert.ok(swContent.includes('cacheFirstWithNetwork') || swContent.includes('cache-first'),
  'should implement cache-first strategy for static assets');

// Check for required static assets in cache list
assert.ok(swContent.includes('index.html'), 'should cache index.html');
assert.ok(swContent.includes('styles.css'), 'should cache styles.css');
assert.ok(swContent.includes('app.js'), 'should cache app.js');
assert.ok(swContent.includes('manifest.json'), 'should cache manifest.json');

// Check for service worker lifecycle management
assert.ok(swContent.includes('skipWaiting'), 'should support skipWaiting');
assert.ok(swContent.includes('clients.claim'), 'should support clients.claim');

console.log('service-worker.test.mjs: pass');
