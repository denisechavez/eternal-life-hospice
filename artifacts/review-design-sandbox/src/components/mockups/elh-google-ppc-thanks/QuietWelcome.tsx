import './QuietWelcome.css';

export function QuietWelcome() {
  const base = import.meta.env.BASE_URL;

  return (
    <main className="quiet-welcome">
      <section className="qw-scene" aria-label="A reassuring moment of support, with two people holding hands">
        <img
          className="qw-landscape"
          src={`${base}images/quiet-welcome-care-original.jpg`}
          width={1080}
          height={1350}
          fetchPriority="high"
          decoding="async"
          alt=""
          aria-hidden="true"
        />
        <div className="qw-scene-shade" aria-hidden="true" />
        <div className="qw-brand">
          <img
            src={`${base}elh-logo-header-cream.png`}
            alt="Eternal Life Hospice"
            className="qw-logo"
          />
          <span className="qw-brand-rule" aria-hidden="true" />
          <span className="qw-tagline">Care That Honors Life.</span>
        </div>
        <p className="qw-scene-caption">A little room to pause</p>
      </section>

      <section className="qw-content" aria-labelledby="qw-heading">
        <div className="qw-confirmation">
          <div className="qw-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" focusable="false">
              <path d="M7.5 16.2 13.2 22l11.4-12" />
            </svg>
          </div>
          <p className="qw-overline">Your message is received</p>
          <h1 id="qw-heading">
            <span>Thank you.</span>{" "}
            <span>We have received</span>{" "}
            <span>your request.</span>
          </h1>
          <p className="qw-body">A member of our care team will contact you to discuss your needs and next steps.</p>
          <p className="qw-privacy">To help protect your privacy and the privacy of your loved one, please avoid sending medical details by email. Our care team can guide you to an appropriate way to share this information.</p>
          <a className="qw-return" href="https://eternallifehospice.com/">
            <span>Return to Eternal Life Hospice</span>
            <span className="qw-arrow" aria-hidden="true">↗</span>
          </a>
        </div>

        <aside className="qw-contact" aria-labelledby="qw-contact-title">
          <span className="qw-contact-line" aria-hidden="true" />
          <div>
            <p className="qw-contact-prompt" id="qw-contact-title">Need to speak with someone now?</p>
            <p className="qw-contact-copy">We're here for you 24 hours a day, 7 days a week.</p>
            <a className="qw-phone" href="tel:+18054099262">Call 805.409.9262</a>
          </div>
        </aside>
      </section>

      <footer className="qw-footer">
        <address>4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362</address>
        <span>Care That Honors Life.</span>
      </footer>
    </main>
  );
}
