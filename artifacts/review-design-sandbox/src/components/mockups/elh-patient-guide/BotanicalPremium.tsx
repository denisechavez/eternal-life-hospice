import React from "react";

export function BotanicalPremium() {
  return (
    <main className="botanical-premium" aria-label="Eternal Life Hospice patient and family guide, three-panel design concept">
      <style>{`
        @font-face {
          font-family: BotanicalFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: BotanicalFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: BotanicalJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: BotanicalJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .botanical-premium, .botanical-premium * { box-sizing: border-box; }
        .botanical-premium {
          --bp-paper: #f4efe5;
          --bp-paper-deep: #e9dfcf;
          --bp-plum: #492f49;
          --bp-plum-dark: #34243a;
          --bp-gold: #ad9060;
          --bp-ink: #403840;
          --bp-muted: #776b70;
          width: 100%;
          height: 100%;
          min-height: 0;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          overflow: hidden;
          background: var(--bp-paper);
          color: var(--bp-ink);
          font-family: BotanicalJost, sans-serif;
          isolation: isolate;
        }
        .bp-panel {
          position: relative;
          width: 100%;
          height: 100%;
          min-width: 0;
          overflow: hidden;
        }
        .bp-panel + .bp-panel { border-left: 1px solid rgba(73,47,73,.22); }
        .bp-label {
          position: absolute;
          z-index: 5;
          left: 34px;
          top: 24px;
          margin: 0;
          font-size: 9px;
          line-height: 1;
          font-weight: 500;
          letter-spacing: .18em;
          text-transform: uppercase;
        }
        .bp-cover {
          background: var(--bp-paper);
        }
        .bp-cover-photo {
          position: absolute;
          inset: 0 0 38% 0;
          width: 100%;
          height: 62%;
          object-fit: cover;
          object-position: 39% center;
          display: block;
        }
        .bp-cover-photo::after { content: ""; }
        .bp-cover-photo-wash {
          position: absolute;
          inset: 0 0 38% 0;
          background: linear-gradient(180deg, rgba(52,36,58,.34), transparent 29%, rgba(52,36,58,.02) 72%, rgba(52,36,58,.18));
          pointer-events: none;
        }
        .bp-cover .bp-label { color: #f7f0e6; }
        .bp-cover-paper {
          position: absolute;
          inset: 55% 0 0;
          background:
            radial-gradient(ellipse at 12% 95%, rgba(173,144,96,.09), transparent 45%),
            var(--bp-paper);
        }
        .bp-cover-logo {
          position: absolute;
          z-index: 2;
          left: 8.3%;
          top: 59.2%;
          width: 31%;
          max-height: 12%;
          object-fit: contain;
          object-position: left center;
          display: block;
          mix-blend-mode: multiply;
        }
        .bp-cover-rule {
          position: absolute;
          left: 8.3%;
          top: 73.3%;
          width: 12%;
          height: 2px;
          background: var(--bp-gold);
        }
        .bp-cover-title {
          position: absolute;
          left: 8.1%;
          top: 76%;
          width: 84%;
          margin: 0;
          color: var(--bp-plum);
          font-family: BotanicalFraunces, Georgia, serif;
          font-size: 43px;
          line-height: .98;
          letter-spacing: -.045em;
          font-weight: 500;
        }
        .bp-cover-tagline {
          position: absolute;
          left: 8.4%;
          bottom: 8.4%;
          margin: 0;
          color: #62535f;
          font-size: 13px;
          line-height: 1.25;
          letter-spacing: .045em;
        }
        .bp-cover-site {
          position: absolute;
          right: 8.2%;
          bottom: 8.4%;
          margin: 0;
          color: var(--bp-plum);
          font-size: 10px;
          line-height: 1.25;
          letter-spacing: .06em;
        }
        .bp-letter {
          padding: 66px 48px 38px;
          background:
            radial-gradient(ellipse at 96% 0%, rgba(173,144,96,.10), transparent 27%),
            var(--bp-paper);
        }
        .bp-letter::before {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          width: 9px;
          height: 100%;
          background: var(--bp-plum);
        }
        .bp-letter::after {
          content: "";
          position: absolute;
          right: -57px;
          bottom: -79px;
          width: 220px;
          height: 220px;
          border: 1px solid rgba(173,144,96,.27);
          border-radius: 50%;
          box-shadow: 0 0 0 15px rgba(173,144,96,.035), 0 0 0 31px rgba(173,144,96,.03);
          pointer-events: none;
        }
        .bp-letter .bp-label {
          left: auto;
          right: 34px;
          top: 27px;
          color: var(--bp-muted);
        }
        .bp-letter-content { position: relative; z-index: 1; }
        .bp-letter-kicker {
          margin: 0 0 9px;
          color: #92794f;
          font-size: 10px;
          line-height: 1.2;
          font-weight: 500;
          letter-spacing: .17em;
          text-transform: uppercase;
        }
        .bp-letter-title {
          margin: 0 0 20px;
          color: var(--bp-plum);
          font-family: BotanicalFraunces, Georgia, serif;
          font-size: 36px;
          line-height: 1.03;
          font-weight: 500;
          letter-spacing: -.035em;
        }
        .bp-draft {
          display: inline-block;
          margin: 0 0 18px;
          padding: 6px 9px 5px;
          border: 1px solid rgba(73,47,73,.28);
          color: var(--bp-plum);
          font-size: 8.5px;
          line-height: 1;
          letter-spacing: .13em;
          font-weight: 500;
        }
        .bp-letter-body {
          color: #51494f;
          font-size: 14px;
          line-height: 1.43;
          letter-spacing: .002em;
        }
        .bp-letter-body p { margin: 0 0 11px; }
        .bp-letter-body .bp-greeting { margin-bottom: 12px; color: var(--bp-plum); }
        .bp-signoff { margin-top: 16px; }
        .bp-signoff p { margin: 0; }
        .bp-name {
          margin-top: 7px !important;
          color: var(--bp-plum);
          font-family: BotanicalFraunces, Georgia, serif;
          font-size: 22px;
          line-height: 1.04;
        }
        .bp-role {
          color: var(--bp-muted);
          font-size: 10.5px;
          line-height: 1.48;
          letter-spacing: .025em;
        }
        .bp-back {
          background: #ede5d8;
          color: var(--bp-plum);
        }
        .bp-back-photo {
          position: absolute;
          inset: 0 0 auto;
          width: 100%;
          height: 25%;
          object-fit: cover;
          object-position: 78% 43%;
          display: block;
        }
        .bp-back-photo-overlay {
          position: absolute;
          inset: 0 0 auto;
          height: 25%;
          background: linear-gradient(180deg, rgba(52,36,58,.38), transparent 65%);
        }
        .bp-back .bp-label { color: #fff9f0; }
        .bp-back-content {
          position: absolute;
          inset: 22% 0 0;
          padding: 28px 42px 25px;
          background:
            linear-gradient(135deg, rgba(255,255,255,.42), transparent 54%),
            #ede5d8;
        }
        .bp-back-heading {
          margin: 0 0 17px;
          color: var(--bp-plum);
          font-family: BotanicalFraunces, Georgia, serif;
          font-size: 39px;
          line-height: 1;
          font-weight: 500;
          letter-spacing: -.04em;
        }
        .bp-contact-card {
          position: relative;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px 15px;
          padding: 17px 17px 16px;
          background: var(--bp-plum);
          color: #f5efe6;
        }
        .bp-contact-card::after {
          content: "";
          position: absolute;
          right: 0;
          top: 0;
          width: 4px;
          height: 100%;
          background: var(--bp-gold);
        }
        .bp-contact-block { min-width: 0; }
        .bp-contact-label {
          display: block;
          margin-bottom: 4px;
          color: #c9b994;
          font-size: 8px;
          line-height: 1;
          font-weight: 500;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .bp-contact-value {
          display: block;
          color: #fff9ef;
          font-size: 14px;
          line-height: 1.25;
          letter-spacing: .005em;
          overflow-wrap: anywhere;
        }
        .bp-contact-address {
          grid-column: 1 / -1;
          padding-top: 11px;
          border-top: 1px solid rgba(238,222,190,.25);
        }
        .bp-contact-address .bp-contact-value { font-size: 12px; line-height: 1.4; }
        .bp-back-site {
          margin: 11px 0 0;
          color: #665767;
          font-size: 10px;
          line-height: 1.2;
          letter-spacing: .09em;
        }
        .bp-writing {
          position: relative;
          margin-top: 22px;
        }
        .bp-writing-title {
          display: flex;
          align-items: baseline;
          gap: 8px;
          margin: 0 0 8px;
          color: var(--bp-plum);
          font-family: BotanicalFraunces, Georgia, serif;
          font-size: 19px;
          line-height: 1.1;
          font-weight: 500;
        }
        .bp-writing-title::after {
          content: "";
          flex: 1;
          height: 1px;
          background: rgba(173,144,96,.65);
        }
        .bp-lines {
          display: grid;
          gap: 0;
        }
        .bp-line {
          height: 22px;
          border-bottom: 1px solid rgba(73,47,73,.27);
        }
        .bp-writing-questions { margin-top: 19px; }
        .bp-footer-label {
          position: absolute;
          right: 0;
          bottom: 0;
          color: #857980;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        @media (max-width: 900px) {
          .bp-label { left: 5%; }
          .bp-cover-title { font-size: clamp(30px, 6.3vw, 43px); }
          .bp-letter { padding-left: 7%; padding-right: 7%; }
          .bp-letter-title { font-size: clamp(27px, 5vw, 36px); }
          .bp-letter-body { font-size: clamp(11px, 1.8vw, 14px); }
          .bp-back-content { padding-left: 6%; padding-right: 6%; }
          .bp-contact-card { padding-left: 12px; padding-right: 12px; }
          .bp-contact-value { font-size: 12px; }
        }
      `}</style>

      <section className="bp-panel bp-cover" aria-label="Front cover">
        <img className="bp-cover-photo" src="/__reviews-mockup/images/elh-patient-guide/premium-botanical.jpg" alt="Magnolia branches in a ceramic vase beside a walnut table and plum linen in a softly lit family home" />
        <div className="bp-cover-photo-wash" aria-hidden="true" />
        <p className="bp-label">Front cover</p>
        <div className="bp-cover-paper" aria-hidden="true" />
        <img className="bp-cover-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png" alt="Eternal Life Hospice" />
        <div className="bp-cover-rule" aria-hidden="true" />
        <h1 className="bp-cover-title">Patient &amp; Family<br />Guide</h1>
        <p className="bp-cover-tagline">Care That Honors Life.</p>
        <p className="bp-cover-site">eternallifehospice.com</p>
      </section>

      <section className="bp-panel bp-letter" aria-label="Inside front cover, welcome letter draft">
        <p className="bp-label">Inside front cover</p>
        <div className="bp-letter-content">
          <p className="bp-letter-kicker">A personal welcome</p>
          <h2 className="bp-letter-title">A note from<br />Aleksandra</h2>
          <p className="bp-draft">DRAFT FOR ALEKSANDRA’S REVIEW</p>
          <div className="bp-letter-body">
            <p className="bp-greeting">Dear family,</p>
            <p>When someone you love needs hospice care, there can be a great deal to take in. You may have questions you have not yet found words for. You do not need to have every answer today.</p>
            <p>At Eternal, we begin by getting to know the person at the center of care—and the family beside them. What brings comfort? What matters most? What would make today feel more like their own?</p>
            <p>My hope is that this guide gives you a place to begin, return to and make your own. Bring us your questions, concerns and the small details that help us understand your loved one.</p>
            <div className="bp-signoff">
              <p>With warmth,</p>
              <p className="bp-name">Aleksandra Dubina</p>
              <p className="bp-role">Founder &amp; CEO<br />Certified Hospice Administrator</p>
            </div>
          </div>
        </div>
      </section>

      <section className="bp-panel bp-back" aria-label="Inside back cover, contact information and family notes">
        <img className="bp-back-photo" src="/__reviews-mockup/images/elh-patient-guide/premium-botanical.jpg" alt="" />
        <div className="bp-back-photo-overlay" aria-hidden="true" />
        <p className="bp-label">Inside back cover</p>
        <div className="bp-back-content">
          <h2 className="bp-back-heading">Keep us close</h2>
          <div className="bp-contact-card">
            <div className="bp-contact-block">
              <span className="bp-contact-label">Main</span>
              <span className="bp-contact-value">805.410.1151</span>
            </div>
            <div className="bp-contact-block">
              <span className="bp-contact-label">Office</span>
              <span className="bp-contact-value">805.953.7273</span>
            </div>
            <div className="bp-contact-block">
              <span className="bp-contact-label">Email</span>
              <span className="bp-contact-value">info@eternallifehospice.com</span>
            </div>
            <div className="bp-contact-block bp-contact-address">
              <span className="bp-contact-label">Visit</span>
              <span className="bp-contact-value">4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</span>
            </div>
          </div>
          <p className="bp-back-site">eternallifehospice.com</p>
          <div className="bp-writing">
            <h3 className="bp-writing-title">Your care team</h3>
            <div className="bp-lines" aria-label="Three blank write-in lines">
              <div className="bp-line" /><div className="bp-line" /><div className="bp-line" />
            </div>
          </div>
          <div className="bp-writing bp-writing-questions">
            <h3 className="bp-writing-title">Questions to keep close</h3>
            <div className="bp-lines" aria-label="Four blank write-in lines">
              <div className="bp-line" /><div className="bp-line" /><div className="bp-line" /><div className="bp-line" />
            </div>
          </div>
          <span className="bp-footer-label">Design concept · For review</span>
        </div>
      </section>
    </main>
  );
}
