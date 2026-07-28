const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const STATUSES = ["Not started", "Email sent", "Replied", "Meeting booked", "Closed", "No interest"];
const CLOSED = ["Closed", "No interest"];
const OWNER_OPTIONS = ["Aleksandra Dubina", "Denise Chavez", "Unassigned"];

let me = null;
let visits = [];
let photos = { card: null, site: null };
let hasCard = "no";
let scanning = false;
let aiEnabled = false;
const SCAN_HINT = "Take a clear photo of the card. We'll read the name, title, email, phone, and address, then you check it. The photo is also saved with the visit.";
const SCAN_HINT_NO_AI = "Card scanning isn't set up yet — the AI integration hasn't been enabled in this Replit. Enter the details below by hand.";

/* ---------------- api ---------------- */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error((data && data.error) || "Something went wrong.");
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
      body: JSON.stringify({ phone: $("#li-phone").value, password: $("#li-pass").value }),
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
        name: $("#re-name").value,
        phone: $("#re-phone").value,
        password: $("#re-pass").value,
        code: $("#re-code").value,
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

/* ================= AI MODEL BANNER ================= */
const AI_BANNER_DISMISSED_KEY = "aiModelBannerDismissed";

function showAiModelBanner(warning) {
  if (sessionStorage.getItem(AI_BANNER_DISMISSED_KEY)) return;
  const banner = $("#aiModelBanner");
  const msg = $("#aiModelBannerMsg");
  if (!banner || !msg) return;
  msg.textContent = warning ||
    "Card scanning is unavailable — the AI model may need updating. Contact your admin.";
  banner.classList.remove("hidden");
}

$("#aiModelBannerDismiss").addEventListener("click", () => {
  const banner = $("#aiModelBanner");
  if (banner) banner.classList.add("hidden");
  sessionStorage.setItem(AI_BANNER_DISMISSED_KEY, "1");
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
  // Show/hide the voice recorder based on AI availability
  const voiceSection = $(".voice");
  if (voiceSection) voiceSection.classList.toggle("hidden", !aiEnabled);

  $("#meName").textContent = me ? me.name : "";
  populateOwners();
  $("#date").value = new Date().toISOString().slice(0, 10);
  showView("app");
  await loadVisits();
  riskCheck();
  validate();
  loadBackupStatus(); // non-blocking — populate Export tab warning in background
}

function populateOwners() {
  const sel = $("#owner");
  const names = [];
  if (me && me.name) names.push(me.name);
  for (const o of OWNER_OPTIONS) if (!names.includes(o)) names.push(o);
  sel.innerHTML = names.map((n) => `<option>${esc(n)}</option>`).join("");
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

/* ================= PHOTO CAPTURE ================= */
function shrink(file, cb) {
  const img = new Image();
  img.onload = () => {
    const max = 900, s = Math.min(1, max / Math.max(img.width, img.height));
    const c = document.createElement("canvas");
    c.width = (img.width * s) | 0;
    c.height = (img.height * s) | 0;
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    cb(c.toDataURL("image/jpeg", 0.6));
    URL.revokeObjectURL(img.src);
  };
  img.src = URL.createObjectURL(file);
}
function bindPhoto(inputSel, slot, dropSel, afterSet) {
  $(inputSel).addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    shrink(f, (d) => {
      photos[slot] = d;
      $(dropSel).classList.add("set");
      drawThumbs();
      if (afterSet) afterSet(d);
    });
  });
}
bindPhoto("#fCard", "card", "#dropCard", (d) => { if (hasCard === "yes") extractCard(d); });
bindPhoto("#fSite", "site", "#dropSite");

/* ----- business card toggle + AI auto-fill ----- */
function setHasCard(val) {
  hasCard = val;
  $$("#hasCard .segbtn").forEach((b) => b.classList.toggle("on", b.dataset.val === val));
  $("#cardScan").classList.toggle("hidden", val !== "yes");
  $("#manualHint").classList.toggle("hidden", val !== "no");
  if (val === "yes") {
    const h = $(".scanhint");
    const btn = $("#scanBtn");
    if (aiEnabled) {
      if (h) { h.textContent = SCAN_HINT; h.classList.remove("busy"); }
      if (btn) btn.disabled = false;
    } else {
      if (h) { h.textContent = SCAN_HINT_NO_AI; h.classList.remove("busy"); }
      if (btn) btn.disabled = true;
    }
  }
  validate();
}
$$("#hasCard .segbtn").forEach((b) => b.addEventListener("click", () => setHasCard(b.dataset.val)));
$("#scanBtn").addEventListener("click", () => $("#fCard").click());

async function extractCard(dataUrl) {
  if (scanning) return;
  scanning = true;
  const hint = $(".scanhint");
  if (hint) { hint.textContent = "Reading the card…"; hint.classList.add("busy"); }
  try {
    const r = await api("/api/extract-card", { method: "POST", body: JSON.stringify({ image: dataUrl }) });
    const c = r.contact || {};
    const fill = (sel, val) => { if (val && !$(sel).value.trim()) $(sel).value = val; };
    fill("#org", c.company);
    fill("#addr", c.address);
    fill("#city", c.city);
    fill("#cname", c.contact_name);
    fill("#ctitle", c.contact_title);
    fill("#cemail", c.contact_email);
    fill("#cphone", c.contact_phone);
    if (hint) { hint.textContent = "Card read — please check every detail is right."; hint.classList.remove("busy"); }
    toast("Card read. Please check the details.");
    validate();
  } catch (err) {
    if (hint) { hint.textContent = "Couldn't read the card. Please type the details by hand."; hint.classList.remove("busy"); }
    toast(err.message || "Couldn't read the card.", true);
  } finally {
    scanning = false;
  }
}

/* ----- voice notes: record → transcribe → append ----- */
let mediaRecorder = null;
let recChunks = [];
let recStream = null;
let recState = "idle"; // idle | recording | working

function pickAudioType() {
  const prefs = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus", "audio/ogg"];
  if (window.MediaRecorder && MediaRecorder.isTypeSupported) {
    for (const t of prefs) if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

function setRecHint(msg, isErr) {
  const h = $("#recHint");
  if (!h) return;
  h.textContent = msg;
  h.classList.toggle("err", !!isErr);
}
const REC_HINT_DEFAULT =
  "Talk through the visit and we'll type it up for you. Review it before saving. The recording is deleted the moment it's turned into text — nothing is stored.";

function setRecState(state) {
  recState = state;
  const btn = $("#recBtn");
  const label = btn.querySelector(".reclabel");
  btn.classList.toggle("recording", state === "recording");
  btn.classList.toggle("working", state === "working");
  btn.disabled = state === "working";
  if (state === "recording") label.textContent = "Stop recording";
  else if (state === "working") label.textContent = "Transcribing…";
  else label.textContent = "Record instead of typing";
}

function stopStream() {
  if (recStream) {
    recStream.getTracks().forEach((t) => t.stop());
    recStream = null;
  }
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
    setRecHint("This browser can't record audio. Please type your notes.", true);
    return;
  }
  try {
    recStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    setRecHint(
      "Microphone access is blocked. Allow the mic in your browser settings, or type your notes.",
      true
    );
    return;
  }
  const mimeType = pickAudioType();
  try {
    mediaRecorder = mimeType ? new MediaRecorder(recStream, { mimeType }) : new MediaRecorder(recStream);
  } catch (_) {
    mediaRecorder = new MediaRecorder(recStream);
  }
  recChunks = [];
  mediaRecorder.addEventListener("dataavailable", (e) => {
    if (e.data && e.data.size > 0) recChunks.push(e.data);
  });
  mediaRecorder.addEventListener("stop", onRecordingStop);
  mediaRecorder.start();
  setRecHint("Recording… tap Stop when you're done.");
  setRecState("recording");
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

async function onRecordingStop() {
  stopStream();
  const type = (mediaRecorder && mediaRecorder.mimeType) || (recChunks[0] && recChunks[0].type) || "audio/webm";
  const blob = new Blob(recChunks, { type });
  recChunks = [];
  mediaRecorder = null;
  if (!blob.size) {
    setRecState("idle");
    setRecHint("Nothing was recorded. Please try again.", true);
    return;
  }
  setRecState("working");
  setRecHint("Transcribing your note…");
  try {
    const dataUrl = await blobToDataUrl(blob);
    const r = await api("/api/transcribe", { method: "POST", body: JSON.stringify({ audio: dataUrl }) });
    const text = (r.text || "").trim();
    if (!text) {
      setRecHint("We couldn't make out any words. Try again in a quieter spot, or type your notes.", true);
    } else {
      appendNotes(text);
      setRecHint("Added below — please read it over and edit before saving.");
      toast("Voice note added. Please review it.");
    }
  } catch (err) {
    setRecHint(err.message || "Couldn't transcribe that. Please try again or type your notes.", true);
    toast(err.message || "Couldn't transcribe that.", true);
  } finally {
    setRecState("idle");
  }
}

function appendNotes(text) {
  const ta = $("#notes");
  const existing = ta.value.trim();
  ta.value = existing ? existing + "\n\n" + text : text;
  riskCheck();
  validate();
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = () => reject(new Error("Couldn't read the recording."));
    fr.readAsDataURL(blob);
  });
}

$("#recBtn").addEventListener("click", () => {
  if (!aiEnabled) {
    setRecHint("Voice notes aren't available yet — enable the OpenAI integration in this Replit's Integrations panel.", true);
    return;
  }
  if (recState === "recording") stopRecording();
  else if (recState === "idle") { setRecHint(REC_HINT_DEFAULT); startRecording(); }
});

function drawThumbs() {
  const labels = { card: "Business card", site: "Materials" };
  $("#thumbs").innerHTML = Object.entries(photos)
    .filter(([, d]) => d)
    .map(
      ([slot, d]) =>
        `<figure><button type="button" class="rm" data-slot="${slot}" aria-label="Remove">×</button><img src="${d}" alt=""><figcaption>${labels[slot]}</figcaption></figure>`
    )
    .join("");
  $$("#thumbs .rm").forEach((b) =>
    b.addEventListener("click", () => {
      const slot = b.dataset.slot;
      photos[slot] = null;
      $(slot === "card" ? "#dropCard" : "#dropSite").classList.remove("set");
      $(slot === "card" ? "#fCard" : "#fSite").value = "";
      drawThumbs();
    })
  );
}

/* ================= VALIDATION ================= */
function validate() {
  let ok = $("#org").value.trim() && $("#date").value && $("#attest").checked && !riskCheck();
  if (hasCard === "no") {
    ok = ok && $("#addr").value.trim() && $("#cname").value.trim();
  }
  $("#saveBtn").disabled = !ok;
}
["#org", "#date", "#notes", "#addr", "#cname"].forEach((s) => $(s).addEventListener("input", validate));
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
    follow_up_due: dueDays === "0" ? null : addDays(visitDate, dueDays),
    followup_status: dueDays === "0" ? "Closed" : "Not started",
    attested: $("#attest").checked === true,
  };

  try {
    const r = await api("/api/visits", { method: "POST", body: JSON.stringify(payload) });
    const visit = r.visit;
    const uploads = [];
    if (photos.card) uploads.push(uploadPhoto(visit.id, "card", photos.card));
    if (photos.site) uploads.push(uploadPhoto(visit.id, "site", photos.site));
    if (uploads.length) {
      try { await Promise.all(uploads); } catch (_) { toast("Visit saved, but a photo failed to upload.", true); }
    }
    clearForm();
    await loadVisits();
    switchTab("queue");
    toast("Visit saved. Follow-up clock started.");
  } catch (err) {
    toast(err.message, true);
    validate();
  }
});

async function uploadPhoto(visitId, kind, dataUrl) {
  return api(`/api/visits/${visitId}/photos`, {
    method: "POST",
    body: JSON.stringify({ kind, image: dataUrl }),
  });
}

function clearForm() {
  ["#org", "#addr", "#city", "#cname", "#ctitle", "#cemail", "#cphone", "#notes"].forEach((s) => ($(s).value = ""));
  $("#cat").selectedIndex = 0;
  $("#county").selectedIndex = 0;
  $("#due").value = "5";
  $$("#mats input").forEach((i) => (i.checked = false));
  $("#attest").checked = false;
  photos = { card: null, site: null };
  $("#fCard").value = "";
  $("#fSite").value = "";
  $("#dropCard").classList.remove("set");
  $("#dropSite").classList.remove("set");
  $("#date").value = new Date().toISOString().slice(0, 10);
  setHasCard("no");
  drawThumbs();
  riskCheck();
  validate();
}
$("#clearBtn").addEventListener("click", clearForm);

/* ================= RENDER QUEUE ================= */
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
  const cols = ["visit_date", "company", "category", "address", "city", "county", "contact_name", "contact_title", "contact_email", "contact_phone", "materials", "notes", "owner", "follow_up_due", "followup_status"];
  const head = ["Visit date", "Organization", "Category", "Address", "City", "County", "Contact", "Title", "Email", "Phone", "Materials left", "Notes", "Owner", "Follow-up due", "Status"];
  const neutralize = (s) => (/^[=+\-@\t\r]/.test(s) ? "'" + s : s);
  const rows = visits.map((v) =>
    cols
      .map((c) => {
        let val = v[c];
        if (Array.isArray(val)) val = val.join("; ");
        if ((c === "visit_date" || c === "follow_up_due") && val) val = String(val).slice(0, 10);
        return `"${neutralize(String(val ?? "")).replace(/"/g, '""')}"`;
      })
      .join(",")
  );
  const blob = new Blob(["\ufeff" + [head.join(","), ...rows].join("\r\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ELH_Field_Log_" + new Date().toISOString().slice(0, 10) + ".csv";
  a.click();
  URL.revokeObjectURL(a.href);
  toast("CSV downloaded.");
});

/* ================= BACKUP STATUS ================= */
async function loadBackupStatus() {
  try {
    const r = await api("/api/backup/status");
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
  } catch (_) {
    // Don't break the export tab if the status check fails
  }
}

/* ================= TABS ================= */
function switchTab(view) {
  $$(".tab").forEach((x) => x.setAttribute("aria-selected", x.dataset.view === view));
  ["log", "queue", "export"].forEach((v) => $("#view-" + v).classList.toggle("hidden", v !== view));
  $("#bar").classList.toggle("hidden", view !== "log");
  window.scrollTo(0, 0);
}
$$(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.view)));

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
