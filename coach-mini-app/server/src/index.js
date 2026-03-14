import { createApp } from "./app.js";

const port = Number.parseInt(process.env.PORT || "3005", 10);

const app = createApp();
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`server listening on http://127.0.0.1:${port}`);
});
