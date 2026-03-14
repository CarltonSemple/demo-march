import express from "express";

function getPythonFunctionBaseUrl() {
  const explicit = (process.env.PY_FUNCTION_BASE_URL || "").trim();
  if (explicit) return explicit;

  const projectId =
    (process.env.FIREBASE_PROJECT || "").trim() ||
    (process.env.GCLOUD_PROJECT || "").trim() ||
    "coach-app-demo-3132026";
  const region = (process.env.FUNCTION_REGION || "").trim() || "us-central1";
  return `http://127.0.0.1:5001/${projectId}/${region}`;
}

export function createApp() {
  const app = express();

  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.status(200).json({ ok: true });
  });

  // Proxies the Python Cloud Function `hello`.
  // GET /api/python/hello?name=Casey
  app.get("/api/python/hello", async (req, res) => {
    try {
      const pythonBaseUrl = getPythonFunctionBaseUrl();

      const url = new URL(pythonBaseUrl.replace(/\/+$/, "") + "/hello");
      if (typeof req.query.name === "string" && req.query.name.trim()) {
        url.searchParams.set("name", req.query.name.trim());
      }

      const resp = await fetch(url, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      const contentType = resp.headers.get("content-type") || "";
      const rawBody = await resp.text();

      if (!resp.ok) {
        return res.status(502).json({
          error: "python_function_error",
          status: resp.status,
          body: rawBody,
        });
      }

      if (!contentType.startsWith("application/json")) {
        return res.status(502).json({
          error: "python_function_non_json",
          contentType,
          body: rawBody,
        });
      }

      const data = JSON.parse(rawBody);
      return res.status(200).json({
        source: "python",
        data,
      });
    } catch (err) {
      return res.status(500).json({
        error: "internal_error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  });

  // Meetings API (Express) -> Meetings Cloud Function (Python)
  app.get("/meetings", async (req, res) => {
    try {
      const pythonBaseUrl = getPythonFunctionBaseUrl();
      const url = new URL(pythonBaseUrl.replace(/\/+$/, "") + "/meetings");

      const groupId = typeof req.query.groupId === "string" ? req.query.groupId.trim() : "";
      if (!groupId) {
        return res.status(400).json({ error: "missing_group_id", message: "groupId is required" });
      }
      url.searchParams.set("groupId", groupId);

      const resp = await fetch(url, { headers: { Accept: "application/json" } });
      const rawBody = await resp.text();

      if (!resp.ok) {
        return res.status(502).json({
          error: "python_function_error",
          status: resp.status,
          body: rawBody,
        });
      }

      return res.status(200).json(JSON.parse(rawBody));
    } catch (err) {
      return res.status(500).json({
        error: "internal_error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  });

  app.post("/meetings", async (req, res) => {
    try {
      const pythonBaseUrl = getPythonFunctionBaseUrl();
      const url = new URL(pythonBaseUrl.replace(/\/+$/, "") + "/meetings");

      const resp = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(req.body ?? {}),
      });

      const rawBody = await resp.text();
      const contentType = resp.headers.get("content-type") || "";

      if (!contentType.startsWith("application/json")) {
        return res.status(502).json({
          error: "python_function_non_json",
          status: resp.status,
          body: rawBody,
        });
      }

      if (!resp.ok) {
        return res.status(502).json(JSON.parse(rawBody));
      }

      return res.status(201).json(JSON.parse(rawBody));
    } catch (err) {
      return res.status(500).json({
        error: "internal_error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  });

  return app;
}
