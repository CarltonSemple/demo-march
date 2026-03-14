import React, { useEffect, useMemo, useRef, useState } from "react";

import {
  createMeeting,
  getProfile,
  listAnnouncements,
  listMeetings,
  listUsers,
  postAnnouncement,
  updateProfile,
} from "./api";

const DEFAULT_GROUP_ID = "demo-group";
const MEET_LINK_PREFIX = "https://meet.google.com/";

function formatDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.onload = () => resolve(String(reader.result || ""));
    reader.readAsDataURL(file);
  });
}

export default function App() {
  const [view, setView] = useState("profile");

  // User selector
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState(null);
  const [users, setUsers] = useState([]);
  const [activeUserId, setActiveUserId] = useState(() => {
    try {
      return window.localStorage.getItem("activeUserId") || "";
    } catch {
      return "";
    }
  });

  const activeUser = useMemo(() => {
    if (!activeUserId) return null;
    return users.find((u) => u?.id === activeUserId) || null;
  }, [users, activeUserId]);

  const canPostAnnouncements = (activeUser?.role || "").toLowerCase() === "coach";

  const activeProfileUserId = activeUserId || "default";

  // Coach Profile
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState(null);
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    bio: "",
    avatarDataUrl: "",
  });

  // Announcements
  const groupId = DEFAULT_GROUP_ID;
  const [announcementsLoading, setAnnouncementsLoading] = useState(false);
  const [announcementsError, setAnnouncementsError] = useState(null);
  const [announcements, setAnnouncements] = useState([]);
  const [announcementText, setAnnouncementText] = useState("");
  const [postingAnnouncement, setPostingAnnouncement] = useState(false);

  // Meetings
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [meetingsError, setMeetingsError] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDateTimeLocal, setMeetingDateTimeLocal] = useState("");
  const [meetingLinkSuffix, setMeetingLinkSuffix] = useState("");
  const [meetingAttendees, setMeetingAttendees] = useState("");
  const [creatingMeeting, setCreatingMeeting] = useState(false);

  const scheduleMeetingInFlightRef = useRef(false);
  const scheduleMeetingIdempotencyKeyRef = useRef("");

  const meetingAttendeesList = useMemo(() => {
    return meetingAttendees
      .split(/[,\n]/g)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [meetingAttendees]);

  async function refreshProfile() {
    setProfileLoading(true);
    setProfileError(null);
    try {
      const p = await getProfile({ userId: activeProfileUserId });
      setProfile({
        name: p?.name || activeUser?.displayName || "",
        email: p?.email || activeUser?.email || "",
        bio: p?.bio || "",
        avatarDataUrl: p?.avatarDataUrl || "",
      });
    } catch (e) {
      setProfileError(e instanceof Error ? e.message : String(e));
    } finally {
      setProfileLoading(false);
    }
  }

  async function refreshAnnouncements() {
    setAnnouncementsLoading(true);
    setAnnouncementsError(null);
    try {
      const items = await listAnnouncements(groupId);
      setAnnouncements(items);
    } catch (e) {
      setAnnouncementsError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnnouncementsLoading(false);
    }
  }

  async function refreshMeetings() {
    setMeetingsLoading(true);
    setMeetingsError(null);
    try {
      const items = await listMeetings(groupId);
      setMeetings(items);
    } catch (e) {
      setMeetingsError(e instanceof Error ? e.message : String(e));
    } finally {
      setMeetingsLoading(false);
    }
  }

  useEffect(() => {
    refreshProfile();
  }, [activeProfileUserId, activeUser?.displayName, activeUser?.email]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setUsersLoading(true);
      setUsersError(null);
      try {
        const items = await listUsers();
        if (cancelled) return;
        setUsers(items);

        setActiveUserId((prev) => {
          const existing = (prev || "").trim();
          const existingStillThere = Array.isArray(items) && existing ? items.some((u) => u?.id === existing) : false;
          const next = existingStillThere ? existing : (items?.[0]?.id || "");
          try {
            if (next) window.localStorage.setItem("activeUserId", next);
          } catch {
            // ignore
          }
          return next;
        });
      } catch (e) {
        if (cancelled) return;
        setUsersError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setUsersLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (view === "announcements") {
      refreshAnnouncements();
    }
    if (view === "meetings") {
      refreshMeetings();
    }
  }, [view]);

  async function onSaveProfile(e) {
    e.preventDefault();
    setProfileSaving(true);
    setProfileError(null);
    try {
      const saved = await updateProfile({
        name: profile.name,
        email: profile.email,
        bio: profile.bio,
        avatarDataUrl: profile.avatarDataUrl || "",
      }, { userId: activeProfileUserId });
      setProfile({
        name: saved?.name || "",
        email: saved?.email || "",
        bio: saved?.bio || "",
        avatarDataUrl: saved?.avatarDataUrl || "",
      });
    } catch (e2) {
      setProfileError(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setProfileSaving(false);
    }
  }

  async function onSelectAvatar(file) {
    if (!file) return;
    const dataUrl = await readFileAsDataUrl(file);
    setProfile((p) => ({ ...p, avatarDataUrl: dataUrl }));
  }

  async function onPostAnnouncement(e) {
    e.preventDefault();
    const text = announcementText.trim();
    if (!text) return;

    setPostingAnnouncement(true);
    setAnnouncementsError(null);
    try {
      await postAnnouncement({ groupId, text });
      setAnnouncementText("");
      await refreshAnnouncements();
    } catch (e2) {
      setAnnouncementsError(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setPostingAnnouncement(false);
    }
  }

  async function onScheduleMeeting(e) {
    e.preventDefault();

    if (scheduleMeetingInFlightRef.current) return;
    scheduleMeetingInFlightRef.current = true;

    setCreatingMeeting(true);
    setMeetingsError(null);
    try {
      const startsAtIso = meetingDateTimeLocal ? new Date(meetingDateTimeLocal).toISOString() : "";

      if (!scheduleMeetingIdempotencyKeyRef.current) {
        const uuid = (typeof crypto !== "undefined" && crypto && typeof crypto.randomUUID === "function")
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        scheduleMeetingIdempotencyKeyRef.current = `schedule-${uuid}`;
      }

      let suffix = meetingLinkSuffix.trim();
      if (suffix.toLowerCase().startsWith(MEET_LINK_PREFIX)) {
        suffix = suffix.slice(MEET_LINK_PREFIX.length);
      }
      suffix = suffix.replace(/^\/+/, "");

      await createMeeting({
        groupId,
        title: meetingTitle,
        dateTime: startsAtIso,
        meetLink: `${MEET_LINK_PREFIX}${suffix}`,
        attendees: meetingAttendeesList,
        idempotencyKey: scheduleMeetingIdempotencyKeyRef.current,
      });
      setMeetingTitle("");
      setMeetingDateTimeLocal("");
      setMeetingLinkSuffix("");
      setMeetingAttendees("");
      scheduleMeetingIdempotencyKeyRef.current = "";
      await refreshMeetings();
    } catch (e2) {
      setMeetingsError(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setCreatingMeeting(false);
      scheduleMeetingInFlightRef.current = false;
    }
  }

  return (
    <div className="appShell">
      <aside className="sidebar" aria-label="Sidebar">
        <div className="sidebarHeader">
          <div>
            <div className="brand">Coach Mini App</div>
            <div className="subtle">Coach tools</div>
          </div>

          <div className="pill" title="Active group">
            Group: <span className="pillValue">{groupId}</span>
          </div>
        </div>

        <nav className="nav" aria-label="Primary">
          <button
            className={view === "profile" ? "navButton navButtonActive" : "navButton"}
            onClick={() => setView("profile")}
            type="button"
            aria-current={view === "profile" ? "page" : undefined}
          >
            Profile
          </button>
          <button
            className={view === "announcements" ? "navButton navButtonActive" : "navButton"}
            onClick={() => setView("announcements")}
            type="button"
            aria-current={view === "announcements" ? "page" : undefined}
          >
            Announcements
          </button>
          <button
            className={view === "meetings" ? "navButton navButtonActive" : "navButton"}
            onClick={() => setView("meetings")}
            type="button"
            aria-current={view === "meetings" ? "page" : undefined}
          >
            Meetings
          </button>
        </nav>

        <div className="sidebarFooter" aria-label="User selector">
          <div className="sidebarFooterTitle">User</div>

          {usersLoading ? <div className="subtle">Loading…</div> : null}
          {usersError ? (
            <div className="subtle" title={usersError}>
              Users unavailable
            </div>
          ) : null}

          {!usersLoading && !usersError ? (
            <select
              className="sidebarSelect"
              value={activeUserId || ""}
              onChange={(e) => {
                const next = e.target.value;
                setActiveUserId(next);
                try {
                  window.localStorage.setItem("activeUserId", next);
                } catch {
                  // ignore
                }
              }}
            >
              {users.length === 0 ? <option value="">No users found</option> : null}
              {users.map((u) => {
                const label = (u?.displayName || "").trim() || (u?.email || "").trim() || u?.id;
                const role = (u?.role || "").trim();
                return (
                  <option key={u.id} value={u.id}>
                    {label}{role ? ` (${role})` : ""}
                  </option>
                );
              })}
            </select>
          ) : null}
        </div>
      </aside>

      <div className="content">
        <div className="page">
          {view === "profile" ? (
            <main className="card cardProfile">
          <div className="row rowBetween">
            <h2 className="sectionTitle">Profile</h2>
            <button className="button buttonSecondary" type="button" onClick={refreshProfile}>
              Reload
            </button>
          </div>

          {profileError ? <div className="error">{profileError}</div> : null}
          {profileLoading ? <div className="subtle">Loading profile…</div> : null}

          <form className="grid" onSubmit={onSaveProfile}>
            <label className="label">
              Name
              <input
                className="input"
                value={profile.name}
                onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                placeholder="Your name"
                autoComplete="name"
              />
            </label>

            <label className="label">
              Email
              <input
                className="input"
                value={profile.email}
                onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </label>

            <label className="label">
              Bio
              <textarea
                className="input textarea"
                value={profile.bio}
                onChange={(e) => setProfile((p) => ({ ...p, bio: e.target.value }))}
                placeholder="A short bio…"
                rows={4}
              />
            </label>

            <div className="row">
              <div className="avatarBlock">
                <div className="label">Avatar</div>
                {profile.avatarDataUrl ? (
                  <img className="avatar" src={profile.avatarDataUrl} alt="Avatar preview" />
                ) : (
                  <div className="avatarPlaceholder">No avatar</div>
                )}
              </div>

              <div className="grid" style={{ alignContent: "start" }}>
                <input
                  className="input"
                  type="file"
                  accept="image/*"
                  onChange={(e) => onSelectAvatar(e.target.files?.[0] || null)}
                />
                <button
                  type="button"
                  className="button buttonSecondary"
                  onClick={() => setProfile((p) => ({ ...p, avatarDataUrl: "" }))}
                  disabled={!profile.avatarDataUrl}
                >
                  Remove avatar
                </button>
              </div>
            </div>

            <div className="row">
              <button className="button" type="submit" disabled={profileSaving}>
                {profileSaving ? "Saving…" : "Save profile"}
              </button>
            </div>
          </form>
            </main>
          ) : null}

          {view === "announcements" ? (
            <main className="stack">
          <section className="card cardNoBorder">
            <div className="row rowBetween">
              <h2 className="sectionTitle">Announcements</h2>
              <button className="button buttonSecondary" type="button" onClick={refreshAnnouncements}>
                Refresh
              </button>
            </div>

            {announcementsError ? <div className="error">{announcementsError}</div> : null}

            {canPostAnnouncements ? (
              <form className="grid" onSubmit={onPostAnnouncement}>
                <label className="label">
                  Post an announcement
                  <textarea
                    className="input textarea"
                    value={announcementText}
                    onChange={(e) => setAnnouncementText(e.target.value)}
                    placeholder="Type an announcement for your group…"
                    rows={3}
                  />
                </label>

                <button className="button" type="submit" disabled={postingAnnouncement}>
                  {postingAnnouncement ? "Posting…" : "Post"}
                </button>
              </form>
            ) : null}

            <div className="subtle">{canPostAnnouncements ? `Visible to group: ${groupId}` : groupId}</div>

            {announcementsLoading ? <div className="subtle">Loading announcements…</div> : null}

            {announcements.length ? (
              <ul className="list listAnnouncements">
                {announcements.map((a) => (
                  <li key={a.id} className="listItem">
                    <div className="listMain">{a.text}</div>
                    <div className="subtle">{formatDateTime(a.createdAt)}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="subtle">No announcements yet.</div>
            )}
          </section>
            </main>
          ) : null}

          {view === "meetings" ? (
            <main className="stack">
          <section className="card cardNoBorder">
            <div className="row rowBetween">
              <h2 className="sectionTitle">Meetings</h2>
              <button className="button buttonSecondary" type="button" onClick={refreshMeetings}>
                Refresh
              </button>
            </div>

            {meetingsError ? <div className="error">{meetingsError}</div> : null}

            <div className="split">
              <form className="grid" onSubmit={onScheduleMeeting}>
                <div className="subtle">Schedule a new meeting</div>
                <label className="label">
                  Title
                  <input
                    className="input"
                    value={meetingTitle}
                    onChange={(e) => setMeetingTitle(e.target.value)}
                    placeholder="Weekly check-in"
                  />
                </label>

                <label className="label">
                  Date / time
                  <input
                    className="input"
                    type="datetime-local"
                    value={meetingDateTimeLocal}
                    onChange={(e) => setMeetingDateTimeLocal(e.target.value)}
                    onMouseDown={(e) => {
                      try {
                        e.currentTarget.showPicker?.();
                      } catch {
                        // ignore (not supported)
                      }
                    }}
                    onTouchStart={(e) => {
                      try {
                        e.currentTarget.showPicker?.();
                      } catch {
                        // ignore (not supported)
                      }
                    }}
                  />
                </label>

                <label className="label">
                  Google Meet link
                  <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                    <span>{MEET_LINK_PREFIX}</span>
                    <input
                      className="input"
                      value={meetingLinkSuffix}
                      onChange={(e) => setMeetingLinkSuffix(e.target.value)}
                      placeholder="abc-defg-hij"
                      aria-label="Meet link code"
                      style={{ width: 160 }}
                    />
                  </div>
                </label>

                <label className="label">
                  Attendees (comma-separated)
                  <textarea
                    className="input textarea"
                    value={meetingAttendees}
                    onChange={(e) => setMeetingAttendees(e.target.value)}
                    placeholder="a@example.com, b@example.com"
                    rows={2}
                  />
                </label>

                <button className="button" type="submit" disabled={creatingMeeting}>
                  {creatingMeeting ? "Scheduling…" : "Schedule meeting"}
                </button>
              </form>

              <div className="grid" style={{ alignContent: "start" }}>
                <div className="subtle">Upcoming meetings</div>

                {meetingsLoading ? <div className="subtle">Loading meetings…</div> : null}

                {meetings.length ? (
                  <ul className="list listMeetings">
                    {meetings.map((m) => (
                      <li key={m.id} className="listItem">
                        <div className="listMain">{m.title}</div>
                        <div className="subtle">{formatDateTime(m.startsAt || m.dateTime)}</div>
                        <div className="subtle">
                          Attendees: {Array.isArray(m.attendees) && m.attendees.length ? m.attendees.join(", ") : "—"}
                        </div>
                        <a className="link" href={m.meetLink} target="_blank" rel="noreferrer">
                          Join link
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="subtle">No upcoming meetings yet.</div>
                )}
              </div>
            </div>
          </section>
            </main>
          ) : null}
        </div>
      </div>
    </div>
  );
}
