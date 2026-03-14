import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "node:http";
import { createApp } from "../../src/app.js";

import { listAnnouncements, postAnnouncement } from "../../../web/src/api.js";

function getPythonBaseUrl() {
  const explicit = process.env.PY_FUNCTION_BASE_URL;
  if (explicit && explicit.trim()) return explicit.trim().replace(/\/+$/, "");

  const projectId = process.env.FIREBASE_PROJECT || process.env.GCLOUD_PROJECT || "coach-app-demo-3132026";
  const region = process.env.FUNCTION_REGION || "us-central1";
  return `http://127.0.0.1:5001/${projectId}/${region}`;
}

function uniqueGroupId() {
  return `itest-ann-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

test("Web API post announcement reaches Express → Cloud Function", async (t) => {
  process.env.PY_FUNCTION_BASE_URL = getPythonBaseUrl();

  const app = createApp();
  const server = createServer(app);

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  assert.ok(address && typeof address === "object");
  const apiOrigin = `http://127.0.0.1:${address.port}`;

  const groupId = uniqueGroupId();
  const text = `Integration announcement ${Date.now()}`;

  let created;
  try {
    created = await postAnnouncement({ groupId, text }, { apiOrigin });
  } catch (err) {
    const message = `postAnnouncement failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  assert.ok(created && created.id, "Expected announcement to have id");
  assert.equal(created.groupId, groupId);
  assert.equal(created.text, text);

  let items;
  try {
    items = await listAnnouncements(groupId, { apiOrigin });
  } catch (err) {
    const message = `listAnnouncements failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  assert.ok(Array.isArray(items));
  const ids = items.map((a) => a.id);
  assert.ok(ids.includes(created.id), "Expected created announcement to appear in listAnnouncements results");
});
