import { useRef, useState } from "react";
import "./_group.css";
import "./refined.css";

export function RefinedPrivacy() {
  const [choice, setChoice] = useState("");
  const [manage, setManage] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const manageButton = useRef<HTMLButtonElement>(null);
  const save = (value: string) => { setChoice(value); setManage(false); };
  return <main className="cookie-proof refined-proof">
    <header><div className="proof-label">Eternal Life Hospice · Design preview</div><p className="proof-note">A more considered welcome, with a clear choice.<br/>Nothing here changes your actual cookie settings.</p></header>
    {choice ? <section className="proof-confirm" role="status"><strong>Your preview choice is saved.</strong><br/>{choice}. No tracking has been enabled.<br/><button className="proof-reset" onClick={() => { setChoice(""); setAnalytics(false); }}>Show notification again</button></section> :
      <section className="privacy-panel" aria-labelledby="privacy-heading">
        <div className="privacy-eyebrow"><span aria-hidden="true" className="privacy-mark">✧</span>Your privacy, your choice</div>
        <h1 id="privacy-heading">A thoughtful approach<br className="privacy-break"/> to your privacy.</h1>
        <p className="privacy-copy">We use essential cookies to keep this website working. With your permission, we also use analytics and tracking to understand visits and how people find us.</p>
        <a className="privacy-policy" href="https://eternallifehospice.com/privacy-policy#cookies" target="_blank" rel="noreferrer">Read our cookie policy <span aria-hidden="true">↗</span></a>
        {manage && <div className="privacy-preferences" id="privacy-preferences" onKeyDown={e => { if (e.key === "Escape") { setManage(false); manageButton.current?.focus(); } }}>
          <div className="privacy-pref-heading"><h2>Cookie preferences</h2><button type="button" onClick={() => { setManage(false); manageButton.current?.focus(); }} aria-label="Close preferences">×</button></div>
          <div className="privacy-pref-row"><div><strong>Essential</strong><p>Needed for site features and security.</p></div><span className="privacy-always">Always on</span></div>
          <label className="privacy-pref-row privacy-optional"><div><strong>Analytics &amp; tracking</strong><p>Google Analytics and Ads, Clarity, Brevo and other non-essential site and call tracking. Enabled or disabled together.</p></div><input type="checkbox" checked={analytics} onChange={e => setAnalytics(e.target.checked)} aria-label="Allow analytics and tracking"/></label>
          <button className="privacy-save" onClick={() => save(analytics ? "All cookies allowed" : "Essential cookies only")}>Save preferences</button>
        </div>}
        <div className="privacy-actions"><button onClick={() => save("Essential cookies only")}>Essential only</button><button onClick={() => save("All cookies allowed")}>Accept all</button></div>
        <div className="privacy-bottom"><button ref={manageButton} aria-expanded={manage} aria-controls="privacy-preferences" onClick={() => setManage(!manage)}>Manage preferences <span aria-hidden="true">{manage ? "−" : "+"}</span></button><span>Change your choice anytime.</span></div>
      </section>}
  </main>;
}
