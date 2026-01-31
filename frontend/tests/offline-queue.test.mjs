/**
 * Offline Queue Tests
 * Verify offline-queue.js exports required functions
 */

import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(__dirname, '..');

// Test offline-queue.js exists
const queuePath = join(frontendDir, 'offline-queue.js');
assert.ok(existsSync(queuePath), 'offline-queue.js should exist');

// Read and validate content
const queueContent = readFileSync(queuePath, 'utf8');

// Check for required exports
assert.ok(queueContent.includes('export async function queueCapture'),
  'should export queueCapture function');
assert.ok(queueContent.includes('export async function getPendingCaptures'),
  'should export getPendingCaptures function');
assert.ok(queueContent.includes('export async function getPendingCount'),
  'should export getPendingCount function');
assert.ok(queueContent.includes('export async function removePendingCapture'),
  'should export removePendingCapture function');
assert.ok(queueContent.includes('export async function syncPendingCaptures'),
  'should export syncPendingCaptures function');
assert.ok(queueContent.includes('export function isOnline'),
  'should export isOnline function');
assert.ok(queueContent.includes('export function setupAutoSync'),
  'should export setupAutoSync function');

// Check for IndexedDB setup
assert.ok(queueContent.includes('indexedDB'), 'should use IndexedDB');
assert.ok(queueContent.includes('DB_NAME'), 'should define DB_NAME');
assert.ok(queueContent.includes('STORE_NAME'), 'should define STORE_NAME');

// Check for localStorage fallback
assert.ok(queueContent.includes('localStorage'), 'should have localStorage fallback');

// Check for event dispatching
assert.ok(queueContent.includes('custos-pending-change'),
  'should dispatch pending-change event');
assert.ok(queueContent.includes('custos-sync-complete'),
  'should dispatch sync-complete event');

// Check for online/offline handling
assert.ok(queueContent.includes("addEventListener('online'"),
  'should listen for online event');
assert.ok(queueContent.includes('navigator.onLine'),
  'should check navigator.onLine');

console.log('offline-queue.test.mjs: pass');
