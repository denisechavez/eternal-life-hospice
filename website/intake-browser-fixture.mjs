// Test-only HTTP fixture. Never imports devserver, database, Brevo or credentials.
import {createServer} from "node:http";
import {readFile} from "node:fs/promises";
import {resolve, extname, sep} from "node:path";

export const turnstileFixture = `
window.turnstile = {
  render(container, options) {
    if (options.action !== "intake" || options.appearance !== "interaction-only")
      throw new Error("Unexpected Turnstile contract");
    const f = window.intakeFixture;
    f.renders++;
    const button = document.createElement("button");
    button.type = "button";
    button.id = "fixture-challenge";
    button.textContent = "Verify you are human (test fixture)";
    button.style.cssText = "display:block;width:260px;max-width:100%;min-height:64px";
    button.addEventListener("click", () => {
      if (f.challenge === "error") options["error-callback"]();
      else if (f.challenge === "expired") options["expired-callback"]();
      else options.callback("synthetic-provider-token");
    });
    container.appendChild(button);
    return "fixture-widget";
  },
  remove() { window.intakeFixture.removed++; }
};`;

export const fixtureBootstrap = `
window.intakeFixture = {challenge:"success", renders:0, removed:0, scriptFailure:false};
// Only accelerate the module's two-minute timeout; keep its minimum-age wait real.
const originalTimeout = window.setTimeout.bind(window);
window.setTimeout = (callback, ms, ...args) =>
  originalTimeout(callback, ms === 120000 ? 400 : ms, ...args);
`;

export async function startIntakeFixture() {
  const root = resolve("website/elh-preview");
  const state = {security: [], posts: [], violations: [], held: null, securityFailure: false,
    submitResponse: null, hold: false, assets: []};
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://fixture.invalid");
    const json = (data, status = 200) => {
      response.writeHead(status, {"Content-Type": "application/json", "Cache-Control": "no-store"});
      response.end(JSON.stringify(data));
    };
    if (url.pathname === "/api/form-security" && request.method === "GET") {
      const token = "synthetic-signed-token-" + (state.security.length + 1);
      state.security.push({form: url.searchParams.get("form"), token, at: Date.now()});
      return json({token, siteKey: "synthetic-site-key", waitMs: 50}, state.securityFailure ? 503 : 200);
    }
    if (url.pathname === "/api/form-submit" && request.method === "POST") {
      let body = "";
      for await (const chunk of request) body += chunk;
      state.posts.push({fields: Object.fromEntries(new URLSearchParams(body)), at: Date.now(),
        headers: request.headers});
      const reply = () => {
        const result = state.submitResponse;
        if (result?.raw) {
          response.writeHead(200, {"Content-Type": "application/json"});
          response.end("not json");
        } else json(result?.body ?? {ok: true, accepted: true, receipt_id: "SYNTHETIC-RECEIPT",
          care_cta_html: '<p>Need to speak with someone now?</p><p>We&#x27;re here for you 24 hours a day, 7 days a week.</p><p><a href="tel:18059537273">Call 805.953.7273</a></p>'},
          result?.status ?? 200);
      };
      if (state.hold) state.held = reply;
      else reply();
      return;
    }
    // Only these unrelated read-only requests are expected from the real pages.
    if (url.pathname === "/api/google-reviews") return json({reviews: []});
    if (url.pathname.startsWith("/api/") || request.method !== "GET") {
      state.violations.push(request.method + " " + url.pathname);
      return json({error: "Unexpected test transport"}, 500);
    }
    let path = url.pathname;
    if (path === "/") path = "/index.html";
    if (path === "/refer") path = "/refer.html";
    const file = resolve(root, "." + decodeURIComponent(path));
    if (!file.startsWith(root + sep)) {response.writeHead(403);response.end();return;}
    try {
      const content = await readFile(file);
      state.assets.push(path);
      const types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
        ".woff2": "font/woff2", ".json": "application/json"};
      response.writeHead(200, {"Content-Type": types[extname(file)] || "application/octet-stream",
        "Cache-Control": "no-store"});
      response.end(content);
    } catch {
      response.writeHead(404);response.end();
    }
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  return {state, origin: `http://127.0.0.1:${server.address().port}`,
    async close() {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }};
}
