// Test-only UI fixture plus an opt-in real handler in an isolated Python process.
import {createServer, request as httpRequest} from "node:http";
import {spawn} from "node:child_process";
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
// Test-only lifecycle evidence; no submitted values are copied into storage.
window.intakeFixture.documentId = crypto.randomUUID();
window.intakeFixture.pageShows = [];
addEventListener("pageshow", event => window.intakeFixture.pageShows.push(event.persisted));
// Only accelerate the module's two-minute timeout; keep its minimum-age wait real.
const originalTimeout = window.setTimeout.bind(window);
window.setTimeout = (callback, ms, ...args) =>
  originalTimeout(callback, ms === 120000 && !window.intakeFixture.realBackend ? 400 : ms, ...args);
`;

export async function startIntakeFixture() {
  if (process.env.REPLIT_DEPLOYMENT === "1") throw new Error("Never run fixtures in production");
  const root = resolve("website/elh-preview");
  const state = {security: [], posts: [], violations: [], held: null, securityFailure: false,
    submitResponse: null, hold: false, assets: [], realSecurity: false, realRequests: [],
    historyCacheable: false};
  let backend;
  let backendPort;
  let backendLog = "";
  async function stopBackend() {
    if (!backend) return;
    if (backend.exitCode === null) {
      const exited = new Promise(resolve => backend.once("exit", resolve));
      backend.stdin.end();
      await exited;
    }
    if (backend.exitCode !== 0) throw new Error("Real backend cleanup failed\n" + backendLog);
    backend = undefined;
  }
  async function startBackend() {
    backend = spawn("python3", ["website/intake-browser-backend.py"],
      {stdio: ["pipe", "pipe", "pipe"]});
    backend.stderr.on("data", chunk => {backendLog = (backendLog + chunk).slice(-4000);});
    backendPort = await new Promise((resolve, reject) => {
      let output = "";
      const timer = setTimeout(() => reject(new Error("Real intake backend startup timed out")), 60000);
      const fail = error => {clearTimeout(timer);reject(error);};
      backend.once("error", fail);
      backend.once("exit", code => fail(new Error(`Real intake backend exited ${code}\n${backendLog}`)));
      backend.stdout.on("data", chunk => {
        output += chunk;
        if (!output.includes("\n")) return;
        try {clearTimeout(timer);resolve(JSON.parse(output.split("\n")[0]).port);}
        catch (error) {fail(error);}
      });
    });
  }
  async function backendRequest(path, method = "GET", headers = {}, body = "") {
    return new Promise((resolve, reject) => {
      const upstream = httpRequest({hostname: "127.0.0.1", port: backendPort, path,
        method, headers}, response => {
        let content = "";
        response.on("data", chunk => {content += chunk;});
        response.on("end", () => resolve({status: response.statusCode, content,
          headers: response.headers}));
      });
      upstream.on("error", reject);
      upstream.setTimeout(10000, () => upstream.destroy(new Error("Real intake backend timeout")));
      upstream.end(body);
    });
  }
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://fixture.invalid");
    const json = (data, status = 200) => {
      response.writeHead(status, {"Content-Type": "application/json", "Cache-Control": "no-store"});
      response.end(JSON.stringify(data));
    };
    if (state.realSecurity && ["/api/form-security", "/api/form-submit"].includes(url.pathname)) {
      let body = "";
      for await (const chunk of request) body += chunk;
      const record = {path: request.url, method: request.method, headers: request.headers,
        fields: Object.fromEntries(new URLSearchParams(body)), at: Date.now()};
      state.realRequests.push(record);
      try {
        // Preserve browser-controlled headers, including Host/absent Origin,
        // but emulate the live proxy selecting a different address each time.
        record.proxyClient = `192.0.2.${(state.realRequests.length % 200) + 1}`;
        const result = await backendRequest(request.url, request.method,
          {...request.headers, "x-forwarded-for": record.proxyClient}, body);
        record.status = result.status;
        record.result = JSON.parse(result.content);
        response.writeHead(result.status, result.headers);
        response.end(result.content);
      } catch (error) {
        state.violations.push(String(error));
        json({error: "real_backend_failed"}, 500);
      }
      return;
    }
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
        if (result?.disconnect) {
          // Simulate losing the response AFTER the fixture has received the POST.
          // Send headers first: an empty reused connection can cause Chromium's
          // own transport to replay a request before JavaScript sees the error.
          response.writeHead(200, {"Content-Type": "application/json", "Content-Length": "10000"});
          response.write('{"ok":');
          setTimeout(() => response.destroy(), 20);
        } else if (result?.raw) {
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
        // Opt-in only for history tests. Never changes deployed page headers,
        // API no-store responses or security/transport isolation.
        "Cache-Control": state.historyCacheable && extname(file) === ".html" ? "private, max-age=0" : "no-store"});
      response.end(content);
    } catch {
      response.writeHead(404);response.end();
    }
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  return {state, origin: `http://127.0.0.1:${server.address().port}`,
    async useRealSecurity() {
      // Give each independent matrix a fresh client/database rather than disabling
      // production rate limits to accommodate accumulated synthetic attempts.
      await stopBackend();
      await startBackend();
      state.moduleFailure = false;
      state.realSecurity = true;
    },
    async backendState() {
      return JSON.parse((await backendRequest("/__fixture__/state")).content);
    },
    async close() {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
      await stopBackend();
    }};
}
