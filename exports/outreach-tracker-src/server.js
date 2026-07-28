const path = require("path");
const express = require("express");
const session = require("express-session");
const pgSession = require("connect-pg-simple")(session);
const bcrypt = require("bcryptjs");
const { pool, query } = require("./db");

const app = express();
const PORT = process.env.PORT || 5000;
const MAX_USERS = 2;

// Populated at startup by probeAiModel(); read by /api/config.
let aiModelWarning = null;

if (!process.env.SESSION_SECRET) {
  console.error(
    "FATAL: SESSION_SECRET is not set. Refusing to start with an insecure session secret."
  );
  process.exit(1);
}

app.set("trust proxy", 1);
app.use(express.json({ limit: "12mb" }));
app.use(express.urlencoded({ extended: true, limit: "12mb" }));

app.use(
  session({
    store: new pgSession({
      pool,
      tableName: "session",
      createTableIfMissing: false,
    }),
    name: "elh_outreach_sid",
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    rolling: true,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: "auto", // secure over HTTPS (Replit proxy), relaxed on plain localhost
      maxAge: 1000 * 60 * 60 * 24 * 30, // 30 days
    },
  })
);

// ---- simple in-memory brute-force throttle (single instance, 2-user tool) ----
const rlBuckets = new Map();
function rateLimit({ max, windowMs, message }) {
  return (req, res, next) => {
    const now = Date.now();
    const key = `${req.path}:${req.ip}`;
    let rec = rlBuckets.get(key);
    if (!rec || now - rec.first > windowMs) {
      rec = { count: 0, first: now };
      rlBuckets.set(key, rec);
    }
    rec.count += 1;
    if (rec.count > max) {
      const waitSec = Math.ceil((rec.first + windowMs - now) / 1000);
      res.setHeader("Retry-After", String(Math.max(waitSec, 1)));
      return res.status(429).json({ error: message });
    }
    next();
  };
}
// occasional cleanup so the map can't grow unbounded
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of rlBuckets) {
    if (now - v.first > 60 * 60 * 1000) rlBuckets.delete(k);
  }
}, 30 * 60 * 1000).unref();

const loginLimiter = rateLimit({
  max: 15,
  windowMs: 10 * 60 * 1000,
  message: "Too many sign-in attempts. Please wait a few minutes and try again.",
});
const registerLimiter = rateLimit({
  max: 8,
  windowMs: 15 * 60 * 1000,
  message: "Too many attempts. Please wait a few minutes and try again.",
});

// ---- helpers ----
function normalizePhone(raw) {
  return String(raw || "").replace(/\D/g, "");
}

// Accepts empty/null (→ stored as null) or a real YYYY-MM-DD calendar date.
function isValidDate(s) {
  if (s === null || s === undefined || s === "") return true;
  const str = String(s).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) return false;
  const d = new Date(str + "T00:00:00Z");
  return !Number.isNaN(d.getTime()) && str === d.toISOString().slice(0, 10);
}

function requireAuth(req, res, next) {
  if (req.session && req.session.userId) return next();
  return res.status(401).json({ error: "Not signed in." });
}

const FOLLOWUP_STATUSES = [
  "Not started",
  "Email sent",
  "Replied",
  "Meeting booked",
  "Closed",
  "No interest",
];
const PHOTO_KINDS = ["card", "site"];

function safeUser(row) {
  return { id: row.id, name: row.name, phone: row.phone };
}

// ---- auth routes ----
app.get("/api/config", async (req, res) => {
  try {
    const { rows } = await query("SELECT COUNT(*)::int AS n FROM users");
    const count = rows[0].n;
    res.json({
      registrationOpen: count < MAX_USERS,
      requiresCode: Boolean(process.env.REGISTRATION_CODE),
      signedIn: Boolean(req.session && req.session.userId),
      aiEnabled: Boolean(process.env.AI_INTEGRATIONS_OPENAI_API_KEY),
      aiModelWarning: aiModelWarning || null,
    });
  } catch (e) {
    console.error("config error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.get("/api/me", requireAuth, async (req, res) => {
  try {
    const { rows } = await query("SELECT id, name, phone FROM users WHERE id = $1", [
      req.session.userId,
    ]);
    if (!rows.length) {
      req.session.destroy(() => {});
      return res.status(401).json({ error: "Not signed in." });
    }
    res.json({ user: safeUser(rows[0]) });
  } catch (e) {
    console.error("me error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.post("/api/register", registerLimiter, async (req, res) => {
  const name = String(req.body.name || "").trim();
  const phone = normalizePhone(req.body.phone);
  const password = String(req.body.password || "");
  const code = String(req.body.code || "");

  if (!name) return res.status(400).json({ error: "Please enter your name." });
  if (phone.length < 10)
    return res.status(400).json({ error: "Please enter a valid phone number." });
  if (password.length < 8)
    return res.status(400).json({ error: "Password must be at least 8 characters." });

  if (process.env.REGISTRATION_CODE && code !== process.env.REGISTRATION_CODE) {
    return res.status(403).json({ error: "Invalid access code." });
  }

  const hash = await bcrypt.hash(password, 12);
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    // serialize all registration attempts so the 2-account cap is enforced atomically
    await client.query("SELECT pg_advisory_xact_lock($1)", [736251]);

    const countRes = await client.query("SELECT COUNT(*)::int AS n FROM users");
    if (countRes.rows[0].n >= MAX_USERS) {
      await client.query("ROLLBACK");
      return res
        .status(403)
        .json({ error: "Sign-up is closed (all accounts are set up)." });
    }
    const existing = await client.query("SELECT id FROM users WHERE phone = $1", [phone]);
    if (existing.rows.length) {
      await client.query("ROLLBACK");
      return res
        .status(409)
        .json({ error: "An account with that phone number already exists." });
    }
    const insert = await client.query(
      "INSERT INTO users (name, phone, password_hash) VALUES ($1, $2, $3) RETURNING id, name, phone",
      [name, phone, hash]
    );
    await client.query("COMMIT");
    req.session.userId = insert.rows[0].id;
    res.json({ user: safeUser(insert.rows[0]) });
  } catch (e) {
    try { await client.query("ROLLBACK"); } catch (_) {}
    console.error("register error", e);
    res.status(500).json({ error: "Server error." });
  } finally {
    client.release();
  }
});

app.post("/api/login", loginLimiter, async (req, res) => {
  try {
    const phone = normalizePhone(req.body.phone);
    const password = String(req.body.password || "");
    if (!phone || !password)
      return res.status(400).json({ error: "Enter your phone number and password." });

    const { rows } = await query(
      "SELECT id, name, phone, password_hash FROM users WHERE phone = $1",
      [phone]
    );
    if (!rows.length) {
      return res.status(401).json({ error: "Incorrect phone number or password." });
    }
    const ok = await bcrypt.compare(password, rows[0].password_hash);
    if (!ok) {
      return res.status(401).json({ error: "Incorrect phone number or password." });
    }
    req.session.userId = rows[0].id;
    res.json({ user: safeUser(rows[0]) });
  } catch (e) {
    console.error("login error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.post("/api/logout", (req, res) => {
  req.session.destroy(() => {
    res.clearCookie("elh_outreach_sid");
    res.json({ ok: true });
  });
});

// ---- visits ----
const VISIT_SELECT = `
  SELECT v.*, u.name AS created_by_name,
    COALESCE(
      (SELECT json_agg(json_build_object('id', p.id, 'kind', p.kind) ORDER BY p.created_at)
       FROM visit_photos p WHERE p.visit_id = v.id),
      '[]'
    ) AS photos
  FROM visits v
  LEFT JOIN users u ON u.id = v.created_by
`;

function cleanMaterials(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((m) => String(m).trim())
    .filter(Boolean)
    .slice(0, 20);
}

app.get("/api/visits", requireAuth, async (req, res) => {
  try {
    const { rows } = await query(
      `${VISIT_SELECT} ORDER BY v.created_at DESC`
    );
    res.json({ visits: rows });
  } catch (e) {
    console.error("list visits error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.get("/api/visits/:id", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });
    const { rows } = await query(`${VISIT_SELECT} WHERE v.id = $1`, [id]);
    if (!rows.length) return res.status(404).json({ error: "Not found." });
    res.json({ visit: rows[0] });
  } catch (e) {
    console.error("get visit error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.post("/api/visits", requireAuth, async (req, res) => {
  try {
    const b = req.body || {};
    const company = String(b.company || "").trim();
    if (!company) return res.status(400).json({ error: "Organization name is required." });
    if (b.attested !== true) {
      return res
        .status(400)
        .json({ error: "You must confirm the notes contain no patient information." });
    }

    const visitDate = b.visit_date ? String(b.visit_date) : null;
    const followUpDue = b.follow_up_due ? String(b.follow_up_due) : null;
    if (!isValidDate(visitDate) || !isValidDate(followUpDue)) {
      return res.status(400).json({ error: "Please provide a valid date (YYYY-MM-DD)." });
    }
    let status = String(b.followup_status || "Not started");
    if (!FOLLOWUP_STATUSES.includes(status)) status = "Not started";
    const materials = JSON.stringify(cleanMaterials(b.materials));
    const t = (k) => String(b[k] || "").trim() || null;

    const { rows } = await query(
      `INSERT INTO visits
        (company, category, address, city, county, visit_date,
         contact_name, contact_title, contact_email, contact_phone,
         materials, notes, owner, follow_up_due, followup_status, attested, created_by)
       VALUES
        ($1,$2,$3,$4,$5,COALESCE($6::date, CURRENT_DATE),
         $7,$8,$9,$10,
         $11::jsonb,$12,$13,$14::date,$15,$16,$17)
       RETURNING *`,
      [
        company,
        t("category"),
        t("address"),
        t("city"),
        t("county"),
        visitDate,
        t("contact_name"),
        t("contact_title"),
        t("contact_email"),
        t("contact_phone"),
        materials,
        t("notes"),
        t("owner"),
        followUpDue,
        status,
        true,
        req.session.userId,
      ]
    );
    res.json({ visit: { ...rows[0], photos: [] } });
  } catch (e) {
    console.error("create visit error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.patch("/api/visits/:id", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });

    const allowed = {
      company: "text",
      category: "text",
      address: "text",
      city: "text",
      county: "text",
      visit_date: "date",
      contact_name: "text",
      contact_title: "text",
      contact_email: "text",
      contact_phone: "text",
      notes: "text",
      owner: "text",
      follow_up_due: "date",
      followup_status: "status",
      materials: "materials",
    };
    const sets = [];
    const params = [];
    for (const [key, type] of Object.entries(allowed)) {
      if (!(key in req.body)) continue;
      let val = req.body[key];
      if (type === "status") {
        if (!FOLLOWUP_STATUSES.includes(String(val))) continue;
        params.push(val);
        sets.push(`${key} = $${params.length}`);
      } else if (type === "materials") {
        params.push(JSON.stringify(cleanMaterials(val)));
        sets.push(`${key} = $${params.length}::jsonb`);
      } else if (type === "date") {
        const dv = val ? String(val) : null;
        if (!isValidDate(dv)) {
          return res.status(400).json({ error: "Please provide a valid date (YYYY-MM-DD)." });
        }
        params.push(dv);
        sets.push(`${key} = $${params.length}::date`);
      } else {
        val = String(val || "").trim();
        params.push(val === "" ? null : val);
        sets.push(`${key} = $${params.length}`);
      }
    }
    if (!sets.length) return res.status(400).json({ error: "Nothing to update." });
    params.push(id);
    const { rows } = await query(
      `UPDATE visits SET ${sets.join(", ")}, updated_at = NOW() WHERE id = $${params.length} RETURNING id`,
      params
    );
    if (!rows.length) return res.status(404).json({ error: "Not found." });
    const full = await query(`${VISIT_SELECT} WHERE v.id = $1`, [id]);
    res.json({ visit: full.rows[0] });
  } catch (e) {
    console.error("update visit error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.delete("/api/visits/:id", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });
    await query("DELETE FROM visits WHERE id = $1", [id]);
    res.json({ ok: true });
  } catch (e) {
    console.error("delete visit error", e);
    res.status(500).json({ error: "Server error." });
  }
});

// ---- photos ----
app.post("/api/visits/:id/photos", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });
    const visit = await query("SELECT id FROM visits WHERE id = $1", [id]);
    if (!visit.rows.length) return res.status(404).json({ error: "Visit not found." });

    const dataUrl = String(req.body.image || "");
    const match = dataUrl.match(/^data:(image\/(png|jpeg|jpg|webp));base64,(.+)$/);
    if (!match) return res.status(400).json({ error: "Invalid image data." });
    const mime = match[1];
    const buffer = Buffer.from(match[3], "base64");
    if (buffer.length > 8 * 1024 * 1024)
      return res.status(413).json({ error: "Image too large." });
    let kind = String(req.body.kind || "site");
    if (!PHOTO_KINDS.includes(kind)) kind = "site";

    const { rows } = await query(
      "INSERT INTO visit_photos (visit_id, kind, mime_type, data) VALUES ($1,$2,$3,$4) RETURNING id, kind, created_at",
      [id, kind, mime, buffer]
    );
    res.json({ photo: rows[0] });
  } catch (e) {
    console.error("upload photo error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.get("/api/photos/:id", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });
    const { rows } = await query(
      "SELECT mime_type, data FROM visit_photos WHERE id = $1",
      [id]
    );
    if (!rows.length) return res.status(404).json({ error: "Not found." });
    res.setHeader("Content-Type", rows[0].mime_type);
    res.setHeader("Cache-Control", "private, max-age=86400");
    res.send(rows[0].data);
  } catch (e) {
    console.error("get photo error", e);
    res.status(500).json({ error: "Server error." });
  }
});

app.delete("/api/photos/:id", requireAuth, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isInteger(id)) return res.status(400).json({ error: "Bad id." });
    await query("DELETE FROM visit_photos WHERE id = $1", [id]);
    res.json({ ok: true });
  } catch (e) {
    console.error("delete photo error", e);
    res.status(500).json({ error: "Server error." });
  }
});

// ---- AI: business card extraction ----
const extractLimiter = rateLimit({
  max: 40,
  windowMs: 10 * 60 * 1000,
  message: "Too many card scans. Please wait a few minutes and try again.",
});

app.post("/api/extract-card", requireAuth, extractLimiter, async (req, res) => {
  try {
    const dataUrl = String(req.body.image || "");
    const match = dataUrl.match(/^data:(image\/(png|jpeg|jpg|webp));base64,(.+)$/);
    if (!match) return res.status(400).json({ error: "Invalid image data." });
    if (Buffer.from(match[3], "base64").length > 8 * 1024 * 1024) {
      return res.status(413).json({ error: "Image too large." });
    }
    let extractCardContact;
    try {
      ({ extractCardContact } = require("./ai"));
    } catch (e) {
      console.error("ai module load error", e);
      return res
        .status(503)
        .json({ error: "Card reading isn't available right now. Please enter the details manually." });
    }
    const contact = await extractCardContact(dataUrl);
    res.json({ contact });
  } catch (e) {
    console.error("extract-card error", e);
    res.status(502).json({ error: "Couldn't read the card. Please enter the details manually." });
  }
});

// ---- AI: voice note transcription ----
const transcribeLimiter = rateLimit({
  max: 40,
  windowMs: 10 * 60 * 1000,
  message: "Too many voice notes. Please wait a few minutes and try again.",
});

app.post("/api/transcribe", requireAuth, transcribeLimiter, async (req, res) => {
  try {
    const dataUrl = String(req.body.audio || "");
    const match = dataUrl.match(
      /^data:(audio\/(webm|ogg|mp4|mpeg|mp3|wav|x-m4a|m4a))(;codecs=[^;]+)?;base64,(.+)$/
    );
    if (!match) return res.status(400).json({ error: "Invalid audio data." });
    const buffer = Buffer.from(match[4], "base64");
    if (buffer.length < 512) {
      return res.status(400).json({ error: "Recording too short. Please try again." });
    }
    if (buffer.length > 8 * 1024 * 1024) {
      return res
        .status(413)
        .json({ error: "Recording too long. Please keep voice notes under a few minutes." });
    }
    const ext = { "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4",
      "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
      "audio/x-m4a": "m4a", "audio/m4a": "m4a" }[match[1]] || "webm";
    let transcribeAudio;
    try {
      ({ transcribeAudio } = require("./ai"));
    } catch (e) {
      console.error("ai module load error", e);
      return res
        .status(503)
        .json({ error: "Voice notes aren't available right now. Please type your notes." });
    }
    const text = await transcribeAudio(buffer, `note.${ext}`);
    res.json({ text });
  } catch (e) {
    console.error("transcribe error", e);
    res.status(502).json({ error: "Couldn't transcribe that. Please try again or type your notes." });
  }
});

// ---- on-demand full backup trigger ----
const triggerLimiter = rateLimit({
  max: 3,
  windowMs: 60 * 60 * 1000, // 1 hour
  message: "Too many backup requests. Please wait before trying again.",
});

app.post("/api/backup/trigger", requireAuth, triggerLimiter, async (req, res) => {
  const forceFullBackup = req.query.full === "true";
  try {
    const result = await runWeeklyBackup({ forceFullBackup });
    if (result && result.busy) {
      return res.status(409).json({ error: "A backup is already in progress. Please wait a moment and try again." });
    }
    // runWeeklyBackup resolves after the run completes (success or failure).
    // Read the latest log row to surface the outcome.
    const r = await query(
      `SELECT status, note FROM backup_log ORDER BY ran_at DESC LIMIT 1`
    );
    const row = r.rows[0];
    if (!row || row.status !== "ok") {
      const note = (row && row.note) || "Unknown error";
      return res.status(502).json({ error: note });
    }
    res.json({ ok: true, note: row.note });
  } catch (e) {
    const msg = String((e && e.message) || "Unknown error").slice(0, 300);
    console.error("on-demand backup trigger error:", msg);
    res.status(500).json({ error: msg });
  }
});

// ---- backup status ----
app.get("/api/backup/status", requireAuth, async (req, res) => {
  try {
    // Prune rows older than 90 days whenever the Export tab polls
    await query(
      `DELETE FROM backup_log WHERE ran_at < NOW() - INTERVAL '90 days'`
    ).catch(() => {}); // ignore if table doesn't exist yet

    const r = await query(
      `SELECT status, ran_at, note FROM backup_log ORDER BY ran_at DESC LIMIT 10`
    );
    if (!r.rows.length) return res.json({ rows: [] });
    res.json({
      rows: r.rows.map((row) => ({
        status: row.status,
        ran_at: row.ran_at,
        note: row.note || null,
      })),
    });
  } catch (_) {
    // backup_log table doesn't exist yet — not a problem
    res.json({ rows: [] });
  }
});

// ---- manual backup trigger ----
const backupRunLimiter = rateLimit({
  max: 1,
  windowMs: 5 * 60 * 1000,
  message: "Please wait 5 minutes before running another backup.",
});

app.post("/api/backup/run", requireAuth, backupRunLimiter, async (req, res) => {
  try {
    await runWeeklyBackup();
    const r = await query(
      `SELECT status, ran_at, note FROM backup_log ORDER BY ran_at DESC LIMIT 10`
    ).catch(() => ({ rows: [] }));
    res.json({ ok: true, rows: r.rows.map((row) => ({ status: row.status, ran_at: row.ran_at, note: row.note || null })) });
  } catch (e) {
    console.error("Manual backup run error:", e);
    res.status(500).json({ error: "Backup run failed. Check server logs." });
  }
});

// ---- weekly backup scheduler ----
// Uses backup_log as persistent state so a server restart doesn't reset the
// 7-day clock.  Key design rules:
//   1. backupRunning guard — prevents overlapping runs.
//   2. scheduleNextBackup reads the LATEST row (any status) so a failed run
//      is treated as an attempt and retried with backoff, not immediately.
//   3. On success → next run in 7 days.
//      On failure → retry in BACKUP_RETRY_MS (1 h) from the last attempt.
//      On DB error → retry scheduleNextBackup in 1 h.

const { runWeeklyBackup, scheduleNextBackup } = require("./backup");

// ---- AI model startup probe ----
// Runs once after boot; sets aiModelWarning when the card-scanning model is
// unreachable or retired so /api/config can surface it to the client.
async function probeAiModel() {
  if (!process.env.AI_INTEGRATIONS_OPENAI_API_KEY) return;
  try {
    const OpenAI = require("openai");
    const client = new OpenAI({
      apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
      baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
    });
    // Use the same model as extractCardContact; a minimal text-only call is
    // enough to confirm the model is live without spending tokens.
    await client.chat.completions.create({
      model: "gpt-5.4-mini",
      messages: [{ role: "user", content: "ping" }],
      max_tokens: 1,
    });
    aiModelWarning = null;
    console.log("AI model probe: card-scanning model is reachable.");
  } catch (e) {
    const msg = String((e && e.message) || "");
    const status = e && e.status;
    // 404 = model not found / retired; treat auth failures and hard
    // unavailability as broken too — any of these blocks field staff.
    if (status === 404 || status === 401 || status === 503 || /model/i.test(msg)) {
      aiModelWarning =
        "Card scanning is unavailable — the AI model may need updating. Contact your admin.";
      console.warn("AI model probe failed (status " + status + "):", msg);
    }
    // Transient network errors are not surfaced as a banner (don't false-alarm).
  }
}

// ---- static frontend ----
app.use(express.static(path.join(__dirname, "public")));

app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`ELH Outreach Tracker running on port ${PORT}`);
  // Non-blocking — sets aiModelWarning if the card-scanning model is broken.
  probeAiModel().catch((e) => console.error("probeAiModel unexpected error:", e));
  // Non-blocking — starts the persistent weekly backup scheduler.
  // Reads the last successful run from backup_log so a server restart does not
  // reset the 7-day clock; fires immediately if overdue or never run before.
  scheduleNextBackup();
});
