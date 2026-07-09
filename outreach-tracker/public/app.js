const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const STATUS_LABELS = {
  brochure_left: "Brochure left",
  followup_due: "Follow-up due",
  emailed: "Emailed",
  responded: "Responded",
  closed: "Closed",
};

const state = {
  user: null,
  visits: [],
  filter: "",
  search: "",
  pendingPhotos: [], // {dataUrl, kind} queued before a visit exists
};

// ---------- API helper ----------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...opts,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error((data && data.error) || "Something went wrong.");
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.add("hidden"), 2600);
}

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

// ---------- boot ----------
async function boot() {
  const cfg = await api("/api/config");
  if (cfg.signedIn) {
    try {
      const me = await api("/api/me");
      state.user = me.user;
      return enterApp();
    } catch (_) {}
  }
  enterAuth(cfg);
}

// ---------- AUTH ----------
function enterAuth(cfg) {
  hide($("#app-screen"));
  show($("#auth-screen"));
  const regTab = $("#register-tab");
  if (!cfg.registrationOpen) {
    regTab.textContent = "Set up (closed)";
    regTab.disabled = true;
    regTab.style.opacity = 0.5;
  }
  if (cfg.requiresCode) show($("#code-label"));
}

$$(".auth-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    if (tab.disabled) return;
    $$(".auth-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const mode = tab.dataset.mode;
    $("#login-form").classList.toggle("hidden", mode !== "login");
    $("#register-form").classList.toggle("hidden", mode !== "register");
    hide($("#auth-error"));
  });
});

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ phone: f.phone.value, password: f.password.value }),
    });
    state.user = data.user;
    enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    const data = await api("/api/register", {
      method: "POST",
      body: JSON.stringify({
        name: f.name.value,
        phone: f.phone.value,
        password: f.password.value,
        code: f.code ? f.code.value : "",
      }),
    });
    state.user = data.user;
    enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
});

function showAuthError(msg) {
  const e = $("#auth-error");
  e.textContent = msg;
  show(e);
}

// ---------- APP ----------
function enterApp() {
  hide($("#auth-screen"));
  show($("#app-screen"));
  $("#whoami").textContent = state.user ? state.user.name : "";
  buildFilters();
  loadVisits();
}

$("#logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  state.user = null;
  location.reload();
});

function buildFilters() {
  const wrap = $("#filters");
  const opts = [["", "All"], ...Object.entries(STATUS_LABELS)];
  wrap.innerHTML = "";
  opts.forEach(([val, label]) => {
    const b = document.createElement("button");
    b.className = "chip" + (state.filter === val ? " active" : "");
    b.textContent = label;
    b.addEventListener("click", () => {
      state.filter = val;
      buildFilters();
      loadVisits();
    });
    wrap.appendChild(b);
  });
}

let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = e.target.value.trim();
    loadVisits();
  }, 250);
});

async function loadVisits() {
  const params = new URLSearchParams();
  if (state.filter) params.set("status", state.filter);
  if (state.search) params.set("q", state.search);
  const data = await api("/api/visits?" + params.toString());
  state.visits = data.visits;
  renderVisits();
}

function fmtDate(d) {
  if (!d) return "";
  const dt = new Date(d);
  if (isNaN(dt)) return "";
  return dt.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function renderVisits() {
  const list = $("#visit-list");
  list.innerHTML = "";
  if (!state.visits.length) {
    show($("#empty-state"));
    return;
  }
  hide($("#empty-state"));
  state.visits.forEach((v) => {
    const card = document.createElement("div");
    card.className = "visit-card";
    const meta = [];
    if (v.visit_date) meta.push("📅 " + fmtDate(v.visit_date));
    if (v.address) meta.push("📍 " + v.address);
    if (v.contact_name) meta.push("👤 " + v.contact_name);
    card.innerHTML = `
      <h3></h3>
      <div class="visit-meta"></div>
      ${v.notes ? `<div class="visit-notes"></div>` : ""}
      <div class="visit-foot">
        <span class="badge ${v.followup_status}">${STATUS_LABELS[v.followup_status] || ""}</span>
        ${v.photo_count ? `<span class="photo-pill">📎 ${v.photo_count} photo${v.photo_count > 1 ? "s" : ""}</span>` : ""}
      </div>`;
    card.querySelector("h3").textContent = v.company;
    card.querySelector(".visit-meta").textContent = meta.join("   ");
    if (v.notes) card.querySelector(".visit-notes").textContent = v.notes;
    card.addEventListener("click", () => openVisit(v.id));
    list.appendChild(card);
  });
}

// ---------- MODAL ----------
const modal = $("#visit-modal");
const vform = $("#visit-form");

function openModal() { show(modal); }
function closeModal() {
  hide(modal);
  vform.reset();
  vform.id.value = "";
  state.pendingPhotos = [];
  $("#photo-grid").innerHTML = "";
  hide($("#modal-error"));
}

$("#modal-close").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

$("#new-visit-btn").addEventListener("click", () => {
  vform.reset();
  vform.id.value = "";
  state.pendingPhotos = [];
  $("#photo-grid").innerHTML = "";
  $("#modal-title").textContent = "Log a visit";
  vform.visit_date.value = new Date().toISOString().slice(0, 10);
  hide($("#delete-visit-btn"));
  hide($("#draft-email-btn"));
  $("#photo-hint").textContent = "Photos are saved once you save the visit.";
  openModal();
});

async function openVisit(id) {
  const data = await api("/api/visits/" + id);
  const v = data.visit;
  vform.id.value = v.id;
  vform.company.value = v.company || "";
  vform.address.value = v.address || "";
  vform.visit_date.value = v.visit_date ? v.visit_date.slice(0, 10) : "";
  vform.followup_status.value = v.followup_status || "brochure_left";
  vform.contact_name.value = v.contact_name || "";
  vform.contact_email.value = v.contact_email || "";
  vform.contact_phone.value = v.contact_phone || "";
  vform.notes.value = v.notes || "";
  $("#modal-title").textContent = v.company;
  show($("#delete-visit-btn"));
  show($("#draft-email-btn"));
  state.pendingPhotos = [];
  $("#photo-hint").textContent = "Tap a photo to remove it.";
  renderPhotoGrid(data.photos, true);
  openModal();
}

function renderPhotoGrid(savedPhotos, saved) {
  const grid = $("#photo-grid");
  grid.innerHTML = "";
  (savedPhotos || []).forEach((p) => {
    const el = document.createElement("div");
    el.className = "thumb";
    el.innerHTML = `<img src="/api/photos/${p.id}" alt="${p.kind}" />
      <span class="thumb-kind">${p.kind === "card" ? "Card" : "Visit"}</span>
      <button type="button" class="thumb-del" data-id="${p.id}">&times;</button>`;
    el.querySelector(".thumb-del").addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!confirm("Remove this photo?")) return;
      await api("/api/photos/" + p.id, { method: "DELETE" });
      el.remove();
      toast("Photo removed");
    });
    grid.appendChild(el);
  });
  // queued (not yet saved) photos
  state.pendingPhotos.forEach((p, idx) => {
    const el = document.createElement("div");
    el.className = "thumb";
    el.innerHTML = `<img src="${p.dataUrl}" alt="${p.kind}" />
      <span class="thumb-kind">${p.kind === "card" ? "Card" : "Visit"}</span>
      <button type="button" class="thumb-del" data-idx="${idx}">&times;</button>`;
    el.querySelector(".thumb-del").addEventListener("click", (ev) => {
      ev.stopPropagation();
      state.pendingPhotos.splice(idx, 1);
      renderPhotoGrid(savedPhotos, saved);
    });
    grid.appendChild(el);
  });
}

// photo capture + resize
$$('input[type="file"]', $("#photo-area")).forEach((input) => {
  input.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    const kind = e.target.dataset.kind;
    e.target.value = "";
    if (!file) return;
    try {
      const dataUrl = await resizeImage(file, 1280, 0.82);
      const id = vform.id.value;
      if (id) {
        // visit exists — upload immediately
        await api(`/api/visits/${id}/photos`, {
          method: "POST",
          body: JSON.stringify({ image: dataUrl, kind }),
        });
        const data = await api("/api/visits/" + id);
        renderPhotoGrid(data.photos, true);
        toast("Photo added");
      } else {
        state.pendingPhotos.push({ dataUrl, kind });
        renderPhotoGrid([], false);
      }
    } catch (err) {
      toast("Could not add photo");
    }
  });
});

function resizeImage(file, maxDim, quality) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();
    reader.onload = () => { img.src = reader.result; };
    reader.onerror = reject;
    img.onload = () => {
      let { width, height } = img;
      if (width > height && width > maxDim) { height = Math.round(height * maxDim / width); width = maxDim; }
      else if (height > maxDim) { width = Math.round(width * maxDim / height); height = maxDim; }
      const canvas = document.createElement("canvas");
      canvas.width = width; canvas.height = height;
      canvas.getContext("2d").drawImage(img, 0, 0, width, height);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    img.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// save visit
vform.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide($("#modal-error"));
  const payload = {
    company: vform.company.value,
    address: vform.address.value,
    visit_date: vform.visit_date.value || null,
    followup_status: vform.followup_status.value,
    contact_name: vform.contact_name.value,
    contact_email: vform.contact_email.value,
    contact_phone: vform.contact_phone.value,
    notes: vform.notes.value,
  };
  try {
    let visitId = vform.id.value;
    if (visitId) {
      await api("/api/visits/" + visitId, { method: "PATCH", body: JSON.stringify(payload) });
    } else {
      const data = await api("/api/visits", { method: "POST", body: JSON.stringify(payload) });
      visitId = data.visit.id;
      // upload any queued photos
      for (const p of state.pendingPhotos) {
        await api(`/api/visits/${visitId}/photos`, {
          method: "POST",
          body: JSON.stringify({ image: p.dataUrl, kind: p.kind }),
        });
      }
    }
    closeModal();
    toast("Visit saved");
    loadVisits();
  } catch (err) {
    const el = $("#modal-error");
    el.textContent = err.message;
    show(el);
  }
});

// delete visit
$("#delete-visit-btn").addEventListener("click", async () => {
  const id = vform.id.value;
  if (!id) return;
  if (!confirm("Delete this visit and its photos? This cannot be undone.")) return;
  await api("/api/visits/" + id, { method: "DELETE" });
  closeModal();
  toast("Visit deleted");
  loadVisits();
});

// copy follow-up email draft
$("#draft-email-btn").addEventListener("click", async () => {
  const company = vform.company.value || "your team";
  const contact = vform.contact_name.value ? vform.contact_name.value.split(" ")[0] : "there";
  const draft =
`Subject: Following up — Eternal Life Hospice

Hi ${contact},

Thank you for taking a moment with me during my recent visit to ${company}. I wanted to follow up and leave you my direct contact in case any of your patients or families could benefit from hospice support.

Eternal Life Hospice is an independent, Medicare-certified hospice serving Ventura and Los Angeles County. Our team provides comfort-focused care with a registered nurse reachable any hour, and we work closely with facilities like yours to make transitions smooth for patients and staff alike.

If it would be helpful, I'd be glad to stop back by, drop off additional materials, or answer any questions about how we partner on referrals.

Warm regards,
${state.user ? state.user.name : ""}
Eternal Life Hospice
805.953.7273 · info@eternallifehospice.com`;

  try {
    await navigator.clipboard.writeText(draft);
    toast("Follow-up email copied");
  } catch (_) {
    prompt("Copy this follow-up email:", draft);
  }
});

boot().catch((err) => {
  console.error(err);
  document.body.innerHTML = '<p style="padding:40px;text-align:center;font-family:sans-serif">Could not load the tracker. Please refresh.</p>';
});
