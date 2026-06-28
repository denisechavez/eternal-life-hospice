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

  // A few gentle conversation starters shown on the greeting — kept short so the
  // panel feels like a warm chat, not a long FAQ menu. People can ask anything
  // in their own words in the box below.
  var STARTERS = [GUIDED[0], GUIDED[1], GUIDED[6]];

  var EMERGENCY = /(emergenc|call 911|\b911\b|can'?t breathe|cannot breathe|chest pain|suicid|kill myself|end my life|overdose|unconscious|not breathing|severe bleeding)/i;

  // Clinical / health-detail questions are for a nurse, not the bot. We never
  // send these to the AI; we route the person to a real person on the phone.
  var CLINICAL = /\b(should (i|we|he|she|they|my)|is it (normal|safe|ok|okay)|how (much|many|often)|what dose|dosage|\d+\s?mg|increase (the|his|her)|lower (the|his|her)|stop (taking|the|giving)|side ?effect|morphine|oxycodone|hydrocodone|fentanyl|lorazepam|ativan|haldol|haloperidol|methadone|opioid|medication|prescrib|symptom|shortness of breath|short of breath|trouble breathing|in pain|severe pain|won'?t eat|not eating|not drinking|stopped eating|vomit|nause|fever|seizure|hallucinat|agitat|infection|\bwound\b|rash|swelling)\b/i;

  // When someone asks to be phoned back, we offer a small in-chat form rather
  // than sending it to the AI.
  var CALLBACK = /(call me|call back|callback|have (someone|somebody) call|someone to call|request a call|can you call|could you call|please call me)/i;

  var history = []; // {role, content} pairs for the AI
  var panel, log, openBtn, dock, inputEl, sendBtn, teaser, backdrop, opened = false, aiAvailable = true;
  var greeted = false, greetTimer = null, closeTimer = null, focusTimer = null;

  /* ---------- styles ---------- */
  function injectStyles() {
    var css = [
      ".elhc, .elhc *{box-sizing:border-box}",
      ".elhc{--p:#5B2E59;--deep:#3C1C3B;--gold:#C9B07E;--blue:#4F7396;--blue-d:#3D5C79;--cream:#F5F0EB;--cmid:#EDE6DE;--cdark:#D8CDBF;--ink:#3a2b39;--mid:#5A4057;font-family:'Jost ELH',system-ui,-apple-system,Segoe UI,Roboto,sans-serif}",
      ".elhc-dock{position:fixed;right:36px;bottom:20px;z-index:2147483000;display:flex;flex-direction:column;align-items:flex-end;gap:.55rem}",
      ".elhc-dock.hide{display:none}",
      ".elhc-launch{position:relative;display:flex;align-items:center;justify-content:center;border:none;cursor:pointer;background:var(--p);color:var(--cream);width:58px;height:58px;border-radius:50%;box-shadow:0 8px 24px rgba(60,28,59,.34);transition:transform .2s,box-shadow .2s}",
      ".elhc-launch:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(60,28,59,.42)}",
      ".elhc-launch svg{width:24px;height:24px;flex-shrink:0}",
      ".elhc-launch::after{content:'';position:absolute;top:2px;right:2px;width:11px;height:11px;border-radius:50%;background:var(--blue);border:2px solid var(--cream)}",
      ".elhc-teaser{position:relative;max-width:236px;background:#fff;color:var(--ink);border:1px solid var(--cdark);border-radius:14px;border-bottom-right-radius:5px;padding:.62rem .72rem;font-size:13px;line-height:1.45;box-shadow:0 12px 30px rgba(60,28,59,.24);cursor:pointer;animation:elhcRise .42s cubic-bezier(.22,1,.36,1) both}",
      ".elhc-teaser:hover{border-color:var(--blue)}",
      ".elhc-teaser strong{display:block;font-family:'Fraunces ELH',Georgia,serif;font-weight:600;font-size:14px;color:var(--p);margin-bottom:2px}",
      ".elhc-teaser-close{position:absolute;top:-9px;right:-9px;width:21px;height:21px;border-radius:50%;background:var(--p);color:var(--cream);border:2px solid var(--cream);cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;line-height:0}",
      ".elhc-teaser-close:hover{background:var(--deep)}",
      ".elhc-teaser-close svg{width:10px;height:10px}",
      ".elhc-chip-cb{background:var(--p);color:var(--cream);border-color:var(--p)}",
      ".elhc-chip-cb:hover{background:var(--deep);border-color:var(--deep);color:var(--cream)}",
      ".elhc-cb{align-self:stretch;background:#fff;border:1px solid var(--cdark);border-radius:14px;padding:.75rem .8rem;display:flex;flex-direction:column;gap:.55rem;animation:elhcRise .4s cubic-bezier(.22,1,.36,1) both}",
      ".elhc-cb label{font-size:11.5px;color:var(--mid);display:block;margin-bottom:.22rem}",
      ".elhc-cb input,.elhc-cb textarea{width:100%;border:1px solid var(--cdark);border-radius:10px;padding:.5rem .6rem;font-family:inherit;font-size:13.5px;color:var(--ink);background:#fff}",
      ".elhc-cb textarea{resize:none;min-height:46px;line-height:1.4}",
      ".elhc-cb input:focus,.elhc-cb textarea:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 3px rgba(79,115,150,.22)}",
      ".elhc-cb-err{color:#9a2b2b;font-size:11.5px}",
      ".elhc-cb-actions{display:flex;gap:.5rem;align-items:center}",
      ".elhc-cb-submit{flex:1;border:none;cursor:pointer;background:var(--p);color:var(--cream);font-family:inherit;font-weight:700;font-size:13.5px;padding:.58rem;border-radius:10px;transition:background .15s}",
      ".elhc-cb-submit:hover{background:var(--deep)}.elhc-cb-submit:disabled{opacity:.6;cursor:default}",
      ".elhc-cb-cancel{background:transparent;border:none;color:var(--mid);font-family:inherit;font-size:12.5px;cursor:pointer;padding:.42rem}",
      ".elhc-cb-cancel:hover{color:var(--p)}",
      ".elhc-backdrop{position:fixed;inset:0;z-index:2147482998;background:rgba(60,28,59,.42);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px);opacity:0;visibility:hidden;transition:opacity .32s ease,visibility .32s ease}",
      ".elhc-backdrop.show{opacity:1;visibility:visible}",
      ".elhc-panel{position:fixed;right:16px;bottom:16px;z-index:2147483000;width:312px;max-width:calc(100vw - 24px);height:462px;max-height:calc(100vh - 32px);background:var(--cream);border-radius:20px;box-shadow:-10px 20px 60px rgba(60,28,59,.26),0 4px 14px rgba(60,28,59,.10);display:none;flex-direction:column;overflow:hidden;border:1px solid var(--cdark)}",
      "@media(max-width:480px){.elhc-panel{right:12px;left:12px;top:12px;bottom:12px;width:auto;height:auto;max-height:none}}",
      ".elhc-panel.open{display:flex;animation:elhcSlideIn .44s cubic-bezier(.22,1,.36,1)}",
      ".elhc-panel.closing{display:flex;animation:elhcSlideOut .3s cubic-bezier(.4,0,1,1) forwards}",
      "@keyframes elhcSlideIn{from{transform:translateX(100%)}to{transform:none}}",
      "@keyframes elhcSlideOut{from{transform:none}to{transform:translateX(100%)}}",
      ".elhc-head{background:linear-gradient(180deg,#ffffff,var(--cream));color:var(--deep);padding:.9rem .85rem .85rem;border-bottom:1px solid var(--cdark)}",
      ".elhc-head-top{display:flex;align-items:center;justify-content:space-between;gap:.4rem}",
      ".elhc-title{font-family:'Fraunces ELH',Georgia,serif;font-size:.9rem;line-height:1.15;color:var(--deep);white-space:nowrap}",
      ".elhc-sub{font-size:11.5px;color:var(--p);opacity:.78;margin-top:2px;white-space:nowrap}",
      ".elhc-x{background:transparent;border:none;color:var(--p);cursor:pointer;opacity:.7;padding:4px;border-radius:6px;line-height:0}",
      ".elhc-x:hover{opacity:1;background:rgba(91,46,89,.1)}",
      ".elhc-call{display:flex;align-items:center;justify-content:center;gap:.45rem;margin-top:.7rem;background:var(--blue);color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:.55rem;border-radius:10px}",
      ".elhc-call:hover{background:var(--blue-d)}",
      ".elhc-call small{font-weight:500;opacity:.8}",
      ".elhc-log{flex:1;overflow-y:auto;padding:1rem .9rem;display:flex;flex-direction:column;gap:.6rem;background:var(--cream)}",
      ".elhc-msg{max-width:84%;padding:.62rem .8rem;border-radius:14px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word;animation:elhcRise .4s cubic-bezier(.22,1,.36,1) both}",
      "@keyframes elhcRise{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}",
      ".elhc-bot{align-self:flex-start;background:var(--cmid);color:var(--ink);border-bottom-left-radius:5px}",
      ".elhc-user{align-self:flex-end;background:var(--p);color:var(--cream);border-bottom-right-radius:5px}",
      ".elhc-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.2rem}",
      ".elhc-chip{background:#fff;border:1px solid var(--cdark);color:var(--p);font-family:inherit;font-size:12.5px;padding:.42rem .7rem;border-radius:20px;cursor:pointer;text-align:left;transition:background .18s,border-color .18s,transform .18s,box-shadow .18s;animation:elhcRise .42s cubic-bezier(.22,1,.36,1) both}",
      ".elhc-chip:hover{background:var(--cmid);border-color:var(--blue);transform:translateY(-1px);box-shadow:0 4px 12px rgba(60,28,59,.12)}",
      ".elhc-typing{align-self:flex-start;display:flex;gap:4px;padding:.7rem .85rem;background:var(--cmid);border-radius:14px;border-bottom-left-radius:5px;animation:elhcRise .3s ease both}",
      ".elhc-typing span{width:6px;height:6px;border-radius:50%;background:var(--p);opacity:.5;animation:elhcBlink 1.2s infinite}",
      ".elhc-typing span:nth-child(2){animation-delay:.2s}.elhc-typing span:nth-child(3){animation-delay:.4s}",
      "@keyframes elhcBlink{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:.9;transform:translateY(-3px)}}",
      ".elhc-foot{border-top:1px solid var(--cdark);padding:.6rem;background:var(--cream)}",
      ".elhc-inrow{display:flex;gap:.45rem;align-items:flex-end}",
      ".elhc-in{flex:1;resize:none;border:1px solid var(--cdark);border-radius:12px;padding:.6rem .7rem;font-family:inherit;font-size:14px;color:var(--ink);background:#fff;max-height:90px;line-height:1.4}",
      ".elhc-in:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 3px rgba(79,115,150,.25)}",
      ".elhc-send{flex-shrink:0;border:none;cursor:pointer;background:var(--p);color:var(--cream);width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;transition:background .15s}",
      ".elhc-send:hover{background:var(--deep)}.elhc-send:disabled{opacity:.5;cursor:default}",
      ".elhc-send svg{width:18px;height:18px}",
      ".elhc-note{font-size:10.5px;color:var(--mid);text-align:center;margin-top:.45rem;line-height:1.4}",
      "@media (max-width:480px){.elhc-panel{right:8px;bottom:8px;width:calc(100vw - 16px);height:calc(100vh - 16px);max-height:calc(100vh - 16px)}.elhc-dock{right:14px;bottom:14px}}",
      "@media (prefers-reduced-motion:reduce){.elhc-panel.open,.elhc-panel.closing,.elhc-msg,.elhc-chip,.elhc-typing,.elhc-teaser{animation:none}.elhc-launch{transition:none}.elhc-typing span{animation:none}}",
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
  function encodeForm(obj) {
    return Object.keys(obj)
      .map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(obj[k]); })
      .join("&");
  }
  function reduced() {
    try { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (e) { return false; }
  }
  function scrollDown() {
    try { log.scrollTo({ top: log.scrollHeight, behavior: reduced() ? "auto" : "smooth" }); }
    catch (e) { log.scrollTop = log.scrollHeight; }
  }

  // Reveal speed: aim for a natural, human cadence regardless of length, but
  // never so slow it feels broken or so fast it's instant.
  function charDelay(text) {
    return Math.min(Math.max(Math.round(950 / text.length), 10), 26);
  }
  // Gently "type" text into a bubble, character by character.
  function typeInto(node, text, done) {
    var i = 0, delay = charDelay(text);
    var step = function () {
      i += 1;
      node.textContent = text.slice(0, i);
      scrollDown();
      if (i < text.length) window.setTimeout(step, delay);
      else if (done) done();
    };
    step();
  }

  function addMsg(text, who, stream, done) {
    var m = el("div", "elhc-msg " + (who === "user" ? "elhc-user" : "elhc-bot"));
    log.appendChild(m);
    if (who === "bot" && stream && !reduced()) {
      typeInto(m, text, done);
    } else {
      m.textContent = text;
      if (done) done();
    }
    scrollDown();
    return m;
  }

  // Play a short series of bot bubbles one after another, each preceded by the
  // typing dots, so the welcome feels like a real person responding.
  function botSequence(lines, done) {
    var i = 0;
    var next = function () {
      if (i >= lines.length) { if (done) done(); return; }
      var line = lines[i++];
      if (reduced()) { addMsg(line, "bot"); next(); return; }
      var t = showTyping();
      var pause = Math.min(420 + line.length * 11, 1100);
      window.setTimeout(function () {
        if (t.parentNode) t.parentNode.removeChild(t);
        addMsg(line, "bot", true, function () {
          window.setTimeout(next, 320);
        });
      }, pause);
    };
    next();
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
          addMsg(it.a, "bot", true);
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
    botSequence(
      [
        "Hello, thank you for reaching out.",
        "I\u2019m here to guide you through any hospice-related questions that you may have. How can I best support you?"
      ],
      function () {
        addCallbackChip();
      }
    );
  }

  function addCallbackChip() {
    var wrap = el("div", "elhc-chips");
    var c = el("button", "elhc-chip elhc-chip-cb");
    c.type = "button";
    c.textContent = "Request a callback";
    c.addEventListener("click", showCallbackForm);
    wrap.appendChild(c);
    log.appendChild(wrap);
    scrollDown();
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
      "I\u2019m having trouble responding just now \u2014 but please don\u2019t let that stop you. Our team is available any time at " +
        PHONE_DISPLAY +
        ", and a real person will be glad to support you.",
      "bot"
    );
    addCallbackChip();
  }

  /* ---------- callback request ---------- */
  function showCallbackForm() {
    addMsg(
      "Of course \u2014 I'd be glad to arrange that. Leave your name and number below and a member of our team will call you. If it's urgent, calling " +
        PHONE_DISPLAY +
        " is the fastest way to reach us.",
      "bot"
    );

    var form = el("div", "elhc-cb");

    var nameWrap = el("div");
    nameWrap.appendChild(el("label", null, "Your name"));
    var nameIn = el("input");
    nameIn.type = "text";
    nameIn.setAttribute("autocomplete", "name");
    nameIn.placeholder = "First and last name";
    nameWrap.appendChild(nameIn);

    var phoneWrap = el("div");
    phoneWrap.appendChild(el("label", null, "Phone number"));
    var phoneIn = el("input");
    phoneIn.type = "tel";
    phoneIn.setAttribute("autocomplete", "tel");
    phoneIn.placeholder = "805.000.0000";
    phoneWrap.appendChild(phoneIn);

    var timeWrap = el("div");
    timeWrap.appendChild(el("label", null, "Best time to reach you (optional)"));
    var timeIn = el("input");
    timeIn.type = "text";
    timeIn.placeholder = "e.g. mornings, after 5pm";
    timeWrap.appendChild(timeIn);

    var noteWrap = el("div");
    noteWrap.appendChild(el("label", null, "Anything we should know? (optional)"));
    var noteIn = el("textarea");
    noteIn.placeholder = "No medical details needed.";
    noteWrap.appendChild(noteIn);

    var err = el("div", "elhc-cb-err");

    var actions = el("div", "elhc-cb-actions");
    var submitBtn = el("button", "elhc-cb-submit");
    submitBtn.type = "button";
    submitBtn.textContent = "Send request";
    var cancelBtn = el("button", "elhc-cb-cancel");
    cancelBtn.type = "button";
    cancelBtn.textContent = "Maybe later";
    actions.appendChild(submitBtn);
    actions.appendChild(cancelBtn);

    form.appendChild(nameWrap);
    form.appendChild(phoneWrap);
    form.appendChild(timeWrap);
    form.appendChild(noteWrap);
    form.appendChild(err);
    form.appendChild(actions);
    log.appendChild(form);
    scrollDown();
    try { nameIn.focus(); } catch (e) {}

    cancelBtn.addEventListener("click", function () {
      if (form.parentNode) form.parentNode.removeChild(form);
      addMsg(
        "No problem at all. Whenever you're ready, I'm here \u2014 or you can call us any time at " +
          PHONE_DISPLAY +
          ".",
        "bot"
      );
    });

    submitBtn.addEventListener("click", function () {
      var name = (nameIn.value || "").trim();
      var phone = (phoneIn.value || "").trim();
      if (!name) {
        err.textContent = "Please add your name so we know who we're calling.";
        nameIn.focus();
        return;
      }
      if (phone.replace(/[^0-9]/g, "").length < 10) {
        err.textContent = "Please add a phone number we can reach you at.";
        phoneIn.focus();
        return;
      }
      err.textContent = "";
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending\u2026";
      submitCallback(
        {
          name: name,
          phone: phone,
          preferred_time: (timeIn.value || "").trim(),
          message: (noteIn.value || "").trim()
        },
        form,
        submitBtn,
        err
      );
    });
  }

  function submitCallback(data, form, submitBtn, err) {
    var body = encodeForm({
      "form-name": "elh-chat-callback",
      source: "chat",
      "bot-field": "",
      name: data.name,
      phone: data.phone,
      preferred_time: data.preferred_time,
      message: data.message
    });
    fetch("/", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body
    })
      .then(function (r) {
        if (!r.ok) throw new Error("bad status");
        if (form.parentNode) form.parentNode.removeChild(form);
        addMsg(
          "Thank you, " +
            data.name.split(" ")[0] +
            ". I've passed this along \u2014 a member of our team will call you" +
            (data.preferred_time ? " (" + data.preferred_time + ")" : "") +
            " as soon as we can. If anything comes up in the meantime, we're always here at " +
            PHONE_DISPLAY +
            ".",
          "bot"
        );
      })
      .catch(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send request";
        err.textContent =
          "I couldn't send that just now \u2014 please call us at " +
          PHONE_DISPLAY +
          " and we'll help right away.";
      });
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
    if (CALLBACK.test(text)) {
      window.setTimeout(showCallbackForm, 200);
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
        addMsg(reply, "bot", true);
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

    // Gentle welcome nudge beside the launcher so visitors feel greeted before
    // they even open the panel. Dismissible, and shows once per visit.
    teaser = el("div", "elhc-teaser");
    teaser.setAttribute("role", "button");
    teaser.setAttribute("tabindex", "0");
    teaser.setAttribute("aria-label", "Open the support guide");
    teaser.style.display = "none";
    teaser.innerHTML =
      "<strong>Hello</strong>Thank you for reaching out. I\u2019m here to guide you through any hospice questions you may have. How can I best support you?";
    var tClose = el("button", "elhc-teaser-close");
    tClose.type = "button";
    tClose.setAttribute("aria-label", "Dismiss");
    tClose.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    tClose.addEventListener("click", function (e) { e.stopPropagation(); dismissTeaser(true); });
    teaser.appendChild(tClose);
    teaser.addEventListener("click", open);
    teaser.addEventListener("keydown", function (e) {
      if (e.target !== teaser) return; // ignore keys from the close button
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
    dock.insertBefore(teaser, openBtn);

    panel = el("div", "elhc elhc-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Eternal Life Hospice support guide");

    var head = el("div", "elhc-head");
    var top = el("div", "elhc-head-top");
    var titleWrap = el("div");
    titleWrap.appendChild(el("div", "elhc-title", "Here in Moments that Matter Most"));
    titleWrap.appendChild(el("div", "elhc-sub", "To guide and support from this moment forward."));
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

    backdrop = el("div", "elhc elhc-backdrop");
    backdrop.addEventListener("click", close);

    document.body.appendChild(dock);
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    maybeShowTeaser();
  }

  function maybeShowTeaser() {
    if (opened) return;
    try { if (sessionStorage.getItem("elhcTeaserSeen")) return; } catch (e) {}
    var delay = reduced() ? 700 : 2200;
    window.setTimeout(function () {
      if (opened || !teaser) return;
      teaser.style.display = "block";
      try { sessionStorage.setItem("elhcTeaserSeen", "1"); } catch (e) {}
      // Gently retire the nudge if it goes unnoticed, so it never nags.
      window.setTimeout(function () { if (!opened) dismissTeaser(false); }, 14000);
    }, delay);
  }

  function dismissTeaser(remember) {
    if (teaser) teaser.style.display = "none";
    if (remember) { try { sessionStorage.setItem("elhcTeaserSeen", "1"); } catch (e) {} }
  }

  function submit() {
    var v = inputEl.value;
    inputEl.value = "";
    inputEl.style.height = "auto";
    send(v);
  }

  function open() {
    dismissTeaser(true);
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
      dock.classList.remove("hide"); // reveal launcher only after panel has slid out
    }, 300);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
