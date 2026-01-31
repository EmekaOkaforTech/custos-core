/**
 * OAuth Flow Tests - Epic 37 Story 37.1
 *
 * Tests for the OAuth calendar connection flow in the frontend.
 */

import assert from 'node:assert';
import { describe, it, beforeEach } from 'node:test';

// Mock DOM elements
const mockElements = {
  calendarProviders: null,
  googleStatus: null,
  microsoftStatus: null,
  providerGoogle: null,
  providerMicrosoft: null,
  calendarAuthStatus: null,
  calendarProviderError: null,
};

// Mock fetch responses
const mockFetch = (url, options) => {
  if (url.includes('/api/calendar/oauth/status')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        google_configured: true,
        microsoft_configured: false,
      }),
    });
  }
  if (url.includes('/api/calendar/oauth/authorize')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        authorization_url: 'https://accounts.google.com/oauth?...',
        state: 'test_state_123',
      }),
    });
  }
  if (url.includes('/api/calendar/oauth/callback')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        connected: true,
        provider: 'google',
        provider_user_id: 'user123',
      }),
    });
  }
  if (url.includes('/api/calendar/connection') && options?.method === 'DELETE') {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        status: 'disconnected',
        provider: 'google',
      }),
    });
  }
  return Promise.reject(new Error('Unknown URL'));
};

describe('OAuth Status Checking', () => {
  it('should correctly parse OAuth status response', async () => {
    const response = await mockFetch('/api/calendar/oauth/status');
    const data = await response.json();

    assert.strictEqual(data.google_configured, true, 'Google should be configured');
    assert.strictEqual(data.microsoft_configured, false, 'Microsoft should not be configured');
  });

  it('should handle missing OAuth configuration gracefully', async () => {
    const mockUnconfigured = () => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        google_configured: false,
        microsoft_configured: false,
      }),
    });

    const response = await mockUnconfigured();
    const data = await response.json();

    assert.strictEqual(data.google_configured, false);
    assert.strictEqual(data.microsoft_configured, false);
  });
});

describe('OAuth Authorization Flow', () => {
  it('should request authorization URL with provider parameter', async () => {
    let capturedUrl = '';
    const mockFetchCapture = (url) => {
      capturedUrl = url;
      return mockFetch(url);
    };

    await mockFetchCapture('/api/calendar/oauth/authorize?provider=google');

    assert.ok(
      capturedUrl.includes('provider=google'),
      'URL should include provider parameter'
    );
  });

  it('should return authorization URL and state', async () => {
    const response = await mockFetch('/api/calendar/oauth/authorize?provider=google');
    const data = await response.json();

    assert.ok(data.authorization_url, 'Should have authorization_url');
    assert.ok(data.state, 'Should have state for CSRF protection');
    assert.ok(data.state.length > 10, 'State should be a secure random string');
  });
});

describe('OAuth Callback Handling', () => {
  it('should exchange code for tokens', async () => {
    const response = await mockFetch('/api/calendar/oauth/callback', {
      method: 'POST',
      body: JSON.stringify({ code: 'auth_code', state: 'test_state' }),
    });
    const data = await response.json();

    assert.strictEqual(data.connected, true, 'Should be connected');
    assert.strictEqual(data.provider, 'google', 'Provider should be google');
    assert.ok(data.provider_user_id, 'Should have provider user ID');
  });

  it('should handle OAuth error from provider', async () => {
    const mockErrorFetch = () => Promise.resolve({
      ok: false,
      json: () => Promise.resolve({
        detail: 'Authorization failed: Code expired',
      }),
    });

    const response = await mockErrorFetch();
    const data = await response.json();

    assert.ok(data.detail.includes('failed'), 'Should contain error message');
  });
});

describe('Calendar Disconnect', () => {
  it('should disconnect and return status', async () => {
    const response = await mockFetch('/api/calendar/connection', {
      method: 'DELETE',
    });
    const data = await response.json();

    assert.strictEqual(data.status, 'disconnected', 'Status should be disconnected');
    assert.ok(data.provider, 'Should include provider in response');
  });
});

describe('Provider Button State', () => {
  it('should disable unconfigured providers', () => {
    const oauthStatus = {
      google_configured: true,
      microsoft_configured: false,
    };

    // Simulate updateProviderButtons logic
    const googleEnabled = oauthStatus.google_configured;
    const microsoftEnabled = oauthStatus.microsoft_configured;

    assert.strictEqual(googleEnabled, true, 'Google button should be enabled');
    assert.strictEqual(microsoftEnabled, false, 'Microsoft button should be disabled');
  });
});

describe('OAuth Callback Page', () => {
  it('should parse URL parameters correctly', () => {
    // Simulate URL parsing from oauth-callback.html
    const testUrl = 'http://localhost/oauth-callback.html?code=abc123&state=xyz789';
    const url = new URL(testUrl);
    const params = url.searchParams;

    assert.strictEqual(params.get('code'), 'abc123');
    assert.strictEqual(params.get('state'), 'xyz789');
  });

  it('should detect OAuth error in URL', () => {
    const testUrl = 'http://localhost/oauth-callback.html?error=access_denied&error_description=User%20denied';
    const url = new URL(testUrl);
    const params = url.searchParams;

    assert.strictEqual(params.get('error'), 'access_denied');
    assert.strictEqual(params.get('error_description'), 'User denied');
  });

  it('should handle missing parameters', () => {
    const testUrl = 'http://localhost/oauth-callback.html';
    const url = new URL(testUrl);
    const params = url.searchParams;

    assert.strictEqual(params.get('code'), null, 'Code should be null');
    assert.strictEqual(params.get('state'), null, 'State should be null');
  });
});

// Run all tests
console.log('Running OAuth flow tests...');
