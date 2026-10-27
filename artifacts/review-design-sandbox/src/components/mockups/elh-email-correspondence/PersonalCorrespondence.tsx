import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type ApprovedMessage = {
  key: string;
  subject: string;
  text: string;
  paragraphs: string[];
  originalHtml: string;
};

const DATA_URL = "/__reviews-mockup/email-design/approved-messages.json";
const LOGO_URL = "/__reviews-mockup/images/elh-patient-guide/logo-plum.png";

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
    const [question, availability, call] = paragraph.split("\n");
    return `<tr><td style="padding:14px 0 24px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-top:1px solid #c8b58d;border-bottom:1px solid #c8b58d">
        <tr><td style="padding:17px 0 16px">
          <p style="margin:0 0 5px;color:#424242;font:bold 16px/1.45 Georgia,'Times New Roman',serif">${escapeHtml(question)}</p>
          <p style="margin:0 0 13px;color:#555555;font:15px/1.55 Georgia,'Times New Roman',serif">${escapeHtml(availability)}</p>
          <a href="tel:18059537273" style="display:inline-block;color:#414141;background:#eee8dc;border:1px solid #d5c8ad;padding:10px 15px;font:bold 15px/1.25 Arial,sans-serif;text-decoration:none">${escapeHtml(call)}</a>
        </td></tr>
      </table>
    </td></tr>`;
  }

  if (paragraph.startsWith("Confirmation number:")) {
    return `<tr><td style="padding:14px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.6 Arial,sans-serif;letter-spacing:.1px">${safe}</p>
    </td></tr>`;
  }

  if (
    paragraph.startsWith("To help protect patient privacy") ||
    paragraph.startsWith("If you are experiencing a medical emergency") ||
    paragraph.startsWith("Important: This confirms receipt")
  ) {
    return `<tr><td style="padding:9px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.65 Arial,sans-serif">${safe}</p>
    </td></tr>`;
  }

  const isGreeting = /^(Dear|Hello) /.test(paragraph);
  const isSignoff = /^(With care,|With appreciation,|Warm regards,|Warmly,)$/.test(paragraph);
  const isTeam = paragraph.startsWith("The Eternal Life Hospice");
  const isTagline = /^(Here in Moments That Matter Most\.|Care That Honors Life\.)$/.test(paragraph);
  const style = isGreeting
    ? "margin:0 0 23px;color:#4a4a4a;font:16px/1.65 Georgia,'Times New Roman',serif"
    : isSignoff
      ? "margin:24px 0 3px;color:#4a4a4a;font:16px/1.65 Georgia,'Times New Roman',serif"
      : isTeam
        ? "margin:0 0 4px;color:#414141;font:bold 16px/1.5 Georgia,'Times New Roman',serif"
        : isTagline
          ? "margin:0 0 21px;color:#65605d;font:italic 14px/1.6 Georgia,'Times New Roman',serif"
          : "margin:0 0 17px;color:#414141;font:16px/1.7 Georgia,'Times New Roman',serif";

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
    html,body{margin:0;width:100%;background:#f5f0eb}
    *{box-sizing:border-box}
    @media only screen and (max-width:480px){
      .outer-pad{padding:11px 9px 18px!important}
      .letterhead{padding:22px 22px 17px!important}
      .letter-body{padding:23px 22px 22px!important}
      .letter-footer{padding:16px 22px 23px!important}
      .brand-logo{width:116px!important}
    }
  </style>
</head>
<body style="margin:0;background:#f5f0eb;color:#414141">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f5f0eb">
    <tr><td class="outer-pad" align="center" style="padding:25px 16px 34px">
      <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:100%;max-width:620px;background:#fffefa">
        <tr><td class="letterhead" style="padding:30px 46px 19px;border-top:2px solid #432440">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="left" valign="middle">
                <img class="brand-logo" src="${LOGO_URL}" width="132" alt="Eternal Life Hospice" style="display:block;width:132px;max-width:100%;height:auto;border:0">
              </td>
              <td align="right" valign="middle" style="color:#757575;font:10px/1.4 Arial,sans-serif;letter-spacing:1.15px;text-transform:uppercase">
                <span style="display:inline-block;width:23px;height:1px;background:#b5a279;vertical-align:middle;margin-right:8px"></span>
                Correspondence
              </td>
            </tr>
          </table>
          <div style="height:1px;margin-top:21px;background:#ded8ce;line-height:1px;font-size:1px">&nbsp;</div>
        </td></tr>
        <tr><td class="letter-body" style="padding:22px 46px 28px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;color:#414141;font:16px/1.7 Georgia,'Times New Roman',serif">
            ${letterRows}
          </table>
        </td></tr>
        <tr><td class="letter-footer" style="padding:17px 46px 27px;border-top:1px solid #ded8ce">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="font:13px/1.5 Arial,sans-serif">
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
</body>
</html>`;
}

export function PersonalCorrespondence() {
  const [messages, setMessages] = useState<ApprovedMessage[]>([]);
  const [activeKey, setActiveKey] = useState(() => {
    return new URLSearchParams(window.location.search).get("email") || "physician";
  });
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const loadMessages = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setLoadError(false);
    try {
      const response = await fetch(DATA_URL, { signal });
      if (!response.ok) throw new Error("Unable to load approved email records");
      const data = (await response.json()) as ApprovedMessage[];
      setMessages(data);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setLoadError(true);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadMessages(controller.signal);
    return () => controller.abort();
  }, [attempt, loadMessages]);

  useEffect(() => {
    if (messages.length && !messages.some((message) => message.key === activeKey)) {
      setActiveKey("physician");
    }
  }, [activeKey, messages]);

  useEffect(() => {
    const handleFrameHeight = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== "elh-letter-height") return;
      const frame = iframeRef.current;
      if (frame && event.source === frame.contentWindow && Number.isFinite(event.data.height)) {
        frame.style.height = `${Math.max(1, event.data.height)}px`;
      }
    };
    window.addEventListener("message", handleFrameHeight);
    return () => window.removeEventListener("message", handleFrameHeight);
  }, []);

  const activeMessage = useMemo(
    () => messages.find((message) => message.key === activeKey),
    [messages, activeKey],
  );
  const currentIndex = messages.findIndex((message) => message.key === activeKey);

  const setEmail = (key: string) => {
    setActiveKey(key);
    const url = new URL(window.location.href);
    url.searchParams.set("email", key);
    window.history.replaceState({}, "", url);
  };

  return (
    <main className="personal-review">
      <style>{`
        .personal-review{--ink:#484442;--muted:#81796f;--line:#ddd3c3;--paper:#f5f0eb;--plum:#432440;--gold:#b5a279;min-height:100dvh;background:#f5f0eb;color:var(--ink);font-family:'DM Sans','Avenir Next',sans-serif;padding:31px 40px 44px;box-sizing:border-box}
        .personal-review *{box-sizing:border-box}
        .personal-review .shell{max-width:1320px;margin:0 auto}
        .personal-review .topline{display:flex;align-items:center;justify-content:space-between;margin-bottom:23px;color:#81796f;font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
        .personal-review .brand{display:flex;align-items:center;gap:10px}
        .personal-review .brand-mark{display:grid;place-items:center;width:27px;height:27px;border:1px solid #b5a279;border-radius:50%;color:#432440;font:italic 15px Georgia,serif}
        .personal-review .edition{font-size:10px;letter-spacing:.13em}
        .personal-review .header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;border-bottom:1px solid #d9cdb7;padding:0 0 20px;margin-bottom:23px}
        .personal-review .eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.19em;color:#9a8967;font-weight:700;margin-bottom:8px}
        .personal-review h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:38px;line-height:1.02;letter-spacing:-.025em;margin:0;color:#432440}
        .personal-review .header-note{font:italic 17px/1.3 'Cormorant Garamond',Georgia,serif;color:#746b66;max-width:260px;text-align:right}
        .personal-review .toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:12px}
        .personal-review .control-label{display:block;margin-bottom:5px;color:#887d6f;font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase}
        .personal-review select{width:min(380px,100%);min-height:40px;padding:9px 38px 9px 12px;border:1px solid #d5c9b6;border-radius:3px;background:#fffefa;color:#4b4541;font:500 13px 'DM Sans','Avenir Next',sans-serif}
        .personal-review .counter{color:#81796f;font:11px 'DM Mono',monospace;letter-spacing:.05em}
        .personal-review .mail-meta{background:#f5f0eb;border:1px solid #dfd8cc;border-bottom:0;padding:15px 20px;display:grid;grid-template-columns:56px minmax(0,1fr);gap:7px 12px}
        .personal-review .meta-label{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#8b8175;font-weight:700;padding-top:2px}
        .personal-review .meta-value{font-size:13px;line-height:1.45;color:#514b48;overflow-wrap:anywhere}
        .personal-review .meta-value.subject{font-weight:600;color:#432440}
        .personal-review .paper-frame{border:1px solid #dfd8cc;background:#f5f0eb;box-shadow:0 12px 28px rgba(67,36,64,.07)}
        .personal-review iframe{display:block;border:0;width:100%;height:1px;min-height:620px;background:#f5f0eb}
        .personal-review .below{display:flex;align-items:center;justify-content:space-between;padding:13px 2px 0;color:#82796f;font:11px 'DM Mono',monospace;letter-spacing:.04em}
        .personal-review .pager{display:flex;gap:8px}
        .personal-review .pager button{border:1px solid #d5c9b6;background:#f5f0eb;color:#432440;border-radius:4px;padding:7px 11px;font:600 11px 'DM Sans',sans-serif;cursor:pointer}
        .personal-review .pager button:disabled{opacity:.42;cursor:not-allowed}
        .personal-review .state{margin:20px 0;background:#f8f4ef;border:1px solid #dfd8cc;padding:18px;color:#5d5651;font-size:14px}
        .personal-review .retry{margin-left:10px;background:#432440;color:#f5f0eb;border:0;border-radius:4px;padding:8px 12px;cursor:pointer}
        .personal-review .loading-line{height:12px;width:54%;margin:0 0 13px;border-radius:2px;background:#e8e0d5}
        .personal-review .loading-line:last-child{width:78%}
        @media(max-width:850px){.personal-review{padding:24px 22px 36px}.personal-review .header{align-items:flex-start}.personal-review .header-note{max-width:170px}}
        @media(max-width:560px){.personal-review{padding:17px 13px 28px}.personal-review .topline{margin-bottom:17px}.personal-review .edition{display:none}.personal-review .header{display:block;padding-bottom:16px;margin-bottom:18px}.personal-review h1{font-size:34px}.personal-review .header-note{text-align:left;margin-top:8px;max-width:none;font-size:16px}.personal-review .toolbar{align-items:flex-end}.personal-review select{width:100%;max-width:300px}.personal-review .mail-meta{grid-template-columns:45px minmax(0,1fr);padding:13px 12px}.personal-review .meta-value{font-size:12px}.personal-review .below{font-size:10px}}
        @media(prefers-reduced-motion:reduce){.personal-review *{scroll-behavior:auto!important}}
      `}</style>
      <div className="shell">
        <div className="topline">
          <div className="brand"><span className="brand-mark">e</span><span>Eternal Life Hospice</span></div>
          <span className="edition">Acknowledgment correspondence · design review</span>
        </div>
        <header className="header">
          <div>
            <div className="eyebrow">Unpublished preview · personal correspondence</div>
            <h1>Prepared with care.</h1>
          </div>
          <div className="header-note">An acknowledgment should feel like a letter, not a system notice.</div>
        </header>

        <section aria-label="Email design preview">
          <div className="toolbar">
            <label>
              <span className="control-label">Approved message</span>
              <select
                aria-label="Select approved message"
                value={activeKey}
                disabled={loading || messages.length === 0}
                onChange={(event) => setEmail(event.target.value)}
              >
                {messages.map((message) => (
                  <option key={message.key} value={message.key}>
                    {message.key.replaceAll("-", " ")}
                  </option>
                ))}
              </select>
            </label>
            <span className="counter">
              {messages.length > 0 && currentIndex >= 0
                ? `${String(currentIndex + 1).padStart(2, "0")} / ${String(messages.length).padStart(2, "0")}`
                : "— / 14"}
            </span>
          </div>

          {loadError ? (
            <div className="state" role="alert">
              Approved messages could not be loaded.
              <button className="retry" type="button" onClick={() => setAttempt((value) => value + 1)}>Retry</button>
            </div>
          ) : loading ? (
            <div className="state" aria-label="Loading approved messages">
              <div className="loading-line" />
              <div className="loading-line" />
              <span>Loading approved correspondence…</span>
            </div>
          ) : activeMessage ? (
            <>
              <div className="mail-meta">
                <span className="meta-label">Subject</span>
                <span className="meta-value subject">{activeMessage.subject}</span>
                <span className="meta-label">To</span>
                <span className="meta-value">[Recipient]</span>
              </div>
              <div className="paper-frame">
                <iframe
                  ref={iframeRef}
                  key={activeMessage.key}
                  title={`${activeMessage.subject} — email preview`}
                  srcDoc={makeEmailDocument(activeMessage)}
                  sandbox="allow-same-origin allow-popups allow-top-navigation-by-user-activation"
                  onLoad={(event) => {
                    const frame = event.currentTarget;
                    const height = frame.contentDocument?.documentElement.scrollHeight;
                    if (height) frame.style.height = `${height}px`;
                  }}
                />
              </div>
              <div className="below">
                <span>{activeMessage.key.replaceAll("-", " ")} · approved copy</span>
                <div className="pager">
                  <button type="button" disabled={currentIndex <= 0} onClick={() => currentIndex > 0 && setEmail(messages[currentIndex - 1].key)}>Previous</button>
                  <button type="button" disabled={currentIndex >= messages.length - 1} onClick={() => currentIndex < messages.length - 1 && setEmail(messages[currentIndex + 1].key)}>Next</button>
                </div>
              </div>
            </>
          ) : (
            <div className="state">Preparing approved correspondence…</div>
          )}
        </section>
      </div>
    </main>
  );
}
