import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "node:http";
import { createApp } from "../../src/app.js";

function getPythonBaseUrl() {
  const explicit = process.env.PY_FUNCTION_BASE_URL;
  if (explicit && explicit.trim()) return explicit.trim().replace(/\/+$/, "");

  const projectId = process.env.FIREBASE_PROJECT || process.env.GCLOUD_PROJECT || "coach-app-demo-3132026";
  const region = process.env.FUNCTION_REGION || "us-central1";
  return `http://127.0.0.1:5001/${projectId}/${region}`;
}

function uniqueGroupId() {
  return `itest-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

test("POST /meetings then GET /meetings returns upcoming meeting", async (t) => {
  process.env.PY_FUNCTION_BASE_URL = getPythonBaseUrl();

  const app = createApp();
  const server = createServer(app);

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  assert.ok(address && typeof address === "object");
  const baseUrl = `http://127.0.0.1:${address.port}`;

  const groupId = uniqueGroupId();
  const startsAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

  const createPayload = {
    groupId,
    title: "Express Integration Meeting",
    dateTime: startsAt,
    meetLink: "https://meet.google.com/abc-defg-hij",
    attendees: ["a@example.com"],
  };

  const createResp = await fetch(`${baseUrl}/meetings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(createPayload),
  });

  if (!createResp.ok) {
    const body = await createResp.text();
    const message = `Create failed (${createResp.status}): ${body}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  const createBody = await createResp.json();
  assert.ok(createBody.meeting?.id);
  assert.equal(createBody.meeting.groupId, groupId);

  const listResp = await fetch(`${baseUrl}/meetings?groupId=${encodeURIComponent(groupId)}`, {
    headers: { Accept: "application/json" },
  });

  if (!listResp.ok) {
    const body = await listResp.text();
    const message = `List failed (${listResp.status}): ${body}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  const listBody = await listResp.json();
  assert.equal(listBody.groupId, groupId);
  assert.ok(Array.isArray(listBody.meetings));

  const ids = listBody.meetings.map((m) => m.id);
  assert.ok(ids.includes(createBody.meeting.id));
});
