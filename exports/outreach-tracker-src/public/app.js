const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const STATUSES = ["Not started", "Email sent", "Replied", "Meeting booked", "Closed", "No interest"];
const CLOSED = ["Closed", "No interest"];
const OWNER_OPTIONS = ["Aleksandra Dubina", "Denise Chavez", "Bianca Kashyap"];

const DRAFT_KEY = "elh_visit_draft";
let me = null;
let visits = [];
let aiEnabled = false;

/* ---------------- api ---------------- */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const err = new Error((data && data.error) || "Something went wrong.");
    err.status = res.status;
    err.retryAfter = res.headers.get("Retry-After");
    throw err;
  }
  return data;
}

/* ---------------- toast ---------------- */
let tt;
function toast(m, isErr) {
  const el = $("#toast");
  el.textContent = m;
  el.classList.toggle("err", !!isErr);
  el.classList.add("on");
  clearTimeout(tt);
  tt = setTimeout(() => el.classList.remove("on"), 2800);
}

const esc = (s) =>
  String(s ?? "").replace(/[<>&"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]));

/* ================= AUTH ================= */
function showAuthError(msg) {
  const el = $("#autherr");
  if (!msg) { el.classList.add("hidden"); return; }
  el.textContent = msg;
  el.classList.remove("hidden");
}

function showView(which) {
  $("#auth").classList.toggle("hidden", which !== "auth");
  $("#app").classList.toggle("hidden", which !== "app");
}

async function initAuthScreen() {
  showAuthError("");
  let cfg = { registrationOpen: true, requiresCode: false };
  try { cfg = await api("/api/config"); } catch (_) {}
  $("#codeWrap").classList.toggle("hidden", !cfg.requiresCode);
  if (!cfg.registrationOpen) {
    $("#toReg").parentElement.style.display = "none";
  }
  showView("auth");
}

function authMode(mode) {
  showAuthError("");
  $("#loginForm").classList.toggle("hidden", mode !== "login");
  $("#regForm").classList.toggle("hidden", mode !== "register");
  $("#regClosed").classList.add("hidden");
}

$("#toReg").addEventListener("click", async () => {
  const cfg = await api("/api/config");
  if (!cfg.registrationOpen) {
    $("#loginForm").classList.add("hidden");
    $("#regForm").classList.add("hidden");
    $("#regClosed").classList.remove("hidden");
    return;
  }
  authMode("register");
});
$("#toLogin").addEventListener("click", () => authMode("login"));
$("#toLogin2").addEventListener("click", () => authMode("login"));

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  try {
    const r = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ phone: $("#li-phone").value.trim(), password: $("#li-pass").value }),
    });
    me = r.user;
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
});

$("#regForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  try {
    const r = await api("/api/register", {
      method: "POST",
      body: JSON.stringify({
        name: $("#re-name").value.trim(),
        phone: $("#re-phone").value.trim(),
        password: $("#re-pass").value,
        code: $("#re-code").value.trim(),
      }),
    });
    me = r.user;
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
});

$("#logoutBtn").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); } catch (_) {}
  me = null;
  visits = [];
  location.reload();
});

/* ================= APP BOOT ================= */
async function enterApp() {
  // Fetch config to learn if the OpenAI integration is enabled
  try {
    const cfg = await api("/api/config");
    aiEnabled = Boolean(cfg.aiEnabled);
    if (cfg.aiModelWarning) showAiModelBanner(cfg.aiModelWarning);
  } catch (_) {
    aiEnabled = false;
  }
  // Show the voice recorder; grey it out with an explanation when AI is unavailable
  updateVoiceSection();

  $("#meName").textContent = me ? me.name : "";
  populateOwners();
  $("#date").value = new Date().toISOString().slice(0, 10);
  restoreDraft();
  showView("app");
  // Show the Save/Clear bar immediately (it starts hidden in HTML but the
  // log view is always the boot default) and lift it above any injected
  // dev bar (e.g. the ELH dev switcher in the Replit preview).
  const _bootBar = $("#bar");
  _bootBar.classList.remove("hidden");
  const _devBar = document.getElementById("_elh-dev-bar");
  if (_devBar) _bootBar.style.bottom = _devBar.offsetHeight + "px";
  await loadVisits();
  riskCheck();
  validate();
  loadBackupStatus(); // non-blocking — populate Export tab warning in background

  // Resume backup-button cooldown if a cooldown was active when the page was last loaded
  const _cooldownUntil = parseInt(_ssGet(RUN_BACKUP_COOLDOWN_KEY) || "0", 10);
  if (_cooldownUntil > Date.now()) {
    const _remainingSec = Math.ceil((_cooldownUntil - Date.now()) / 1000);
    const _backupBtn = $("#runBackupBtn");
    if (_backupBtn) _startRunBackupCooldown(_backupBtn, _remainingSec);
  } else if (_cooldownUntil > 0) {
    _ssRemove(RUN_BACKUP_COOLDOWN_KEY); // expired — clean up proactively
  }

  // If the export view was already the active tab when the app booted (e.g. a
  // direct deep-link or cold-boot on the Export tab), switchTab() was never
  // called, so the "Last checked" interval was never started.  Start it now.
  const _bootExportView = $("#view-export");
  if (_bootExportView && !_bootExportView.classList.contains("hidden") && !_backupCheckedAtTimer) {
    _backupCheckedAtTimer = setInterval(renderCheckedAt, 1000);
  }
}

function populateOwners() {
  const sel = $("#owner");
  sel.innerHTML = OWNER_OPTIONS.map((n) => `<option>${esc(n)}</option>`).join("");
}

async function loadVisits() {
  try {
    const r = await api("/api/visits");
    visits = r.visits || [];
  } catch (err) {
    visits = [];
    toast(err.message, true);
  }
  render();
}

/* ================= PHI GUARDRAIL ================= */
const RISK = [
  /\bpatient\b/i, /\bmrs?\.\s/i, /\bms\.\s/i, /\bdob\b/i, /\bmrn\b/i,
  /\bdiagnos/i, /\bcancer\b/i, /\bcopd\b/i, /\bdementia\b/i, /\broom\s?\d/i,
  /\b\d{1,3}\s?(years?\s?old|yo)\b/i, /\bhospice for\b/i,
];
function riskCheck() {
  const t = $("#notes").value;
  const hit = RISK.some((r) => r.test(t));
  $("#guard").classList.toggle("alarm", hit);
  $("#guard").querySelector("b").textContent = hit
    ? "That reads like patient information"
    : "This log holds no patient information";
  return hit;
}


/* ----- keep voice section in sync with the current aiEnabled value ----- */
function updateVoiceSection() {
  const voiceSection = $(".voice");
  if (!voiceSection) return;
  const btn = voiceSection.querySelector("#recBtn");
  if (!aiEnabled) {
    const msg = "Voice notes aren't available yet — enable the OpenAI integration in this Replit's Integrations panel.";
    if (btn) {
      btn.setAttribute("aria-disabled", "true");
      btn.setAttribute("title", "Voice notes unavailable — AI integration not enabled");
      btn.setAttribute("aria-describedby", "recHint");
    }
    setRecHint(msg, true);
  } else {
    if (btn) {
      btn.removeAttribute("aria-disabled");
      btn.removeAttribute("title");
      btn.removeAttribute("aria-describedby");
    }
  }
}


/* ----- voice notes: SpeechRecognition (browser-native, no server needed) ----- */
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition || null;
let recognition = null;
let recState = "idle"; // idle | recording
let recFinalText = "";

const REC_HINT_DEFAULT =
  "Tap Stop when you're done — your words will appear in the notes box. Review before saving.";

function setRecHint(msg, isErr) {
  const h = $("#recHint");
  if (!h) return;
  h.textContent = msg;
  h.classList.toggle("err", !!isErr);
}

function setRecState(state) {
  recState = state;
  const btn = $("#recBtn");
  const label = btn.querySelector(".reclabel");
  btn.classList.toggle("recording", state === "recording");
  btn.classList.remove("working");
  btn.disabled = false;
  label.textContent = state === "recording" ? "Stop recording" : "Record instead of typing";
}

function appendNotes(text) {
  const ta = $("#notes");
  const existing = ta.value.trim();
  ta.value = existing ? existing + "\n\n" + text : text;
  riskCheck();
  validate();
}

function startRecording() {
  if (!SpeechRec) {
    setRecHint("Your browser doesn't support voice recording. Please type your notes.", true);
    return;
  }
  recFinalText = "";
  recognition = new SpeechRec();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    setRecState("recording");
    setRecHint("Listening… tap Stop when you're done.");
  };

  recognition.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) recFinalText += t + " ";
      else interim = t;
    }
    setRecHint("Listening… " + (recFinalText + interim).trim());
  };

  recognition.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      setRecHint("Microphone access is blocked. Allow it in your browser settings, or type your notes.", true);
    } else if (e.error === "no-speech") {
      setRecHint("No speech detected. Try again or type your notes.", true);
    } else {
      setRecHint("Recording error (" + e.error + "). Please type your notes.", true);
    }
    setRecState("idle");
    recognition = null;
  };

  recognition.onend = () => {
    const text = recFinalText.trim();
    setRecState("idle");
    recognition = null;
    if (!text) {
      setRecHint("Nothing was captured. Try again in a quieter spot, or type your notes.", true);
      return;
    }
    appendNotes(text);
    setRecHint("Added below — read it over and edit before saving.");
    toast("Voice note added. Please review it.");
  };

  try {
    recognition.start();
  } catch (e) {
    setRecHint("Couldn't start recording. Please type your notes.", true);
    recognition = null;
  }
}

function stopRecording() {
  if (recognition) {
    recognition.stop();
  }
}

$("#recBtn").addEventListener("click", () => {
  if (recState === "recording") stopRecording();
  else { setRecHint(REC_HINT_DEFAULT); startRecording(); }
});

/* ================= CARD SCAN ================= */
$("#scanCardBtn").addEventListener("click", () => $("#cardFileInput").click());
$("#cardFileInput").addEventListener("change", async () => {
  const file = $("#cardFileInput").files[0];
  if (!file) return;
  const scanBtn = $("#scanCardBtn");
  const status = $("#scanStatus");
  scanBtn.disabled = true;
  status.textContent = "Reading card…";
  try {
    const dataUrl = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
    const data = await api("/api/extract-card", { method: "POST", body: JSON.stringify({ image: dataUrl }) });
    const c = data.contact || {};
    if (c.contact_name)  { $("#cname").value  = c.contact_name;  }
    if (c.contact_title) { $("#ctitle").value = c.contact_title; }
    if (c.contact_email) { $("#cemail").value = c.contact_email; }
    if (c.contact_phone) { $("#cphone").value = c.contact_phone; }
    if (c.company) { $("#org").value  = c.company;  }
    if (c.address) { $("#addr").value = c.address;  }
    if (c.city)    { $("#city").value = c.city;     }
    status.textContent = "Fields filled from card.";
    validate();
  } catch (e) {
    status.textContent = e.message || "Couldn't read the card — fill in manually.";
  } finally {
    scanBtn.disabled = false;
    $("#cardFileInput").value = "";
  }
});

/* ================= VALIDATION ================= */
function validate() {
  const ok = $("#org").value.trim() && $("#date").value && $("#attest").checked && !riskCheck()
    && $("#addr").value.trim() && $("#cname").value.trim();
  $("#saveBtn").disabled = !ok;
}
["#org", "#date", "#notes", "#addr", "#cname"].forEach((s) => $(s).addEventListener("input", () => { validate(); saveDraft(); }));
["#cat", "#city", "#county", "#ctitle", "#cemail", "#cphone", "#owner", "#fmethod", "#due"].forEach((s) => $(s)?.addEventListener("change", saveDraft));
$$("#mats input").forEach((i) => i.addEventListener("change", saveDraft));
$("#attest").addEventListener("change", validate);

/* ================= CLOCK ================= */
const DAY = 864e5;
function daysTo(iso) {
  return Math.ceil((new Date(iso + "T00:00:00") - new Date(new Date().toDateString())) / DAY);
}
function addDays(iso, n) {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + +n);
  return d.toISOString().slice(0, 10);
}

/* ================= SAVE ================= */
$("#saveBtn").addEventListener("click", async () => {
  if ($("#saveBtn").disabled) return;
  $("#saveBtn").disabled = true;
  const dueDays = $("#due").value;
  const visitDate = $("#date").value;
  const payload = {
    company: $("#org").value.trim(),
    category: $("#cat").value,
    address: $("#addr").value.trim(),
    city: $("#city").value.trim(),
    county: $("#county").value,
    visit_date: visitDate,
    contact_name: $("#cname").value.trim(),
    contact_title: $("#ctitle").value.trim(),
    contact_email: $("#cemail").value.trim(),
    contact_phone: $("#cphone").value.trim(),
    materials: $$("#mats input:checked").map((i) => i.value),
    notes: $("#notes").value.trim(),
    owner: $("#owner").value,
    follow_up_method: $("#fmethod").value,
    follow_up_due: addDays(visitDate, dueDays),
    followup_status: "Not started",
    attested: $("#attest").checked === true,
  };

  try {
    await api("/api/visits", { method: "POST", body: JSON.stringify(payload) });
    clearForm();        // also calls clearDraft() internally
    await loadVisits();
    switchTab("queue");
    toast("Visit saved. Follow-up clock started.");
  } catch (err) {
    toast(err.message, true);
    validate();
  }
});


function clearForm() {
  ["#org", "#addr", "#city", "#cname", "#ctitle", "#cemail", "#cphone", "#notes"].forEach((s) => ($(s).value = ""));
  $("#cat").selectedIndex = 0;
  $("#county").selectedIndex = 0;
  $("#fmethod").selectedIndex = 0;
  $("#due").value = "2";
  $$("#mats input").forEach((i) => (i.checked = false));
  $("#attest").checked = false;
  $("#date").value = new Date().toISOString().slice(0, 10);
  clearDraft();
  riskCheck();
  validate();
}

function saveDraft() {
  const mat = $("input[name='mats']:checked");
  const draft = {
    org: $("#org").value,
    cat: $("#cat").value,
    date: $("#date").value,
    addr: $("#addr").value,
    city: $("#city").value,
    county: $("#county").value,
    cname: $("#cname").value,
    ctitle: $("#ctitle").value,
    cemail: $("#cemail").value,
    cphone: $("#cphone").value,
    notes: $("#notes").value,
    owner: $("#owner").value,
    fmethod: $("#fmethod").value,
    due: $("#due").value,
    mat: mat ? mat.value : "",
  };
  // attest is intentionally excluded — must be re-confirmed every session
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (_) {}
  _flashDraftSaved("Draft saved");
}
function render() {
  const open = visits.filter((v) => !CLOSED.includes(v.followup_status));
  $("#qcount").textContent = open.length;
  $("#sVisits").textContent = visits.length;
  $("#sOrgs").textContent = new Set(visits.map((v) => v.company)).size;
  $("#sOpen").textContent = open.length;
  $("#sWon").textContent = visits.filter((v) => v.followup_status === "Meeting booked").length;

  const q = $("#queue");
  if (!visits.length) {
    q.innerHTML = `<div class="empty"><h3>No visits logged</h3><p>Log your first visit and it appears here with a follow-up clock running against it.</p></div>`;
    return;
  }

  q.innerHTML = visits
    .map((v) => {
      const status = v.followup_status;
      const closed = CLOSED.includes(status);
      const due = v.follow_up_due ? String(v.follow_up_due).slice(0, 10) : "";
      let n = "—", cls = "", lbl = "days out";
      if (closed) {
        n = status === "Closed" ? "Closed" : "No";
        cls = "done";
        lbl = status === "Closed" ? "complete" : "interest";
      } else if (due) {
        const d = daysTo(due);
        if (d < 0) { n = Math.abs(d); cls = "late"; lbl = d === -1 ? "day late" : "days late"; }
        else if (d <= 1) { n = d === 0 ? "Today" : d; cls = "due"; lbl = d === 0 ? "due" : "day out"; }
        else { n = d; lbl = "days out"; }
      }
      const vdate = v.visit_date ? String(v.visit_date).slice(0, 10) : "";
      const meta = [
        v.contact_name && `${esc(v.contact_name)}${v.contact_title ? ", " + esc(v.contact_title) : ""}`,
        [v.city, v.county && v.county + " County"].filter(Boolean).map(esc).join(" · "),
        vdate && "Visited " + vdate,
      ].filter(Boolean).join("<br>");
      const mats = Array.isArray(v.materials) ? v.materials : [];
      const pics = (v.photos || []).map((p) => `<img src="/api/photos/${p.id}" alt="${esc(p.kind)}">`).join("");

      return `<article class="card ${cls}">
        <div class="cardin">
          <div class="crow">
            <div><h3 class="org">${esc(v.company)}</h3><div class="meta">${meta}</div></div>
            <div class="clock ${cls}"><div class="n" style="${String(n).length > 3 ? "font-size:15px" : ""}">${n}</div><div class="l">${lbl}</div></div>
          </div>
          ${mats.length ? `<div class="mats">${mats.map((m) => `<span class="mat">${esc(m)}</span>`).join("")}</div>` : ""}
          ${v.notes ? `<div class="cnote">${esc(v.notes)}</div>` : ""}
          ${pics ? `<div class="snap">${pics}</div>` : ""}
        </div>
        <div class="cardfoot">
          <select data-id="${v.id}" class="st">
            ${STATUSES.map((s) => `<option ${s === status ? "selected" : ""}>${s}</option>`).join("")}
          </select>
          <button class="del" data-id="${v.id}">Delete</button>
          <div class="who">${esc(v.owner || "Unassigned")}${due && !closed ? "<br>due " + due : ""}</div>
        </div>
      </article>`;
    })
    .join("");

  q.querySelectorAll(".st").forEach((sel) =>
    sel.addEventListener("change", async (e) => {
      const id = e.target.dataset.id;
      try {
        await api(`/api/visits/${id}`, { method: "PATCH", body: JSON.stringify({ followup_status: e.target.value }) });
        await loadVisits();
      } catch (err) {
        toast(err.message, true);
      }
    })
  );

  q.querySelectorAll(".del").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const v = visits.find((x) => String(x.id) === String(id));
      if (!confirm(`Delete the visit to ${v ? v.company : "this organization"}? This cannot be undone.`)) return;
      try {
        await api(`/api/visits/${id}`, { method: "DELETE" });
        await loadVisits();
        toast("Visit deleted.");
      } catch (err) {
        toast(err.message, true);
      }
    })
  );
}

/* ================= CSV ================= */
$("#csv").addEventListener("click", () => {
  if (!visits.length) return toast("No visits to export yet.", true);
  const cols = ["visit_date", "company", "category", "address", "city", "county", "contact_name", "contact_title", "contact_email", "contact_phone", "materials", "notes", "owner", "follow_up_method", "follow_up_due", "followup_status"];
  const head = ["Visit date", "Organization", "Category", "Address", "City", "County", "Contact", "Title", "Email", "Phone", "Materials left", "Notes", "Owner", "Follow-up type", "Follow-up due", "Status"];
  const neutralize = (s) => (/^[=+\-@\t\r]/.test(s) ? "'" + s : s);
  const rows = visits.map((v) =>
    cols.map((c) => {
      const val = c === "materials" ? (Array.isArray(v[c]) ? v[c].join("; ") : "") : String(v[c] ?? "");
      return neutralize('"' + val.replace(/"/g, '""') + '"');
    }).join(",")
  );
  const blob = new Blob(["\ufeff" + [head.join(","), ...rows].join("\r\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ELH_Field_Log_" + new Date().toISOString().slice(0, 10) + ".csv";
  a.click();
  URL.revokeObjectURL(a.href);
  toast("CSV downloaded.");
});

/* ================= ON-DEMAND FULL BACKUP ================= */
(function () {
  const btn = $("#triggerBackup");
  const statusEl = $("#triggerBackupStatus");
  if (!btn || !statusEl) return;

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.classList.toggle("trigger-backup-error", Boolean(isError));
    statusEl.classList.remove("hidden");
  }

  btn.addEventListener("click", async () => {
    if (btn.disabled) return;
    btn.disabled = true;
    btn.textContent = "Sending…";
    statusEl.classList.add("hidden");
    statusEl.textContent = "";
    try {
      await api("/api/backup/run", { method: "POST" });
      setStatus("Full backup sent.", false);
      toast("Full backup sent.");
      loadBackupStatus();
    } catch (e) {
      const msg = (e && e.message) || "Backup failed. Check BACKUP_EMAIL and the Brevo API key.";
      setStatus(msg, true);
      toast(msg, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "Send full backup now";
    }
  });
})();

/* ================= BACKUP STATUS ================= */
let _backupStatusCache = null; // { ts: Number, data: Object }
const BACKUP_STATUS_TTL = 30_000; // 30 seconds
let _backupCheckedAtTimer = null;

function renderCheckedAt() {
  const el = $("#backupCheckedAt");
  if (!el || !_backupStatusCache) return;
  const secs = Math.round((Date.now() - _backupStatusCache.ts) / 1000);
  const label = secs < 5 ? "just now" : secs + " s ago";
  el.textContent = "Last checked " + label;
  el.classList.remove("hidden");
}

async function loadBackupStatus() {
  try {
    let r;
    if (_backupStatusCache && (Date.now() - _backupStatusCache.ts < BACKUP_STATUS_TTL)) {
      r = _backupStatusCache.data;
    } else {
      r = await api("/api/backup/status");
      _backupStatusCache = { ts: Date.now(), data: r };
    }
    const warn = $("#backupWarn");
    const msgEl = $("#backupWarnMsg");
    const histEl = $("#backupHistory");
    if (!warn || !msgEl || !histEl) return;

    const rows = r.rows || [];

    // ---- warning banner: based on most recent row ----
    let problem = null;
    if (rows.length > 0) {
      const latest = rows[0];
      if (latest.status === "error") {
        problem = "The last backup attempt failed" +
          (latest.note ? ": " + latest.note : "") +
          ". Check BACKUP_EMAIL and the Brevo API key.";
      } else {
        const ageDays = (Date.now() - new Date(latest.ran_at).getTime()) / (1000 * 60 * 60 * 24);
        if (ageDays > 10) {
          problem = "No successful backup in " + Math.floor(ageDays) +
            " days. Check the backup schedule and email configuration.";
        }
      }
    }

    if (problem) {
      msgEl.textContent = problem;
      warn.classList.remove("hidden");
      if (rows[0] && rows[0].status !== "error") {
        toast("Backup may be overdue. Check the Export tab.", true);
      }
    } else {
      warn.classList.add("hidden");
    }

    // ---- history list ----
    if (rows.length === 0) {
      histEl.classList.add("hidden");
    } else {
      // Build with DOM nodes so server-sourced text (note, date) is never treated as HTML
      const heading = document.createElement("p");
      heading.className = "bh-heading";
      heading.textContent = "Recent backup runs";

      const ul = document.createElement("ul");
      ul.className = "bh-list";

      rows.forEach((row) => {
        const icon = row.status === "ok" ? "✓" : row.status === "error" ? "✕" : "–";
        const iconClass = row.status === "ok" ? "bh-ok" : row.status === "error" ? "bh-err" : "bh-na";
        const dateStr = new Date(row.ran_at).toLocaleDateString("en-US", {
          month: "short", day: "numeric", year: "numeric",
        });

        const li = document.createElement("li");
        li.className = "bh-row";

        const iconSpan = document.createElement("span");
        iconSpan.className = "bh-icon " + iconClass;
        iconSpan.textContent = icon;

        const dateSpan = document.createElement("span");
        dateSpan.className = "bh-date";
        dateSpan.textContent = dateStr;

        li.appendChild(iconSpan);
        li.appendChild(dateSpan);

        if (row.note) {
          const noteSpan = document.createElement("span");
          noteSpan.className = "bh-note";
          noteSpan.textContent = row.note; // textContent — never innerHTML
          li.appendChild(noteSpan);
        }

        ul.appendChild(li);
      });

      histEl.innerHTML = ""; // clear any previous render
      histEl.appendChild(heading);
      histEl.appendChild(ul);
      histEl.classList.remove("hidden");
    }
    renderCheckedAt();
  } catch (_) {
    // Don't break the export tab if the status check fails
  }
}

/* ================= STORAGE HELPERS ================= */
// sessionStorage can throw in privacy/restricted modes — always access via
// these wrappers so a blocked storage API never breaks app initialisation.
function _ssGet(key) {
  try { return sessionStorage.getItem(key); } catch (_) { return null; }
}
function _ssSet(key, val) {
  try { sessionStorage.setItem(key, val); } catch (_) {}
}
function _ssRemove(key) {
  try { sessionStorage.removeItem(key); } catch (_) {}
}

/* ================= RUN BACKUP NOW ================= */
let _runBackupCooldownTimer = null;

const RUN_BACKUP_COOLDOWN_KEY = "runBackupCooldownUntil";

function _startRunBackupCooldown(btn, waitSec) {
  if (_runBackupCooldownTimer) clearInterval(_runBackupCooldownTimer);
  let remaining = Math.max(waitSec, 1);
  _ssSet(RUN_BACKUP_COOLDOWN_KEY, String(Date.now() + remaining * 1000));
  btn.disabled = true;
  function tick() {
    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    btn.textContent = m > 0
      ? `Try again in ${m}:${String(s).padStart(2, "0")}`
      : `Try again in ${s}s`;
    remaining -= 1;
    if (remaining < 0) {
      clearInterval(_runBackupCooldownTimer);
      _runBackupCooldownTimer = null;
      _ssRemove(RUN_BACKUP_COOLDOWN_KEY);
      btn.disabled = false;
      btn.textContent = "Run backup now";
    }
  }
  tick();
  _runBackupCooldownTimer = setInterval(tick, 1000);
}

$("#runBackupBtn").addEventListener("click", async () => {
  const btn = $("#runBackupBtn");
  if (btn.disabled) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = "Running…";
  try {
    const r = await api("/api/backup/run", { method: "POST" });
    _backupStatusCache = { ts: Date.now(), data: r }; // treat fresh run as new cache baseline
    renderCheckedAt();
    // Refresh the status UI with the rows returned by the endpoint
    const warn = $("#backupWarn");
    const msgEl = $("#backupWarnMsg");
    const histEl = $("#backupHistory");
    if (warn && msgEl && histEl) {
      // Reuse loadBackupStatus logic by passing the fresh rows
      const rows = r.rows || [];
      let problem = null;
      if (rows.length > 0) {
        const latest = rows[0];
        if (latest.status === "error") {
          problem = "The last backup attempt failed" +
            (latest.note ? ": " + latest.note : "") +
            ". Check BACKUP_EMAIL and the Brevo API key.";
        }
      }
      if (problem) {
        msgEl.textContent = problem;
        warn.classList.remove("hidden");
        toast("Backup failed — check the Export tab for details.", true);
      } else {
        warn.classList.add("hidden");
        toast("Backup sent. Check the inbox at BACKUP_EMAIL.");
      }
      // Rebuild history list
      if (rows.length === 0) {
        histEl.classList.add("hidden");
      } else {
        const heading = document.createElement("p");
        heading.className = "bh-heading";
        heading.textContent = "Recent backup runs";
        const ul = document.createElement("ul");
        ul.className = "bh-list";
        rows.forEach((row) => {
          const icon = row.status === "ok" ? "✓" : row.status === "error" ? "✕" : "–";
          const iconClass = row.status === "ok" ? "bh-ok" : row.status === "error" ? "bh-err" : "bh-na";
          const dateStr = new Date(row.ran_at).toLocaleDateString("en-US", {
            month: "short", day: "numeric", year: "numeric",
          });
          const li = document.createElement("li");
          li.className = "bh-row";
          const iconSpan = document.createElement("span");
          iconSpan.className = "bh-icon " + iconClass;
          iconSpan.textContent = icon;
          const dateSpan = document.createElement("span");
          dateSpan.className = "bh-date";
          dateSpan.textContent = dateStr;
          li.appendChild(iconSpan);
          li.appendChild(dateSpan);
          if (row.note) {
            const noteSpan = document.createElement("span");
            noteSpan.className = "bh-note";
            noteSpan.textContent = row.note;
            li.appendChild(noteSpan);
          }
          ul.appendChild(li);
        });
        histEl.innerHTML = "";
        histEl.appendChild(heading);
        histEl.appendChild(ul);
        histEl.classList.remove("hidden");
      }
    }
    btn.disabled = false;
    btn.textContent = orig;
  } catch (err) {
    if (err.status === 429) {
      const waitSec = parseInt(err.retryAfter || "300", 10);
      _startRunBackupCooldown(btn, waitSec);
      toast(err.message || "Please wait before running another backup.", true);
    } else {
      toast(err.message || "Backup failed.", true);
      btn.disabled = false;
      btn.textContent = orig;
    }
  }
});

/* ================= TABS ================= */
function switchTab(view) {
  $$(".tab").forEach((x) => x.setAttribute("aria-selected", x.dataset.view === view));
  ["log", "queue", "export"].forEach((v) => $("#view-" + v).classList.toggle("hidden", v !== view));
  const bar = $("#bar");
  bar.classList.toggle("hidden", view !== "log");
  if (view === "log") {
    const devBar = document.getElementById("_elh-dev-bar");
    bar.style.bottom = devBar ? devBar.offsetHeight + "px" : "";
  }
  window.scrollTo(0, 0);
  if (_backupCheckedAtTimer) { clearInterval(_backupCheckedAtTimer); _backupCheckedAtTimer = null; }
  if (view === "export") {
    loadBackupStatus();
    _backupCheckedAtTimer = setInterval(renderCheckedAt, 1000);
  }
  if (view === "log") {
    api("/api/config").then((cfg) => {
      aiEnabled = Boolean(cfg.aiEnabled);
      updateVoiceSection();
      updateVoiceSection();
    }).catch(() => {});
  }
}
$$(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.view)));

/* Pause the "Last checked" ticker when the browser tab is hidden;
   resume it only when the Export view is still the active in-app tab. */
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    if (_backupCheckedAtTimer) { clearInterval(_backupCheckedAtTimer); _backupCheckedAtTimer = null; }
  } else {
    const exportView = $("#view-export");
    if (exportView && !exportView.classList.contains("hidden") && !_backupCheckedAtTimer) {
      _backupCheckedAtTimer = setInterval(renderCheckedAt, 1000);
    }
  }
});

/* ================= BOOT ================= */
(async () => {
  try {
    const r = await api("/api/me");
    me = r.user;
    await enterApp();
  } catch (_) {
    await initAuthScreen();
  }
})();

let _draftTimer;

function restoreDraft() {
  let draft;
  try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); } catch (_) {}
  if (!draft) return;
  const set = (id, val) => { if (val && $(id)) $(id).value = val; };
  set("#org", draft.org);
  set("#cat", draft.cat);
  set("#date", draft.date);
  set("#addr", draft.addr);
  set("#city", draft.city);
  set("#county", draft.county);
  set("#cname", draft.cname);
  set("#ctitle", draft.ctitle);
  set("#cemail", draft.cemail);
  set("#cphone", draft.cphone);
  set("#notes", draft.notes);
  set("#owner", draft.owner);
  set("#fmethod", draft.fmethod);
  set("#due", draft.due);
  if (draft.mat) {
    const matInput = $(`input[name='mats'][value='${draft.mat.replace(/'/g, "\\'")}']`);
    if (matInput) matInput.checked = true;
  }
  riskCheck();
  validate();
  // Show the restore indicator if there is real content
  if (draft.org || draft.notes || draft.cname) _flashDraftSaved("Draft restored");
}

function _flashDraftSaved(msg) {
  const el = $("#draftStatus");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("on");
  clearTimeout(_draftTimer);
  _draftTimer = setTimeout(() => el.classList.remove("on"), 2200);
}

function clearDraft() {
  try { localStorage.removeItem(DRAFT_KEY); } catch (_) {}
  const el = $("#draftStatus");
  if (el) el.classList.remove("on");
}
