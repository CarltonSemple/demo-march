import React, { useEffect, useMemo, useState } from "react";

import {
  createMeeting,
  getProfile,
  listAnnouncements,
  listMeetings,
  postAnnouncement,
  updateProfile,
} from "./api";

const DEFAULT_GROUP_ID = "demo-group";

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
  const [meetingLink, setMeetingLink] = useState("https://meet.google.com/");
  const [meetingAttendees, setMeetingAttendees] = useState("");
  const [creatingMeeting, setCreatingMeeting] = useState(false);

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
      const p = await getProfile();
      setProfile({
        name: p?.name || "",
        email: p?.email || "",
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
  }, []);

  useEffect(() => {
    if (view !== "announcements") return;
    refreshAnnouncements();
    refreshMeetings();
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
      });
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

    setCreatingMeeting(true);
    setMeetingsError(null);
    try {
      const startsAtIso = meetingDateTimeLocal ? new Date(meetingDateTimeLocal).toISOString() : "";
      await createMeeting({
        groupId,
        title: meetingTitle,
        dateTime: startsAtIso,
        meetLink: meetingLink,
        attendees: meetingAttendeesList,
      });
      setMeetingTitle("");
      setMeetingDateTimeLocal("");
      setMeetingAttendees("");
      await refreshMeetings();
    } catch (e2) {
      setMeetingsError(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setCreatingMeeting(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Coach Mini App</h1>
        <p className="subtle">Profile • Announcements • Meetings (Group: {groupId})</p>

        <nav className="tabs">
          <button
            className={view === "profile" ? "tab tabActive" : "tab"}
            onClick={() => setView("profile")}
            type="button"
          >
            Profile
          </button>
          <button
            className={view === "announcements" ? "tab tabActive" : "tab"}
            onClick={() => setView("announcements")}
            type="button"
          >
            Announcements
          </button>
        </nav>
      </header>

      {view === "profile" ? (
        <main className="card">
          <h2 className="sectionTitle">Coach Profile</h2>

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
              <button className="button buttonSecondary" type="button" onClick={refreshProfile}>
                Reload
              </button>
            </div>
          </form>
        </main>
      ) : (
        <main className="stack">
          <section className="card">
            <h2 className="sectionTitle">Announcements</h2>

            {announcementsError ? <div className="error">{announcementsError}</div> : null}

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

            <div className="row rowBetween">
              <div className="subtle">Visible to group: {groupId}</div>
              <button className="button buttonSecondary" type="button" onClick={refreshAnnouncements}>
                Refresh
              </button>
            </div>

            {announcementsLoading ? <div className="subtle">Loading announcements…</div> : null}

            {announcements.length ? (
              <ul className="list">
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

          <section className="card">
            <h2 className="sectionTitle">Meeting Scheduler</h2>
            {meetingsError ? <div className="error">{meetingsError}</div> : null}

            <form className="grid" onSubmit={onScheduleMeeting}>
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
                />
              </label>

              <label className="label">
                Google Meet link
                <input
                  className="input"
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  placeholder="https://meet.google.com/..."
                />
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

            <div className="row rowBetween">
              <div className="subtle">Upcoming meetings</div>
              <button className="button buttonSecondary" type="button" onClick={refreshMeetings}>
                Refresh
              </button>
            </div>

            {meetingsLoading ? <div className="subtle">Loading meetings…</div> : null}

            {meetings.length ? (
              <ul className="list">
                {meetings.map((m) => (
                  <li key={m.id} className="listItem">
                    <div className="listMain">{m.title}</div>
                    <div className="subtle">{formatDateTime(m.startsAt || m.dateTime)}</div>
                    <a className="link" href={m.meetLink} target="_blank" rel="noreferrer">
                      Join link
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="subtle">No upcoming meetings yet.</div>
            )}
          </section>
        </main>
      )}
    </div>
  );
}
