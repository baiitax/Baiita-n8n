import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from '../server.mjs';

let server;
let baseUrl;

before(async () => {
  server = createServer();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  baseUrl = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  if (server?.listening) {
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
});

test('serves the interactive dashboard shell', async () => {
  const response = await fetch(baseUrl);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /text\/html/);
  assert.match(await response.text(), /Baiita n8n/);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.match(response.headers.get('content-security-policy'), /script-src 'self'/);
  assert.doesNotMatch(response.headers.get('content-security-policy'), /unsafe-inline/);
});

test('supports HEAD requests without returning an HTML body', async () => {
  const response = await fetch(baseUrl, { method: 'HEAD' });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), '');
});

test('serves the app assets with the expected content types', async () => {
  const [script, stylesheet, icons] = await Promise.all([
    fetch(`${baseUrl}/app.js`),
    fetch(`${baseUrl}/styles.css`),
    fetch(`${baseUrl}/assets/icons.svg`),
  ]);
  assert.equal(script.status, 200);
  assert.match(script.headers.get('content-type'), /javascript/);
  assert.match(await script.text(), /renderOverview/);
  assert.equal(stylesheet.status, 200);
  assert.match(stylesheet.headers.get('content-type'), /text\/css/);
  assert.equal(icons.status, 200);
  assert.match(icons.headers.get('content-type'), /image\/svg\+xml/);
});

test('exposes a non-sensitive health response', async () => {
  const response = await fetch(`${baseUrl}/api/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    status: 'ok',
    service: 'Baiita n8n preview',
    mode: 'demo',
  });
  assert.equal(response.headers.get('cache-control'), 'no-store');
});

test('does not expose files outside the explicit asset allowlist', async () => {
  for (const route of ['/.env', '/server.mjs', '/package.json', '/%2e%2e/.git/config', '/missing']) {
    const response = await fetch(`${baseUrl}${route}`);
    assert.equal(response.status, 404, `${route} should be unavailable`);
  }
});

test('rejects unsupported methods', async () => {
  const response = await fetch(baseUrl, { method: 'POST' });
  assert.equal(response.status, 405);
  assert.equal(response.headers.get('allow'), 'GET, HEAD');
});
