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

  return app;
}
