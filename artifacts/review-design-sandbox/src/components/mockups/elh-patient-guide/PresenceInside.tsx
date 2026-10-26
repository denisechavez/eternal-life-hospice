export function PresenceInside() {
  return (
    <main className="elh-presence-inside" aria-label="Eternal Life Hospice patient guide inside covers">
      <style>{`
        @font-face {
          font-family: "ELH Presence Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Presence Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Presence Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Presence Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-weight: 500;
          font-display: swap;
        }
        .elh-presence-inside,
        .elh-presence-inside * {
          box-sizing: border-box;
        }
        .elh-presence-inside {
          --inside-cream: #f6f0e5;
          --inside-plum: #4c2943;
          --inside-gold: #a77f43;
          --inside-ink-soft: #6f5c68;
          display: grid;
          grid-template-columns: 1fr 1fr;
          width: 100%;
          height: 100dvh;
          min-height: 100%;
          overflow: hidden;
          background: var(--inside-cream);
          color: var(--inside-plum);
          font-family: "ELH Presence Jost", sans-serif;
        }
        .elh-inside-panel {
          position: relative;
          min-width: 0;
          height: 100%;
          overflow: hidden;
          padding: 48px 66px 44px;
          background:
            radial-gradient(ellipse at 0% 100%, rgba(167,127,67,.045), transparent 38%),
            var(--inside-cream);
        }
        .elh-inside-panel--right {
          border-left: 1px solid rgba(76,41,67,.25);
          padding-right: 70px;
          padding-left: 70px;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(167,127,67,.055), transparent 38%),
            #f8f3e9;
        }
        .elh-inside-logo {
          display: block;
          width: 148px;
          height: 54px;
          object-fit: contain;
          object-position: left center;
        }
        .elh-inside-photo {
          position: absolute;
          top: 47px;
          right: 66px;
          width: 94px;
          height: 55px;
          overflow: hidden;
          border-radius: 2px 2px 14px 2px;
          opacity: .84;
        }
        .elh-inside-photo img {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: 46% 43%;
        }
        .elh-inside-kicker {
          margin: 24px 0 12px;
          color: var(--inside-gold);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: .17em;
          line-height: 1.2;
          text-transform: uppercase;
        }
        .elh-inside-title {
          margin: 0;
          font-family: "ELH Presence Fraunces", Georgia, serif;
          font-size: 43px;
          font-weight: 500;
          letter-spacing: -.045em;
          line-height: 1.05;
        }
        .elh-inside-intro {
          max-width: 490px;
          margin: 24px 0 0;
          color: #55464f;
          font-size: 16px;
          line-height: 1.57;
        }
        .elh-inside-intro + .elh-inside-intro {
          margin-top: 13px;
        }
        .elh-inside-section-title {
          margin: 27px 0 0;
          font-family: "ELH Presence Fraunces", Georgia, serif;
          font-size: 22px;
          font-weight: 500;
          letter-spacing: -.025em;
          line-height: 1.2;
        }
        .elh-write-field {
          position: relative;
          height: 64px;
          margin-top: 5px;
          border-bottom: 1px solid rgba(76,41,67,.38);
        }
        .elh-write-field:first-of-type {
          margin-top: 17px;
        }
        .elh-write-label {
          position: absolute;
          bottom: 9px;
          left: 0;
          color: var(--inside-ink-soft);
          font-size: 13px;
          letter-spacing: .015em;
        }
        .elh-inside-tagline {
          margin: 23px 0 0;
          color: var(--inside-gold);
          font-family: "ELH Presence Fraunces", Georgia, serif;
          font-size: 21px;
          font-style: italic;
          line-height: 1.2;
        }
        .elh-inside-contact-list {
          display: grid;
          grid-template-columns: 1fr 1fr;
          column-gap: 32px;
          row-gap: 17px;
          margin-top: 25px;
          padding: 20px 0 21px;
          border-top: 1px solid rgba(167,127,67,.52);
          border-bottom: 1px solid rgba(167,127,67,.52);
        }
        .elh-inside-contact-item {
          min-width: 0;
        }
        .elh-inside-contact-item--wide {
          grid-column: 1 / -1;
        }
        .elh-inside-contact-label {
          display: block;
          margin-bottom: 3px;
          color: var(--inside-gold);
          font-size: 10px;
          font-weight: 500;
          letter-spacing: .15em;
          line-height: 1.3;
          text-transform: uppercase;
        }
        .elh-inside-contact-value {
          display: block;
          color: var(--inside-plum);
          font-size: 16px;
          line-height: 1.4;
        }
        .elh-inside-contact-item:first-child .elh-inside-contact-value,
        .elh-inside-contact-item:nth-child(2) .elh-inside-contact-value {
          font-size: 20px;
          letter-spacing: -.02em;
        }
        .elh-inside-notes-title {
          margin-top: 27px;
          font-size: 21px;
        }
        .elh-notes-rules {
          margin-top: 14px;
        }
        .elh-notes-rule {
          height: 43px;
          border-bottom: 1px solid rgba(76,41,67,.32);
        }
        .elh-inside-draft {
          position: absolute;
          right: 66px;
          bottom: 25px;
          left: 66px;
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 0;
          color: #897b7e;
          font-size: 9px;
          font-weight: 500;
          letter-spacing: .14em;
          line-height: 1.2;
          text-transform: uppercase;
        }
        .elh-inside-draft::before {
          width: 21px;
          height: 1px;
          background: rgba(167,127,67,.72);
          content: "";
        }
        .elh-inside-panel--right .elh-inside-draft {
          right: 70px;
          left: 70px;
        }
        @media (max-width: 767px) {
          .elh-presence-inside {
            display: block;
            height: auto;
            overflow: visible;
          }
          .elh-inside-panel {
            min-height: 100dvh;
            height: auto;
            padding: 38px 8vw 70px;
            overflow: hidden;
          }
          .elh-inside-panel--right {
            border-top: 1px solid rgba(76,41,67,.25);
            border-left: 0;
          }
          .elh-inside-title {
            font-size: clamp(36px, 9vw, 43px);
          }
          .elh-inside-draft {
            right: 8vw;
            left: 8vw;
          }
          .elh-inside-panel--right .elh-inside-draft {
            right: 8vw;
            left: 8vw;
          }
        }
      `}</style>

      <section className="elh-inside-panel elh-inside-panel--left" aria-labelledby="elh-inside-welcome">
        <img
          className="elh-inside-logo"
          src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
          alt="Eternal Life Hospice"
        />
        <div className="elh-inside-photo" aria-hidden="true">
          <img src="/__reviews-mockup/images/elh-patient-guide/care.webp" alt="" />
        </div>
        <p className="elh-inside-kicker">INSIDE FRONT COVER</p>
        <h1 className="elh-inside-title" id="elh-inside-welcome">Welcome to Eternal</h1>
        <p className="elh-inside-intro">
          This guide is a place to keep information, questions and notes as you and your family receive hospice care.
        </p>
        <p className="elh-inside-intro">
          You do not need to take everything in at once. Keep it nearby and bring your questions to your care team.
        </p>
        <h2 className="elh-inside-section-title">Make this guide your own</h2>
        <div className="elh-write-field"><span className="elh-write-label">Patient name</span></div>
        <div className="elh-write-field"><span className="elh-write-label">Preferred name</span></div>
        <div className="elh-write-field"><span className="elh-write-label">A person to contact</span></div>
        <p className="elh-inside-tagline">Care That Honors Life.</p>
        <p className="elh-inside-draft">DRAFT COPY · FOR REVIEW</p>
      </section>

      <section className="elh-inside-panel elh-inside-panel--right" aria-labelledby="elh-inside-contact">
        <p className="elh-inside-kicker">INSIDE BACK COVER</p>
        <h2 className="elh-inside-title" id="elh-inside-contact">Keep us close</h2>
        <div className="elh-inside-contact-list">
          <div className="elh-inside-contact-item">
            <span className="elh-inside-contact-label">Main</span>
            <span className="elh-inside-contact-value">805.410.1151</span>
          </div>
          <div className="elh-inside-contact-item">
            <span className="elh-inside-contact-label">Office</span>
            <span className="elh-inside-contact-value">805.953.7273</span>
          </div>
          <div className="elh-inside-contact-item elh-inside-contact-item--wide">
            <span className="elh-inside-contact-label">Email</span>
            <span className="elh-inside-contact-value">info@eternallifehospice.com</span>
          </div>
          <div className="elh-inside-contact-item elh-inside-contact-item--wide">
            <span className="elh-inside-contact-label">Address</span>
            <span className="elh-inside-contact-value">
              4165 E Thousand Oaks Blvd, Ste 325B<br />
              Westlake Village, CA 91362
            </span>
          </div>
          <div className="elh-inside-contact-item elh-inside-contact-item--wide">
            <span className="elh-inside-contact-label">Website</span>
            <span className="elh-inside-contact-value">eternallifehospice.com</span>
          </div>
        </div>
        <h3 className="elh-inside-section-title elh-inside-notes-title">Questions for your care team</h3>
        <div className="elh-notes-rules" aria-hidden="true">
          <div className="elh-notes-rule" />
          <div className="elh-notes-rule" />
          <div className="elh-notes-rule" />
          <div className="elh-notes-rule" />
          <div className="elh-notes-rule" />
        </div>
        <p className="elh-inside-draft">DRAFT COPY · FOR REVIEW</p>
      </section>
    </main>
  );
}
