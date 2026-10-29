import "./AmethystAssurance.css";

export function AmethystAssurance() {
  const base = import.meta.env.BASE_URL;

  return (
    <main className="aa-page">
      <header className="aa-header">
        <a
          className="aa-brand"
          href="https://eternallifehospice.com/"
          aria-label="Eternal Life Hospice home"
        >
          <img
            className="aa-logo"
            src={`${base}elh-logo-stacked-official.png`}
            alt="Eternal Life Hospice"
          />
        </a>
      </header>

      <section className="aa-confirmation" aria-labelledby="aa-title">
        <div className="aa-confirmation-inner">
          <div className="aa-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="m5.5 12.3 4.15 4.1L18.7 7.5" />
            </svg>
          </div>
          <p className="aa-kicker">A note from Eternal Life Hospice</p>
          <h1 id="aa-title">Thank you. We have received your request.</h1>
          <p className="aa-reassurance">
            A member of our care team will contact you to discuss your needs and next steps.
          </p>
          <p className="aa-privacy">To help protect your privacy and the privacy of your loved one, please avoid sending medical details by email. Our care team can guide you to an appropriate way to share this information.</p>
        </div>
        <div className="aa-ornament" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </section>

      <section className="aa-contact" aria-labelledby="aa-contact-title">
        <div className="aa-contact-copy">
          <p className="aa-contact-label">Here when you need us</p>
          <h2 id="aa-contact-title">Need to speak with someone now?</h2>
          <p className="aa-contact-description">
            We&apos;re here for you 24 hours a day, 7 days a week.
          </p>
        </div>
        <a className="aa-call" href="tel:+18054099262" aria-label="Call Eternal Life Hospice at 805.409.9262">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M7.1 3.8h3.1l1.25 4.05-1.9 1.9a15.1 15.1 0 0 0 4.7 4.7l1.9-1.9 4.05 1.25v3.1c0 1.1-.9 2-2 2A15.7 15.7 0 0 1 5.1 5.8c0-1.1.9-2 2-2Z" />
          </svg>
          <span>Call 805.409.9262</span>
        </a>
      </section>

      <footer className="aa-footer">
        <div className="aa-footer-brand">
          <p className="aa-tagline">Care That Honors Life.</p>
          <address>
            4165 E Thousand Oaks Blvd, Suite 325B
            <br />
            Westlake Village, CA 91362
          </address>
        </div>
        <a className="aa-return" href="https://eternallifehospice.com/">
          Return to our homepage
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M4 10h11M10 4.5 15.5 10 10 15.5" />
          </svg>
        </a>
      </footer>
    </main>
  );
}

export default AmethystAssurance;
