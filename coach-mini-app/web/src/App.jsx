import React, { useState } from "react";

export default function App() {
  const [name, setName] = useState("Casey");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function callBackend() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const url = new URL("/api/python/hello", window.location.origin);
      if (name.trim()) url.searchParams.set("name", name.trim());

      const resp = await fetch(url, { headers: { Accept: "application/json" } });
      const body = await resp.json().catch(() => null);

      if (!resp.ok) {
        throw new Error(body?.error || `Request failed (${resp.status})`);
      }

      setResult(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Coach Mini App</h1>
        <p className="subtle">Quick smoke test for Express → Python Cloud Function</p>
      </header>

      <main className="card">
        <label className="label">
          Name
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Casey"
          />
        </label>

        <button className="button" onClick={callBackend} disabled={loading}>
          {loading ? "Calling…" : "Call backend"}
        </button>

        {error ? <div className="error">{error}</div> : null}

        {result ? (
          <pre className="pre">{JSON.stringify(result, null, 2)}</pre>
        ) : (
          <div className="subtle">Result will show here.</div>
        )}
      </main>
    </div>
  );
}
