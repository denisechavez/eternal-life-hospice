import React, { useEffect, useMemo, useState } from "react";

type ApprovedMessage = {
  key: string;
  subject: string;
  text: string;
  paragraphs: string[];
  originalHtml: string;
};

const DATA_URL = "/__reviews-mockup/email-design/approved-messages.json";
const LOGO_PLUM = "/__reviews-mockup/images/elh-patient-guide/logo-plum.png";

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderParagraph(paragraph: string) {
  const safe = escapeHtml(paragraph);
  if (paragraph.startsWith("Need to speak with someone now?\n")) {
    const lines = paragraph.split("\n");
    return `<tr><td style="padding:5px 0 25px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">
        <tr><td style="border-top:1px solid #d8c8a5;padding-top:17px">
          <p style="margin:0 0 5px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif">${escapeHtml(lines[0])}</p>
          <p style="margin:0 0 13px;color:#505050;font:15px/1.55 Georgia,'Times New Roman',serif">${escapeHtml(lines[1])}</p>
          <a href="tel:18059537273" style="display:inline-block;padding:11px 17px;background:#eee6d6;border:1px solid #b5a279;color:#414141;font:bold 14px/1.2 Arial,sans-serif;text-decoration:none">${escapeHtml(lines[2])}</a>
        </td></tr>
      </table>
    </td></tr>`;
  }

  const isGreeting = /^(Dear|Hello) /.test(paragraph);
  const isSignoff = /^(With care,|With appreciation,|Warm regards,|Warmly,)$/.test(paragraph);
  const isTeam = paragraph.startsWith("The Eternal Life Hospice");
  const isTagline = /^(Here in Moments That Matter Most\.|Care That Honors Life\.)$/.test(paragraph);
  const isConfirmation = paragraph.startsWith("Confirmation number:");
  const isNotice =
    paragraph.startsWith("To help protect patient privacy") ||
    paragraph.startsWith("If you are experiencing a medical emergency") ||
    paragraph.startsWith("Important: This confirms receipt") ||
    paragraph.startsWith("Scheduling note:") ||
    paragraph.startsWith("Please note:");

  let style = "margin:0 0 17px;color:#414141;font:16px/1.68 Georgia,'Times New Roman',serif";
  if (isGreeting) style = "margin:0 0 22px;color:#414141;font:16px/1.65 Georgia,'Times New Roman',serif";
  if (isSignoff) style = "margin:23px 0 3px;color:#414141;font:16px/1.65 Georgia,'Times New Roman',serif";
  if (isTeam) style = "margin:0 0 4px;color:#414141;font:bold 16px/1.5 Georgia,'Times New Roman',serif";
  if (isTagline) style = "margin:0 0 22px;color:#555555;font:italic 14px/1.6 Georgia,'Times New Roman',serif";
  if (isConfirmation) style = "margin:18px 0 11px;padding-top:14px;border-top:1px solid #e5dfd2;color:#555555;font:13px/1.6 Arial,sans-serif;letter-spacing:.1px";
  if (isNotice) style = "margin:9px 0 0;color:#555555;font:13px/1.65 Arial,sans-serif";

  return `<tr><td><p style="${style}">${safe}</p></td></tr>`;
}

function makeEmailDocument(message: ApprovedMessage) {
  const letterRows = message.paragraphs.map(renderParagraph).join("");
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body{margin:0!important;padding:0!important;width:100%!important}
    body{background:#432440;color:#414141;-webkit-text-size-adjust:100%}
    table{border-collapse:collapse}
    @media only screen and (max-width:480px){
      .outer-pad{padding:12px 7px 18px!important}
      .folio{padding:7px!important}
      .seal-cell{padding:15px 17px 12px!important}
      .seal-ring{width:64px!important;height:64px!important}
      .seal-logo{width:43px!important}
      .letter-content{padding:22px 19px 19px!important}
      .letter-footer{padding:0 19px 20px!important}
      .letter-copy{font-size:15.5px!important;line-height:1.66!important}
    }
  </style>
</head>
<body style="margin:0;background:#432440;color:#414141">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#432440">
    <tr><td class="outer-pad" align="center" style="padding:22px 14px 30px">
      <table role="presentation" class="folio" width="620" cellpadding="0" cellspacing="0" style="width:100%;max-width:620px;padding:10px;background:#b5a279">
        <tr><td style="padding:1px;background:#432440">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#fffefa">
            <tr><td class="seal-cell" style="padding:19px 37px 16px;border-bottom:1px solid #e4dac9">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="85" valign="middle" style="width:85px">
                    <table role="presentation" class="seal-ring" width="70" height="70" cellpadding="0" cellspacing="0" style="width:70px;height:70px;border:1px solid #b5a279;border-radius:50%;background:#f5f0eb">
                      <tr><td align="center" valign="middle" style="border:3px double #d7c7a2;border-radius:50%">
                        <img class="seal-logo" src="${LOGO_PLUM}" width="48" alt="Eternal Life Hospice" style="display:block;width:48px;max-width:100%;height:auto;border:0">
                      </td></tr>
                    </table>
                  </td>
                  <td valign="middle" style="padding-left:17px">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr><td height="1" style="height:1px;background:#d7c7a2;font-size:1px;line-height:1px">&nbsp;</td></tr>
                      <tr><td align="right" style="padding-top:7px;color:#9a8967;font:10px/1 Arial,sans-serif;letter-spacing:2px">&nbsp;</td></tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td></tr>
            <tr><td class="letter-content" style="padding:30px 48px 25px">
              <table role="presentation" class="letter-copy" width="100%" cellpadding="0" cellspacing="0" style="width:100%;color:#414141;font:16px/1.68 Georgia,'Times New Roman',serif">
                ${letterRows}
              </table>
            </td></tr>
            <tr><td class="letter-footer" style="padding:0 48px 26px">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="padding-top:15px;border-top:1px solid #d8c8a5;font:13px/1.5 Arial,sans-serif">
                  <a href="mailto:info@eternallifehospice.com" style="color:#535353;text-decoration:none;overflow-wrap:anywhere">info@eternallifehospice.com</a><br>
                  <span style="display:inline-block;padding-top:9px;color:#555555;font:12px/1.55 Arial,sans-serif">
                    Eternal Life Hospice<br>
                    4165 E Thousand Oaks Blvd, Suite 325B<br>
                    Westlake Village, CA 91362
                  </span>
                </td></tr>
              </table>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

function prettyName(key: string) {
  return key.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function AmethystSeal() {
  const [messages, setMessages] = useState<ApprovedMessage[]>([]);
  const [activeKey, setActiveKey] = useState(() => {
    return new URLSearchParams(window.location.search).get("email") || "physician";
  });
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load approved email records");
        return response.json();
      })
      .then((data: ApprovedMessage[]) => {
        if (!mounted) return;
        setMessages(data);
        setLoadError(false);
      })
      .catch(() => {
        if (mounted) setLoadError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (messages.length && !messages.some((message) => message.key === activeKey)) {
      setActiveKey("physician");
    }
  }, [activeKey, messages]);

  const activeMessage = useMemo(
    () => messages.find((message) => message.key === activeKey),
    [messages, activeKey],
  );
  const currentIndex = messages.findIndex((message) => message.key === activeKey);

  const selectEmail = (key: string) => {
    setActiveKey(key);
    const url = new URL(window.location.href);
    url.searchParams.set("email", key);
    window.history.replaceState({}, "", url);
  };

  const retry = () => {
    setLoadError(false);
    setMessages([]);
    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load approved email records");
        return response.json();
      })
      .then((data: ApprovedMessage[]) => setMessages(data))
      .catch(() => setLoadError(true));
  };

  return (
    <main className="amethyst-review">
      <style>{`
        .amethyst-review{--ink:#4a4545;--muted:#81796f;--line:#d9cdb7;--paper:#f5f0eb;--plum:#432440;--gold:#b5a279;min-height:100dvh;background:#f5f0eb;color:var(--ink);font-family:'DM Sans','Avenir Next',sans-serif;padding:30px 38px 44px;box-sizing:border-box}
        .amethyst-review *{box-sizing:border-box}
        .amethyst-review .shell{max-width:1340px;margin:0 auto}
        .amethyst-review .topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;color:#81796f;font-size:10px;font-weight:700;letter-spacing:.17em;text-transform:uppercase}
        .amethyst-review .brand{display:flex;align-items:center;gap:11px}
        .amethyst-review .brand-seal{width:26px;height:26px;border:1px solid var(--gold);border-radius:50%;display:grid;place-items:center;color:var(--plum);font:italic 13px Georgia,serif}
        .amethyst-review .header{display:flex;justify-content:space-between;align-items:flex-end;gap:22px;border-bottom:1px solid var(--line);padding:0 0 20px;margin-bottom:23px}
        .amethyst-review .eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.18em;color:#9a8967;font-weight:700;margin-bottom:8px}
        .amethyst-review h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:38px;line-height:1.02;letter-spacing:-.025em;margin:0;color:var(--plum)}
        .amethyst-review .header-note{font:italic 16px/1.35 'Cormorant Garamond',Georgia,serif;color:#746b66;max-width:280px;text-align:right}
        .amethyst-review .toolbar{display:grid;grid-template-columns:minmax(210px, .8fr) minmax(0,1.8fr);gap:18px;align-items:stretch;margin-bottom:15px}
        .amethyst-review .selector-wrap{display:flex;align-items:center;gap:12px;padding:13px 15px;border:1px solid #dfd8cc;background:#faf7f2}
        .amethyst-review label{color:#897d6c;font-size:10px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;white-space:nowrap}
        .amethyst-review select{width:100%;min-width:0;border:0;background:transparent;color:#514b48;font:600 13px 'DM Sans','Avenir Next',sans-serif;outline:none;cursor:pointer}
        .amethyst-review .mail-meta{background:#f5f0eb;border:1px solid #dfd8cc;padding:13px 18px;display:grid;grid-template-columns:52px minmax(0,1fr) 25px minmax(90px,.5fr);gap:8px 10px;align-items:center}
        .amethyst-review .meta-label{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#8b8175;font-weight:700}
        .amethyst-review .meta-value{font-size:12px;line-height:1.4;color:#514b48;overflow-wrap:anywhere}
        .amethyst-review .meta-value.subject{font-weight:600;color:var(--plum)}
        .amethyst-review .preview-frame{border:1px solid #d9cdb7;background:var(--plum);box-shadow:0 13px 27px rgba(67,36,64,.12)}
        .amethyst-review iframe{display:block;border:0;width:100%;height:700px;background:var(--plum)}
        .amethyst-review .below{display:flex;align-items:center;justify-content:space-between;padding:12px 2px 0;color:#82796f;font:10px 'DM Mono',monospace;letter-spacing:.04em}
        .amethyst-review .pager{display:flex;gap:8px}
        .amethyst-review .pager button{border:1px solid #d5c9b6;background:#f5f0eb;color:var(--plum);border-radius:3px;padding:7px 11px;font:600 11px 'DM Sans',sans-serif;cursor:pointer}
        .amethyst-review .pager button:hover:not(:disabled){background:#ebe3d7}
        .amethyst-review .pager button:disabled{opacity:.42;cursor:not-allowed}
        .amethyst-review .state{margin:18px 0;background:#faf7f2;border:1px solid #dfd8cc;padding:19px;color:#5d5651;font-size:14px}
        .amethyst-review .retry{margin-left:10px;background:var(--plum);color:#f5f0eb;border:0;border-radius:3px;padding:8px 12px;cursor:pointer}
        @media(max-width:820px){.amethyst-review{padding:24px 20px 34px}.amethyst-review .header{align-items:flex-start}.amethyst-review .header-note{max-width:200px}.amethyst-review .toolbar{grid-template-columns:1fr}.amethyst-review .selector-wrap{padding:10px 13px}}
        @media(max-width:560px){.amethyst-review{padding:17px 12px 27px}.amethyst-review .topline{margin-bottom:18px}.amethyst-review .topline .edition{display:none}.amethyst-review .header{display:block;padding-bottom:16px;margin-bottom:17px}.amethyst-review h1{font-size:34px}.amethyst-review .header-note{text-align:left;margin-top:8px;max-width:none;font-size:15px}.amethyst-review .toolbar{gap:9px;margin-bottom:10px}.amethyst-review .selector-wrap{gap:9px}.amethyst-review .mail-meta{grid-template-columns:43px minmax(0,1fr);padding:12px}.amethyst-review .meta-label:nth-of-type(2){grid-column:1}.amethyst-review .meta-value:nth-of-type(2){grid-column:2}.amethyst-review .meta-value{font-size:11px}.amethyst-review iframe{height:900px}.amethyst-review .below{font-size:9px}}
        @media(prefers-reduced-motion:reduce){.amethyst-review *{transition:none!important}}
      `}</style>
      <div className="shell">
        <div className="topline">
          <div className="brand"><span className="brand-seal">e</span><span>Eternal Life Hospice</span></div>
          <span className="edition">Acknowledgment correspondence · design review</span>
        </div>
        <header className="header">
          <div>
            <div className="eyebrow">Unpublished preview · amethyst seal</div>
            <h1>A mark of recognition.</h1>
          </div>
          <div className="header-note">An intimate folio composition, anchored by the Eternal identity.</div>
        </header>

        {loadError ? (
          <div className="state" role="alert">
            Approved messages could not be loaded.
            <button className="retry" type="button" onClick={retry}>Retry</button>
          </div>
        ) : messages.length === 0 ? (
          <div className="state" aria-live="polite">Loading approved messages…</div>
        ) : (
          <>
            <div className="toolbar">
              <div className="selector-wrap">
                <label htmlFor="amethyst-email-select">Request type</label>
                <select
                  id="amethyst-email-select"
                  value={activeKey}
                  onChange={(event) => selectEmail(event.target.value)}
                >
                  {messages.map((message) => (
                    <option key={message.key} value={message.key}>{prettyName(message.key)}</option>
                  ))}
                </select>
              </div>
              {activeMessage ? (
                <div className="mail-meta" aria-label="Email details">
                  <span className="meta-label">Subject</span>
                  <span className="meta-value subject">{activeMessage.subject}</span>
                  <span className="meta-label">To</span>
                  <span className="meta-value">[Recipient]</span>
                </div>
              ) : <div className="state">Preparing approved correspondence…</div>}
            </div>

            {activeMessage && (
              <>
                <div className="preview-frame">
                  <iframe
                    title={`${activeMessage.subject} — email preview`}
                    srcDoc={makeEmailDocument(activeMessage)}
                    sandbox="allow-same-origin allow-popups allow-top-navigation-by-user-activation"
                    onLoad={(event) => {
                      const frame = event.currentTarget;
                      const doc = frame.contentDocument;
                      if (!doc) return;
                      const fitFrame = () => {
                        frame.style.height = `${Math.max(500, doc.documentElement.scrollHeight, doc.body?.scrollHeight || 0)}px`;
                      };
                      fitFrame();
                      if (doc.fonts?.ready) void doc.fonts.ready.then(fitFrame);
                    }}
                  />
                </div>
                <div className="below">
                  <span>{String(currentIndex + 1).padStart(2, "0")} / {String(messages.length).padStart(2, "0")}</span>
                  <div className="pager">
                    <button
                      type="button"
                      disabled={currentIndex <= 0}
                      onClick={() => currentIndex > 0 && selectEmail(messages[currentIndex - 1].key)}
                    >Previous</button>
                    <button
                      type="button"
                      disabled={currentIndex >= messages.length - 1}
                      onClick={() => currentIndex < messages.length - 1 && selectEmail(messages[currentIndex + 1].key)}
                    >Next</button>
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
