import test from "node:test";
import assert from "node:assert/strict";

import { createApp } from "../../src/app.js";

function listen(app) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (!addr || typeof addr === "string") {
        reject(new Error("Unexpected server address"));
        return;
      }
      resolve({
        baseUrl: `http://127.0.0.1:${addr.port}`,
        close: () => new Promise((r) => server.close(() => r())),
      });
    });
  });
}

test("GET /health returns ok", async () => {
  const app = createApp();
  const srv = await listen(app);
  try {
    const resp = await fetch(`${srv.baseUrl}/health`);
    assert.equal(resp.status, 200);
    const data = await resp.json();
    assert.deepEqual(data, { ok: true });
  } finally {
    await srv.close();
  }
});

test("GET /api/meetings without groupId returns 400 (no proxy)", async () => {
  const app = createApp();
  const srv = await listen(app);
  try {
    const resp = await fetch(`${srv.baseUrl}/api/meetings`);
    assert.equal(resp.status, 400);
    const data = await resp.json();
    assert.equal(data.error, "missing_group_id");
  } finally {
    await srv.close();
  }
});

test("GET /api/announcements without groupId returns 400 (no proxy)", async () => {
  const app = createApp();
  const srv = await listen(app);
  try {
    const resp = await fetch(`${srv.baseUrl}/api/announcements`);
    assert.equal(resp.status, 400);
    const data = await resp.json();
    assert.equal(data.error, "missing_group_id");
  } finally {
    await srv.close();
  }
});
