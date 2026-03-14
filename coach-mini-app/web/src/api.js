async function readJson(resp) {
  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  return { data, text };
}

function getApiOrigin() {
  const viteEnv = (import.meta && import.meta.env) ? import.meta.env : {};

  const explicit = String(
    (viteEnv.VITE_API_ORIGIN) ||
    (typeof process !== "undefined" && process.env ? (process.env.VITE_API_ORIGIN || process.env.API_ORIGIN) : "") ||
    ""
  ).trim();
  if (explicit) return explicit.replace(/\/+$/, "");

  // In dev, default to the Express server if we're not already on it.
  // This avoids relying on the Vite dev proxy being configured/running.
  if (typeof window !== "undefined" && viteEnv.DEV && window.location.port !== "3005") {
    return "http://127.0.0.1:3005";
  }

  if (typeof window !== "undefined") {
    return window.location.origin;
  }

  // Node/test fallback.
  return "http://127.0.0.1:3005";
}

function apiUrl(pathname) {
  const origin = getApiOrigin();
  return new URL(pathname, origin).toString();
}

function apiUrlWithOptions(pathname, options) {
  const origin = (options && options.apiOrigin) ? String(options.apiOrigin).trim().replace(/\/+$/, "") : getApiOrigin();
  return new URL(pathname, origin).toString();
}

function apiError(resp, payload) {
  const message = payload?.message || payload?.error || `Request failed (${resp.status})`;
  const err = new Error(message);
  err.status = resp.status;
  err.payload = payload;
  return err;
}

export async function getProfile(options = {}) {
  const url = new URL(apiUrlWithOptions("/api/profile", options));
  const userId = options?.userId || options?.user_id || options?.coachId || options?.coach_id;
  if (typeof userId === "string" && userId.trim()) {
    url.searchParams.set("userId", userId.trim());
  }

  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function updateProfile(profilePatch, options = {}) {
  const url = new URL(apiUrlWithOptions("/api/profile", options));
  const userId = options?.userId || options?.user_id || options?.coachId || options?.coach_id;
  if (typeof userId === "string" && userId.trim()) {
    url.searchParams.set("userId", userId.trim());
  }

  const resp = await fetch(url, {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(profilePatch ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function listAnnouncements(groupId, options = {}) {
  const url = new URL(apiUrlWithOptions("/api/announcements", options));
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcements || [];
}

export async function postAnnouncement({ groupId, text }, options = {}) {
  const resp = await fetch(apiUrlWithOptions("/api/announcements", options), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ groupId, text }),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcement;
}

export async function listMeetings(groupId, options = {}) {
  const url = new URL(apiUrlWithOptions("/api/meetings", options));
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meetings || [];
}

export async function createMeeting(payload, options = {}) {
  const resp = await fetch(apiUrlWithOptions("/api/meetings", options), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meeting;
}

export async function listUsers(options = {}) {
  const resp = await fetch(apiUrlWithOptions("/api/users", options), { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return (data && data.users) || [];
}
