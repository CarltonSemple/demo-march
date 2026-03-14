import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "node:http";
import { createApp } from "../../src/app.js";

function getBaseUrl() {
  const base = process.env.PY_FUNCTION_BASE_URL;
  if (base && base.trim()) return base.trim().replace(/\/+$/, "");

  const projectId = process.env.FIREBASE_PROJECT || process.env.GCLOUD_PROJECT || "coach-app-demo-3132026";
  const region = process.env.FUNCTION_REGION || "us-central1";
  return `http://127.0.0.1:5001/${projectId}/${region}`;
}

test("GET /api/python/hello proxies Python hello", async (t) => {
  process.env.PY_FUNCTION_BASE_URL = getBaseUrl();

  const app = createApp();
  const server = createServer(app);

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  assert.ok(address && typeof address === "object");

  const url = `http://127.0.0.1:${address.port}/api/python/hello?name=Casey`;

  let resp;
  try {
    resp = await fetch(url, { headers: { Accept: "application/json" } });
  } catch (err) {
    const message = `Express server not reachable: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") {
      assert.fail(message);
    }
    t.skip(message);
    return;
  }

  // If the emulator isn't running, the Express route will return a 500/502.
  if (!resp.ok) {
    const body = await resp.text();
    const message = `Python emulator not reachable or returned error (${resp.status}): ${body}`;
    if (process.env.CI === "true") {
      assert.fail(message);
    }
    t.skip(message);
    return;
  }

  const payload = await resp.json();
  assert.equal(payload.source, "python");
  assert.deepEqual(payload.data, { message: "Hello, Casey!" });
});
