import "./PersonalLetter.css";

export function PersonalLetter() {
  const logoPath = `${import.meta.env.BASE_URL}elh-logo-stacked-official.png`;

  return (
    <main className="elh-letter-page" aria-labelledby="elh-letter-title">
      <div className="elh-letter-disclosure" role="note">
        Google PPC · Design review only · Not connected to the live form
      </div>

      <header className="elh-letter-masthead">
        <img
          className="elh-letter-logo"
          src={logoPath}
          alt="Eternal Life Hospice"
        />
        <p className="elh-letter-brand-name" aria-hidden="true">
          Eternal Life Hospice
        </p>
      </header>

      <section
        className="elh-letter-content"
        aria-label="Request acknowledgment and contact information"
      >
        <div className="elh-letter-message">
          <p className="elh-letter-eyebrow">A note from our care team</p>
          <h1 id="elh-letter-title">
            Thank you. We have received your request.
          </h1>
          <p className="elh-letter-body">
            A member of our care team will contact you to discuss your needs and
            next steps.
          </p>
          <p className="elh-letter-privacy">
            Please avoid sending medical details by email.
          </p>
          <a
            className="elh-letter-return"
            href="https://eternallifehospice.com/"
          >
            <span>Return to Eternal Life Hospice</span>
            <span className="elh-letter-arrow" aria-hidden="true">
              →
            </span>
          </a>
        </div>

        <aside
          className="elh-letter-availability"
          aria-labelledby="elh-letter-availability-title"
        >
          <p className="elh-letter-availability-kicker">
            Here whenever you need us
          </p>
          <h2 id="elh-letter-availability-title">
            Need to speak with someone now?
          </h2>
          <p className="elh-letter-availability-copy">
            We're here for you 24 hours a day, 7 days a week.
          </p>
          <a
            className="elh-letter-phone"
            href="tel:+18054099262"
            aria-label="Call Eternal Life Hospice at 805.409.9262"
          >
            Call 805.409.9262
          </a>
        </aside>
      </section>

      <footer className="elh-letter-footer">
        <div>
          <p className="elh-letter-tagline">Care That Honors Life.</p>
          <address>
            4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362
          </address>
        </div>
        <p className="elh-letter-footer-note">With care, Eternal Life Hospice</p>
      </footer>
    </main>
  );
}

export default PersonalLetter;
