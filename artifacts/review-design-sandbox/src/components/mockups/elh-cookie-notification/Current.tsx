import { useState } from "react";
import "./_group.css";

// Source: website/elh-preview/assets/analytics.js, ensureCSS/showBanner/ensureModal.
// Only consent persistence and tracker loading are replaced with local preview state.
export function Current() {
  const [choice, setChoice] = useState("");
  const [manage, setManage] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const save = (value: string) => { setChoice(value); setManage(false); };
  return <main className="cookie-proof">
    <header><div className="proof-label">Current website notification</div><p className="proof-note">Original pill, extracted from the site. This preview does not save cookies or enable tracking.</p></header>
    {choice && <div className="proof-confirm" role="status">{choice} selected for this preview.<br/><button className="proof-reset" onClick={() => setChoice("")}>Show notification again</button></div>}
    {!choice && <div id="elh-cc" className="elh-cc-in" role="region" aria-label="Cookie consent">
      <div id="elh-cc-in"><p>We use <a href="https://eternallifehospice.com/privacy-policy#cookies" target="_blank" rel="noreferrer">cookies</a></p>
        <div id="elh-cc-btns"><button className="elh-ccb elh-cc-ok" onClick={() => save("All cookies")}>Accept</button>
          <button className="elh-ccb elh-cc-mg" aria-haspopup="dialog" onClick={() => setManage(true)}>Manage</button></div>
      </div>
    </div>}
    <div id="elh-cc-modal" className={manage ? "elh-cc-open" : ""} onClick={e => { if (e.target === e.currentTarget) setManage(false); }}>
      <div id="elh-cc-box" role="dialog" aria-modal="true" aria-labelledby="current-preferences-heading">
        <h2 id="current-preferences-heading">Cookie Preferences</h2>
        <p>Choose which cookies you allow. You can update your choice at any time using the Cookie Settings link in the footer.</p>
        <div className="elh-cc-row"><div className="elh-cc-row-lbl"><strong>Essential</strong><span>Required for basic site functions. Always active.</span></div><label className="elh-tog"><input type="checkbox" checked disabled aria-label="Essential cookies always on"/><span className="elh-tog-tr"/></label></div>
        <div className="elh-cc-row"><div className="elh-cc-row-lbl"><strong>Analytics &amp; Tracking</strong><span>Google Analytics, Microsoft Clarity, Brevo, and call-tracking — help us understand how the site is used and how visitors find us. All non-essential tracking is enabled or disabled together.</span></div><label className="elh-tog"><input type="checkbox" checked={analytics} onChange={e => setAnalytics(e.target.checked)} aria-label="Analytics and tracking"/><span className="elh-tog-tr"/></label></div>
        <div id="elh-cc-mbtns"><button className="elh-cc-decl" onClick={() => save("Essential cookies only")}>Decline All</button><button className="elh-cc-save" onClick={() => save(analytics ? "All cookies" : "Essential cookies only")}>Save Preferences</button></div>
      </div>
    </div>
  </main>;
}
