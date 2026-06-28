/* Eternal Life Hospice — guided + AI assistant.
   Self-contained: injects its own styles + markup so it works on every page
   (including index.html / resources.html, which do not link elh.css).
   The guided answers and the phone link work with no setup. The free-text
   "ask anything" box calls a Netlify function (netlify/functions/chat) that
   adds the AI reply once OPENAI_API_KEY is configured in Netlify; if that is
   not available, it falls back gracefully to the guided answers + phone. */
(function () {
  "use strict";
  if (window.__elhChatLoaded) return;
  window.__elhChatLoaded = true;

  var PHONE_DISPLAY = "805.953.7273";
  var PHONE_TEL = "18059537273";
  var ENDPOINT = "/.netlify/functions/chat";

  // Concise, on-brand answers drawn from the site content.
  var GUIDED = [
    {
      q: "What is hospice care?",
      a: "Hospice is comfort-focused care for someone facing a serious illness \u2014 easing pain and symptoms while supporting the whole family, wherever home is. The goal is comfort, dignity and the best possible quality of time together."
    },
    {
      q: "Is it covered by Medicare?",
      a: "Yes. Hospice is fully covered under Medicare Part A \u2014 typically with no deductibles or copays for hospice services. We also work with Medi-Cal and most insurance plans."
    },
    {
      q: "What areas do you serve?",
      a: "We care for families across Ventura County and Los Angeles County \u2014 at home, in assisted living, skilled nursing, or board-and-care communities."
    },
    {
      q: "How quickly can care begin?",
      a: "Often the same day. We offer same-day admissions with 24/7 on-call nursing. The fastest way to begin is a quick call to " + PHONE_DISPLAY + "."
    },
    {
      q: "Does care happen at home?",
      a: "Yes \u2014 wherever home is. Most of our care is delivered right in the patient's own residence, with support a phone call away, day or night."
    },
    {
      q: "What therapies are included?",
      a: "At no additional cost we bring in music therapy, therapeutic massage, reiki, aromatherapy, pet therapy, sound bath, holistic medicine and end-of-life doula support \u2014 alongside the clinical team."
    },
    {
      q: "How do I start care for a loved one?",
      a: "We can guide you gently through it. The quickest path is a call to " + PHONE_DISPLAY + ", any time \u2014 we'll listen first and walk you through the next steps."
    }
  ];

  var EMERGENCY = /(emergenc|call 911|\b911\b|can'?t breathe|cannot breathe|chest pain|suicid|kill myself|end my life|overdose|unconscious|not breathing|severe bleeding)/i;

  // Clinical / health-detail questions are for a nurse, not the bot. We never
  // send these to the AI; we route the person to a real person on the phone.
  var CLINICAL = /\b(should (i|we|he|she|they|my)|is it (normal|safe|ok|okay)|how (much|many|often)|what dose|dosage|\d+\s?mg|increase (the|his|her)|lower (the|his|her)|stop (taking|the|giving)|side ?effect|morphine|oxycodone|hydrocodone|fentanyl|lorazepam|ativan|haldol|haloperidol|methadone|opioid|medication|prescrib|symptom|shortness of breath|short of breath|trouble breathing|in pain|severe pain|won'?t eat|not eating|not drinking|stopped eating|vomit|nause|fever|seizure|hallucinat|agitat|infection|\bwound\b|rash|swelling)\b/i;

  var history = []; // {role, content} pairs for the AI
  var panel, log, openBtn, dock, inputEl, sendBtn, opened = false, aiAvailable = true;
  var greeted = false, greetTimer = null, closeTimer = null, focusTimer = null;

  /* ---------- styles ---------- */
  function injectStyles() {
    var css = [
      ".elhc, .elhc *{box-sizing:border-box}",
      ".elhc{--p:#5B2E59;--deep:#3C1C3B;--gold:#C9B07E;--cream:#F5F0EB;--cmid:#EDE6DE;--cdark:#D8CDBF;--ink:#3a2b39;--mid:#5A4057;font-family:'Jost ELH',system-ui,-apple-system,Segoe UI,Roboto,sans-serif}",
      ".elhc-dock{position:fixed;right:20px;bottom:20px;z-index:2147483000;display:flex;flex-direction:column;align-items:flex-end;gap:.55rem}",
      ".elhc-dock.hide{display:none}",
      ".elhc-launch{position:relative;display:flex;align-items:center;justify-content:center;border:none;cursor:pointer;background:var(--p);color:var(--cream);width:58px;height:58px;border-radius:50%;box-shadow:0 8px 24px rgba(60,28,59,.34);transition:transform .2s,box-shadow .2s}",
      ".elhc-launch:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(60,28,59,.42)}",
      ".elhc-launch svg{width:24px;height:24px;flex-shrink:0}",
      ".elhc-launch::after{content:'';position:absolute;top:2px;right:2px;width:11px;height:11px;border-radius:50%;background:var(--gold);border:2px solid var(--cream)}",
      ".elhc-panel{position:fixed;right:20px;bottom:20px;z-index:2147483000;width:370px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 40px);background:var(--cream);border-radius:18px;box-shadow:0 24px 60px rgba(60,28,59,.34);display:none;flex-direction:column;overflow:hidden;border:1px solid var(--cdark)}",
      ".elhc-panel.open{display:flex;animation:elhcUp .42s cubic-bezier(.22,1,.36,1)}",
      ".elhc-panel.closing{display:flex;animation:elhcDown .26s cubic-bezier(.4,0,1,1) forwards}",
      "@keyframes elhcUp{from{opacity:0;transform:translateY(18px) scale(.985)}to{opacity:1;transform:none}}",
      "@keyframes elhcDown{from{opacity:1;transform:none}to{opacity:0;transform:translateY(16px) scale(.985)}}",
      ".elhc-head{background:linear-gradient(135deg,var(--p),var(--deep));color:var(--cream);padding:.95rem 1rem .9rem}",
      ".elhc-head-top{display:flex;align-items:center;justify-content:space-between;gap:.5rem}",
      ".elhc-title{font-family:'Fraunces ELH',Georgia,serif;font-size:1.12rem;line-height:1.2}",
      ".elhc-sub{font-size:11.5px;opacity:.82;margin-top:2px}",
      ".elhc-x{background:transparent;border:none;color:var(--cream);cursor:pointer;opacity:.85;padding:4px;border-radius:6px;line-height:0}",
      ".elhc-x:hover{opacity:1;background:rgba(255,255,255,.12)}",
      ".elhc-call{display:flex;align-items:center;justify-content:center;gap:.45rem;margin-top:.7rem;background:var(--gold);color:var(--deep);text-decoration:none;font-weight:700;font-size:14px;padding:.55rem;border-radius:10px}",
      ".elhc-call:hover{filter:brightness(1.04)}",
      ".elhc-call small{font-weight:500;opacity:.8}",
      ".elhc-log{flex:1;overflow-y:auto;padding:1rem .9rem;display:flex;flex-direction:column;gap:.6rem;background:var(--cream)}",
      ".elhc-msg{max-width:84%;padding:.62rem .8rem;border-radius:14px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word;animation:elhcRise .4s cubic-bezier(.22,1,.36,1) both}",
      "@keyframes elhcRise{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}",
      ".elhc-bot{align-self:flex-start;background:var(--cmid);color:var(--ink);border-bottom-left-radius:5px}",
      ".elhc-user{align-self:flex-end;background:var(--p);color:var(--cream);border-bottom-right-radius:5px}",
      ".elhc-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.2rem}",
      ".elhc-chip{background:#fff;border:1px solid var(--cdark);color:var(--p);font-family:inherit;font-size:12.5px;padding:.42rem .7rem;border-radius:20px;cursor:pointer;text-align:left;transition:background .18s,border-color .18s,transform .18s,box-shadow .18s;animation:elhcRise .42s cubic-bezier(.22,1,.36,1) both}",
      ".elhc-chip:hover{background:var(--cmid);border-color:var(--gold);transform:translateY(-1px);box-shadow:0 4px 12px rgba(60,28,59,.12)}",
      ".elhc-typing{align-self:flex-start;display:flex;gap:4px;padding:.7rem .85rem;background:var(--cmid);border-radius:14px;border-bottom-left-radius:5px;animation:elhcRise .3s ease both}",
      ".elhc-typing span{width:6px;height:6px;border-radius:50%;background:var(--p);opacity:.5;animation:elhcBlink 1.2s infinite}",
      ".elhc-typing span:nth-child(2){animation-delay:.2s}.elhc-typing span:nth-child(3){animation-delay:.4s}",
      "@keyframes elhcBlink{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:.9;transform:translateY(-3px)}}",
      ".elhc-foot{border-top:1px solid var(--cdark);padding:.6rem;background:var(--cream)}",
      ".elhc-inrow{display:flex;gap:.45rem;align-items:flex-end}",
      ".elhc-in{flex:1;resize:none;border:1px solid var(--cdark);border-radius:12px;padding:.6rem .7rem;font-family:inherit;font-size:14px;color:var(--ink);background:#fff;max-height:90px;line-height:1.4}",
      ".elhc-in:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 3px rgba(201,176,126,.25)}",
      ".elhc-send{flex-shrink:0;border:none;cursor:pointer;background:var(--p);color:var(--cream);width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;transition:background .15s}",
      ".elhc-send:hover{background:var(--deep)}.elhc-send:disabled{opacity:.5;cursor:default}",
      ".elhc-send svg{width:18px;height:18px}",
      ".elhc-note{font-size:10.5px;color:var(--mid);text-align:center;margin-top:.45rem;line-height:1.4}",
      "@media (max-width:480px){.elhc-panel{right:8px;bottom:8px;width:calc(100vw - 16px);height:calc(100vh - 16px);max-height:calc(100vh - 16px)}.elhc-dock{right:14px;bottom:14px}}",
      "@media (prefers-reduced-motion:reduce){.elhc-panel.open,.elhc-panel.closing,.elhc-msg,.elhc-chip,.elhc-typing{animation:none}.elhc-launch{transition:none}.elhc-typing span{animation:none}}",
      "@media print{.elhc-dock,.elhc-panel{display:none!important}}"
    ].join("\n");
    var s = document.createElement("style");
    s.setAttribute("data-elhc", "");
    s.textContent = css;
    document.head.appendChild(s);
  }

  /* ---------- helpers ---------- */
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(t) {
    return String(t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function reduced() {
    try { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (e) { return false; }
  }
  function scrollDown() {
    try { log.scrollTo({ top: log.scrollHeight, behavior: reduced() ? "auto" : "smooth" }); }
    catch (e) { log.scrollTop = log.scrollHeight; }
  }

  function addMsg(text, who) {
    var m = el("div", "elhc-msg " + (who === "user" ? "elhc-user" : "elhc-bot"));
    m.textContent = text;
    log.appendChild(m);
    scrollDown();
    return m;
  }

  function addChips(items) {
    var wrap = el("div", "elhc-chips");
    items.forEach(function (it, i) {
      var c = el("button", "elhc-chip");
      c.type = "button";
      c.textContent = it.q;
      c.style.animationDelay = (0.08 * i + 0.12).toFixed(2) + "s";
      c.addEventListener("click", function () {
        addMsg(it.q, "user");
        history.push({ role: "user", content: it.q });
        var pushAnswer = function () {
          addMsg(it.a, "bot");
          history.push({ role: "assistant", content: it.a });
        };
        if (reduced()) { pushAnswer(); return; }
        var t = showTyping();
        window.setTimeout(function () {
          if (t.parentNode) t.parentNode.removeChild(t);
          pushAnswer();
        }, 650);
      });
      wrap.appendChild(c);
    });
    log.appendChild(wrap);
    scrollDown();
  }

  function showTyping() {
    var t = el("div", "elhc-typing");
    t.innerHTML = "<span></span><span></span><span></span>";
    log.appendChild(t);
    scrollDown();
    return t;
  }

  /* ---------- conversation ---------- */
  function greet() {
    greeted = true;
    addMsg(
      "Hello, and welcome. I'm here to gently guide you through questions about Eternal Life Hospice \u2014 our care, coverage, and how to begin. Whenever you'd rather speak with a person, our team is one tap away, any time, 24/7.",
      "bot"
    );
    addChips(GUIDED);
  }

  function emergencyReply() {
    addMsg(
      "If this is a medical emergency, please call 911 right away. For an urgent hospice need, our nurses are available around the clock at " +
        PHONE_DISPLAY +
        " \u2014 please call and a real person will support you right now.",
      "bot"
    );
  }

  function clinicalReply() {
    addMsg(
      "I want to make sure you get the right support \u2014 a question like that is best for one of our nurses rather than me. Please call " +
        PHONE_DISPLAY +
        " any time, day or night, and a caring person will talk it through with you. If this is an emergency, please call 911.",
      "bot"
    );
  }

  function localFallback() {
    aiAvailable = false;
    addMsg(
      "I can't reach the assistant at the moment \u2014 but I can still guide you. You can tap one of the common questions below, or call our team any time at " +
        PHONE_DISPLAY +
        " and a real person will be glad to support you.",
      "bot"
    );
    addChips(GUIDED);
  }

  function send(text) {
    text = (text || "").trim();
    if (!text) return;
    addMsg(text, "user");
    history.push({ role: "user", content: text });
    if (history.length > 16) history = history.slice(-16);

    if (EMERGENCY.test(text)) {
      window.setTimeout(emergencyReply, 200);
      return;
    }
    if (CLINICAL.test(text)) {
      window.setTimeout(clinicalReply, 200);
      return;
    }
    if (!aiAvailable) {
      window.setTimeout(localFallback, 200);
      return;
    }

    var typing = showTyping();
    sendBtn.disabled = true;

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history })
    })
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(new Error("bad status"));
      })
      .then(function (data) {
        if (typing.parentNode) typing.parentNode.removeChild(typing);
        sendBtn.disabled = false;
        var reply = data && data.reply ? String(data.reply).trim() : "";
        if (!reply) { localFallback(); return; }
        addMsg(reply, "bot");
        history.push({ role: "assistant", content: reply });
      })
      .catch(function () {
        if (typing.parentNode) typing.parentNode.removeChild(typing);
        sendBtn.disabled = false;
        localFallback();
      });
  }

  /* ---------- build UI ---------- */
  function build() {
    injectStyles();

    dock = el("div", "elhc elhc-dock");

    openBtn = el("button", "elhc-launch");
    openBtn.type = "button";
    openBtn.setAttribute("aria-label", "Open the support guide");
    openBtn.setAttribute("title", "Questions? We\u2019re here");
    openBtn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 9.5 9.5 0 0 1-4-.9L3 20l1.4-4.5a8.4 8.4 0 0 1-1-4A8.38 8.38 0 0 1 12 3a8.38 8.38 0 0 1 9 8.5z"/></svg>';
    openBtn.addEventListener("click", open);

    dock.appendChild(openBtn);

    panel = el("div", "elhc elhc-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Eternal Life Hospice support guide");

    var head = el("div", "elhc-head");
    var top = el("div", "elhc-head-top");
    var titleWrap = el("div");
    titleWrap.appendChild(el("div", "elhc-title", "We\u2019re here for you"));
    titleWrap.appendChild(el("div", "elhc-sub", "Caring support \u2014 any hour, day or night, available 24/7 days a week."));
    var x = el("button", "elhc-x");
    x.type = "button";
    x.setAttribute("aria-label", "Close the support guide");
    x.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    x.addEventListener("click", close);
    top.appendChild(titleWrap);
    top.appendChild(x);
    head.appendChild(top);

    var call = el("a", "elhc-call");
    call.href = "tel:" + PHONE_TEL;
    call.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24 11.4 11.4 0 0 0 3.6.58 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.58 3.6a1 1 0 0 1-.24 1z"/></svg>' +
      "<span>Call " + PHONE_DISPLAY + " <small>\u00b7 24/7</small></span>";
    head.appendChild(call);
    panel.appendChild(head);

    log = el("div", "elhc-log");
    panel.appendChild(log);

    var foot = el("div", "elhc-foot");
    var row = el("div", "elhc-inrow");
    inputEl = el("textarea", "elhc-in");
    inputEl.rows = 1;
    inputEl.setAttribute("placeholder", "Type your question\u2026");
    inputEl.setAttribute("aria-label", "Type your question");
    inputEl.addEventListener("input", function () {
      inputEl.style.height = "auto";
      inputEl.style.height = Math.min(inputEl.scrollHeight, 90) + "px";
    });
    inputEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });
    sendBtn = el("button", "elhc-send");
    sendBtn.type = "button";
    sendBtn.setAttribute("aria-label", "Send");
    sendBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>';
    sendBtn.addEventListener("click", submit);
    row.appendChild(inputEl);
    row.appendChild(sendBtn);
    foot.appendChild(row);
    foot.appendChild(
      el(
        "div",
        "elhc-note",
        "A guide for general questions \u2014 not medical advice. For anything urgent, please call " +
          PHONE_DISPLAY +
          "."
      )
    );
    panel.appendChild(foot);

    document.body.appendChild(dock);
    document.body.appendChild(panel);
  }

  function submit() {
    var v = inputEl.value;
    inputEl.value = "";
    inputEl.style.height = "auto";
    send(v);
  }

  function open() {
    window.clearTimeout(closeTimer);
    panel.classList.remove("closing");
    panel.classList.add("open");
    dock.classList.add("hide");
    if (!opened) {
      opened = true;
      if (reduced()) greet();
      else greetTimer = window.setTimeout(greet, 220);
    }
    if (reduced()) inputEl.focus();
    else focusTimer = window.setTimeout(function () { inputEl.focus(); }, 260);
  }
  function close() {
    window.clearTimeout(greetTimer);
    window.clearTimeout(focusTimer);
    window.clearTimeout(closeTimer);
    if (!greeted) opened = false; // allow greeting on next open if it never ran
    panel.classList.remove("open");
    if (reduced()) {
      panel.classList.remove("closing");
      dock.classList.remove("hide");
      return;
    }
    panel.classList.add("closing");
    closeTimer = window.setTimeout(function () {
      panel.classList.remove("closing");
      dock.classList.remove("hide"); // reveal launcher only after panel has faded out
    }, 280);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
