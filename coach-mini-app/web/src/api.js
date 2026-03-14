async function readJson(resp) {
  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  return { data, text };
}

function getApiOrigin() {
  const explicit = String(import.meta.env.VITE_API_ORIGIN || "").trim();
  if (explicit) return explicit.replace(/\/+$/, "");

  // In dev, default to the Express server if we're not already on it.
  // This avoids relying on the Vite dev proxy being configured/running.
  if (import.meta.env.DEV && window.location.port !== "3005") {
    return "http://127.0.0.1:3005";
  }

  return window.location.origin;
}

function apiUrl(pathname) {
  const origin = getApiOrigin();
  return new URL(pathname, origin).toString();
}

function apiError(resp, payload) {
  const message = payload?.message || payload?.error || `Request failed (${resp.status})`;
  const err = new Error(message);
  err.status = resp.status;
  err.payload = payload;
  return err;
}

export async function getProfile() {
  const resp = await fetch(apiUrl("/api/profile"), { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function updateProfile(profilePatch) {
  const resp = await fetch(apiUrl("/api/profile"), {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(profilePatch ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function listAnnouncements(groupId) {
  const url = new URL(apiUrl("/api/announcements"));
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcements || [];
}

export async function postAnnouncement({ groupId, text }) {
  const resp = await fetch(apiUrl("/api/announcements"), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ groupId, text }),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcement;
}

export async function listMeetings(groupId) {
  const url = new URL(apiUrl("/api/meetings"));
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meetings || [];
}

export async function createMeeting(payload) {
  const resp = await fetch(apiUrl("/api/meetings"), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meeting;
}

export async function listUsers() {
  const resp = await fetch(apiUrl("/api/users"), { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return (data && data.users) || [];
}
