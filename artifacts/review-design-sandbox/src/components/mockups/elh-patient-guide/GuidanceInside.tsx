export function GuidanceInside() {
  return (
    <main className="elh-inside-spread" aria-label="Eternal Life Hospice patient guide inside covers">
      <style>{`
        @font-face {
          font-family: "ELH Inside Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Inside Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Inside Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Inside Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-weight: 500;
          font-display: swap;
        }
        .elh-inside-spread,
        .elh-inside-spread * {
          box-sizing: border-box;
        }
        .elh-inside-spread {
          --inside-cream: #f6f0e5;
          --inside-plum: #4c2943;
          --inside-gold: #a77f43;
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          width: 100%;
          height: 100dvh;
          min-height: 100%;
          overflow: hidden;
          color: var(--inside-plum);
          background: var(--inside-cream);
          font-family: "ELH Inside Jost", sans-serif;
          -webkit-font-smoothing: antialiased;
        }
        .elh-inside-panel {
          position: relative;
          min-width: 0;
          height: 100%;
          overflow: hidden;
          padding: 50px 72px 34px;
          background:
            radial-gradient(ellipse at 92% 9%, rgba(205, 187, 155, .12), transparent 31%),
            var(--inside-cream);
        }
        .elh-inside-panel + .elh-inside-panel {
          border-left: 1px solid rgba(76, 41, 67, .22);
          background:
            radial-gradient(ellipse at 9% 90%, rgba(205, 187, 155, .10), transparent 33%),
            #f4eee3;
        }
        .elh-inside-head {
          display: flex;
          min-height: 76px;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }
        .elh-inside-logo {
          display: block;
          width: 164px;
          height: 66px;
          object-fit: contain;
          object-position: left top;
        }
        .elh-inside-label {
          margin: 10px 0 0;
          color: var(--inside-gold);
          font-size: 10px;
          font-weight: 500;
          letter-spacing: .15em;
          line-height: 1.45;
          text-align: right;
          white-space: nowrap;
        }
        .elh-inside-rule {
          position: relative;
          height: 1px;
          margin-top: 5px;
          background: rgba(76, 41, 67, .21);
        }
        .elh-inside-rule::before {
          position: absolute;
          top: -2px;
          left: 0;
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--inside-gold);
          content: "";
        }
        .elh-inside-title {
          margin: 34px 0 20px;
          font-family: "ELH Inside Fraunces", Georgia, serif;
          font-size: 43px;
          font-weight: 500;
          letter-spacing: -.045em;
          line-height: 1.08;
        }
        .elh-inside-copy {
          max-width: 510px;
          margin: 0;
          font-size: 16px;
          font-weight: 400;
          line-height: 1.62;
        }
        .elh-inside-copy + .elh-inside-copy {
          margin-top: 14px;
        }
        .elh-inside-subhead {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 28px 0 17px;
          font-family: "ELH Inside Fraunces", Georgia, serif;
          font-size: 22px;
          font-weight: 500;
          letter-spacing: -.02em;
          line-height: 1.2;
        }
        .elh-inside-subhead::after {
          height: 1px;
          flex: 1;
          background: rgba(167, 127, 67, .48);
          content: "";
        }
        .elh-inside-writefields {
          display: grid;
          gap: 19px;
        }
        .elh-inside-writefield {
          display: flex;
          min-height: 36px;
          align-items: flex-end;
          gap: 14px;
          color: rgba(76, 41, 67, .9);
          font-size: 13px;
          letter-spacing: .015em;
        }
        .elh-inside-writefield span:first-child {
          flex: 0 0 auto;
        }
        .elh-inside-writefield span:last-child {
          height: 24px;
          flex: 1;
          border-bottom: 1px solid rgba(76, 41, 67, .39);
        }
        .elh-inside-tagline {
          position: absolute;
          bottom: 83px;
          left: 72px;
          margin: 0;
          font-family: "ELH Inside Fraunces", Georgia, serif;
          font-size: 23px;
          font-style: italic;
          font-weight: 400;
          letter-spacing: -.025em;
        }
        .elh-inside-footer {
          position: absolute;
          right: 72px;
          bottom: 27px;
          left: 72px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding-top: 12px;
          border-top: 1px solid rgba(76, 41, 67, .17);
          color: rgba(76, 41, 67, .62);
          font-size: 8px;
          font-weight: 500;
          letter-spacing: .13em;
          line-height: 1.2;
        }
        .elh-inside-footer::before {
          position: absolute;
          top: -2px;
          left: 0;
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: var(--inside-gold);
          content: "";
        }
        .elh-inside-footer span:last-child {
          letter-spacing: .08em;
        }
        .elh-back-title {
          margin-top: 31px;
          margin-bottom: 19px;
        }
        .elh-inside-contacts {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px 25px;
        }
        .elh-contact {
          min-width: 0;
        }
        .elh-contact-label {
          display: block;
          margin-bottom: 4px;
          color: var(--inside-gold);
          font-size: 10px;
          font-weight: 500;
          letter-spacing: .12em;
          line-height: 1.3;
          text-transform: uppercase;
        }
        .elh-contact-value {
          display: block;
          color: var(--inside-plum);
          font-size: 17px;
          font-weight: 500;
          letter-spacing: .01em;
          line-height: 1.35;
          text-decoration: none;
          overflow-wrap: anywhere;
        }
        .elh-contact-wide {
          grid-column: 1 / -1;
        }
        .elh-contact-email {
          font-size: 15px;
          font-weight: 400;
        }
        .elh-contact-address {
          font-size: 14px;
          font-weight: 400;
          line-height: 1.5;
        }
        .elh-contact-website {
          font-size: 13px;
          font-weight: 500;
          letter-spacing: .055em;
        }
        .elh-back-notes {
          margin-top: 22px;
        }
        .elh-back-notes .elh-inside-subhead {
          margin-top: 0;
          margin-bottom: 10px;
          font-size: 20px;
        }
        .elh-note-rules {
          display: grid;
          gap: 22px;
        }
        .elh-note-rule {
          height: 19px;
          border-bottom: 1px solid rgba(76, 41, 67, .32);
        }
        @media (max-width: 900px) {
          .elh-inside-panel {
            padding-right: 7.5%;
            padding-left: 7.5%;
          }
          .elh-inside-footer {
            right: 7.5%;
            left: 7.5%;
          }
          .elh-inside-tagline {
            left: 7.5%;
          }
          .elh-inside-title {
            font-size: clamp(31px, 6.3vw, 43px);
          }
          .elh-inside-copy {
            font-size: clamp(13px, 2.35vw, 16px);
          }
        }
        @media (max-width: 620px) {
          .elh-inside-spread {
            grid-template-columns: 1fr 1fr;
          }
          .elh-inside-panel {
            padding: 27px 5.8% 28px;
          }
          .elh-inside-logo {
            width: 110px;
            height: 48px;
          }
          .elh-inside-label {
            margin-top: 7px;
            font-size: 7px;
            letter-spacing: .1em;
          }
          .elh-inside-head {
            min-height: 55px;
          }
          .elh-inside-title {
            margin-top: 24px;
            font-size: clamp(25px, 7vw, 35px);
          }
          .elh-inside-copy {
            font-size: 11px;
            line-height: 1.5;
          }
          .elh-inside-copy + .elh-inside-copy {
            margin-top: 10px;
          }
          .elh-inside-subhead {
            margin-top: 20px;
            font-size: 17px;
          }
          .elh-inside-writefields {
            gap: 11px;
          }
          .elh-inside-writefield {
            gap: 6px;
            font-size: 9px;
          }
          .elh-inside-tagline {
            bottom: 75px;
            font-size: 16px;
          }
          .elh-inside-footer {
            right: 5.8%;
            bottom: 22px;
            left: 5.8%;
            font-size: 6px;
          }
          .elh-contact-label {
            font-size: 7px;
          }
          .elh-contact-value {
            font-size: 10px;
          }
          .elh-contact-email,
          .elh-contact-address {
            font-size: 9px;
          }
          .elh-contact-website {
            font-size: 8px;
          }
          .elh-inside-contacts {
            gap: 12px 8px;
          }
          .elh-back-notes {
            margin-top: 17px;
          }
          .elh-back-notes .elh-inside-subhead {
            font-size: 15px;
          }
          .elh-note-rules {
            gap: 14px;
          }
        }
      `}</style>

      <section className="elh-inside-panel" aria-label="Inside front cover">
        <header className="elh-inside-head">
          <img
            className="elh-inside-logo"
            src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
            alt="Eternal Life Hospice"
          />
          <p className="elh-inside-label">INSIDE FRONT COVER</p>
        </header>
        <div className="elh-inside-rule" aria-hidden="true" />

        <h1 className="elh-inside-title">Welcome to Eternal</h1>
        <p className="elh-inside-copy">
          This guide is a place to keep information, questions and notes as you and your family receive hospice care.
        </p>
        <p className="elh-inside-copy">
          You do not need to take everything in at once. Keep it nearby and bring your questions to your care team.
        </p>

        <h2 className="elh-inside-subhead">Make this guide your own</h2>
        <div className="elh-inside-writefields" aria-label="Personalize this guide">
          <div className="elh-inside-writefield"><span>Patient name</span><span aria-hidden="true" /></div>
          <div className="elh-inside-writefield"><span>Preferred name</span><span aria-hidden="true" /></div>
          <div className="elh-inside-writefield"><span>A person to contact</span><span aria-hidden="true" /></div>
        </div>

        <p className="elh-inside-tagline">Care That Honors Life.</p>
        <footer className="elh-inside-footer">
          <span>DRAFT COPY · FOR REVIEW</span>
          <span>ETERNAL LIFE HOSPICE</span>
        </footer>
      </section>

      <section className="elh-inside-panel" aria-label="Inside back cover">
        <header className="elh-inside-head">
          <img
            className="elh-inside-logo"
            src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
            alt="Eternal Life Hospice"
          />
          <p className="elh-inside-label">INSIDE BACK COVER</p>
        </header>
        <div className="elh-inside-rule" aria-hidden="true" />

        <h1 className="elh-inside-title elh-back-title">Keep us close</h1>
        <div className="elh-inside-contacts">
          <div className="elh-contact">
            <span className="elh-contact-label">Main</span>
            <span className="elh-contact-value">805.410.1151</span>
          </div>
          <div className="elh-contact">
            <span className="elh-contact-label">Office</span>
            <span className="elh-contact-value">805.953.7273</span>
          </div>
          <div className="elh-contact elh-contact-wide">
            <span className="elh-contact-value elh-contact-email">info@eternallifehospice.com</span>
          </div>
          <div className="elh-contact elh-contact-wide">
            <span className="elh-contact-value elh-contact-address">
              4165 E Thousand Oaks Blvd, Ste 325B<br />
              Westlake Village, CA 91362
            </span>
          </div>
          <div className="elh-contact elh-contact-wide">
            <span className="elh-contact-value elh-contact-website">eternallifehospice.com</span>
          </div>
        </div>

        <section className="elh-back-notes" aria-label="Writing space for questions">
          <h2 className="elh-inside-subhead">Questions for your care team</h2>
          <div className="elh-note-rules" aria-hidden="true">
            <div className="elh-note-rule" />
            <div className="elh-note-rule" />
            <div className="elh-note-rule" />
            <div className="elh-note-rule" />
          </div>
        </section>

        <footer className="elh-inside-footer">
          <span>DRAFT COPY · FOR REVIEW</span>
          <span>ETERNAL LIFE HOSPICE</span>
        </footer>
      </section>
    </main>
  );
}
