async function readJson(resp) {
  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  return { data, text };
}

function apiError(resp, payload) {
  const message = payload?.message || payload?.error || `Request failed (${resp.status})`;
  const err = new Error(message);
  err.status = resp.status;
  err.payload = payload;
  return err;
}

export async function getProfile() {
  const resp = await fetch("/api/profile", { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function updateProfile(profilePatch) {
  const resp = await fetch("/api/profile", {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(profilePatch ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.profile;
}

export async function listAnnouncements(groupId) {
  const url = new URL("/api/announcements", window.location.origin);
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcements || [];
}

export async function postAnnouncement({ groupId, text }) {
  const resp = await fetch("/api/announcements", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ groupId, text }),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.announcement;
}

export async function listMeetings(groupId) {
  const url = new URL("/api/meetings", window.location.origin);
  url.searchParams.set("groupId", groupId);
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meetings || [];
}

export async function createMeeting(payload) {
  const resp = await fetch("/api/meetings", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  const { data } = await readJson(resp);
  if (!resp.ok) throw apiError(resp, data);
  return data.meeting;
}
