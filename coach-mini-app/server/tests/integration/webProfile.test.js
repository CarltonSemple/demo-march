import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "node:http";
import { createApp } from "../../src/app.js";

import { getProfile, listUsers, updateProfile } from "../../../web/src/api.js";

function getPythonBaseUrl() {
  const explicit = process.env.PY_FUNCTION_BASE_URL;
  if (explicit && explicit.trim()) return explicit.trim().replace(/\/+$/, "");

  const projectId = process.env.FIREBASE_PROJECT || process.env.GCLOUD_PROJECT || "coach-app-demo-3132026";
  const region = process.env.FUNCTION_REGION || "us-central1";
  return `http://127.0.0.1:5001/${projectId}/${region}`;
}

function uniqueUserId() {
  return `itest-user-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

test("Web API save profile reaches Express → Cloud Function", async (t) => {
  process.env.PY_FUNCTION_BASE_URL = getPythonBaseUrl();

  const app = createApp();
  const server = createServer(app);

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  assert.ok(address && typeof address === "object");
  const apiOrigin = `http://127.0.0.1:${address.port}`;

  const userId = uniqueUserId();

  // Seed a user record (the profile endpoint should keep this in sync).
  try {
    const pythonBaseUrl = getPythonBaseUrl();
    const resp = await fetch(`${pythonBaseUrl}/createUser`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        id: userId,
        email: `seed.${Date.now()}@example.com`,
        role: "member",
        displayName: "Seed User",
      }),
    });

    if (!resp.ok) {
      const raw = await resp.text();
      throw new Error(`createUser failed: ${resp.status} ${raw}`);
    }
  } catch (err) {
    const message = `createUser seed failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  const patch = {
    name: `Integration Coach ${Date.now()}`,
    email: `integration.${Date.now()}@example.com`,
    bio: "Integration test bio",
  };

  let saved;
  try {
    saved = await updateProfile(patch, { apiOrigin, userId });
  } catch (err) {
    const message = `updateProfile failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  assert.equal(saved.userId, userId);
  assert.equal(saved.name, patch.name);
  assert.equal(saved.email, patch.email.toLowerCase());
  assert.equal(saved.bio, patch.bio);

  let loaded;
  try {
    loaded = await getProfile({ apiOrigin, userId });
  } catch (err) {
    const message = `getProfile failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  assert.equal(loaded.userId, userId);
  assert.equal(loaded.name, patch.name);
  assert.equal(loaded.email, patch.email.toLowerCase());
  assert.equal(loaded.bio, patch.bio);

  // Email and displayName are duplicated in users/*; ensure we keep them in sync.
  let users;
  try {
    users = await listUsers({ apiOrigin });
  } catch (err) {
    const message = `listUsers failed: ${err instanceof Error ? err.message : String(err)}`;
    if (process.env.CI === "true") assert.fail(message);
    t.skip(message);
    return;
  }

  const u = users.find((x) => x.id === userId);
  assert.ok(u, "Expected seeded user to appear in listUsers");
  assert.equal(u.email, patch.email.toLowerCase());
  assert.equal(u.displayName, patch.name);
});
