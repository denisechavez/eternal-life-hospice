import React from "react";

export function BotanicalPremium() {
  return (
    <main className="company-guide" aria-label="Eternal Life Hospice guide, four cover surfaces">
      <style>{`
        @font-face {
          font-family: CompanyFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: CompanyFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: CompanyJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: CompanyJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .company-guide, .company-guide * { box-sizing: border-box; }
        .company-guide {
          --cg-plum: #432c47;
          --cg-plum-deep: #35243b;
          --cg-paper: #f5f0e6;
          --cg-paper-shadow: #e9dfd0;
          --cg-gold: #b89b69;
          --cg-ink: #433c42;
          --cg-muted: #796f73;
          width: 100%;
          height: 100%;
          min-height: 0;
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          overflow: hidden;
          color: var(--cg-ink);
          background: var(--cg-paper);
          font-family: CompanyJost, sans-serif;
          isolation: isolate;
        }
        .cg-surface {
          position: relative;
          min-width: 0;
          height: 100%;
          overflow: hidden;
        }
        .cg-surface + .cg-surface { border-left: 1px solid rgba(67,44,71,.24); }
        .cg-label {
          position: absolute;
          z-index: 5;
          top: 25px;
          left: 34px;
          margin: 0;
          color: var(--cg-muted);
          font-size: 9px;
          line-height: 1;
          letter-spacing: .18em;
          font-weight: 500;
          text-transform: uppercase;
        }

        /* Front cover: restrained plum typography over a full-bleed coastal meadow */
        .cg-front {
          background: var(--cg-plum);
          color: var(--cg-paper);
        }
        .cg-front-photo {
          position: absolute;
          z-index: 0;
          inset: auto 0 0;
          width: 100%;
          height: 352px;
          display: block;
          object-fit: cover;
          object-position: center 68%;
        }
        .cg-front .cg-label { color: #d6c9ae; }
        .cg-front-logo {
          position: absolute;
          left: 56px;
          top: 83px;
          width: 188px;
          height: auto;
          max-height: 100px;
          object-fit: contain;
          object-position: left center;
          display: block;
          z-index: 1;
        }
        .cg-title-mark {
          position: absolute;
          z-index: 1;
          left: 58px;
          top: 255px;
          width: 34px;
          height: 2px;
          background: var(--cg-gold);
        }
        .cg-front-title {
          position: absolute;
          z-index: 1;
          left: 54px;
          top: 282px;
          width: 575px;
          margin: 0;
          color: #f6efe3;
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 57px;
          line-height: .98;
          letter-spacing: -.045em;
          font-weight: 500;
        }
        .cg-front-tagline {
          position: absolute;
          z-index: 1;
          left: 58px;
          top: 432px;
          margin: 0;
          color: #d8cdb8;
          font-size: 15px;
          line-height: 1.3;
          letter-spacing: .05em;
        }
        .cg-front-site {
          position: absolute;
          z-index: 1;
          left: 58px;
          bottom: 365px;
          margin: 0;
          color: #e4d8c3;
          font-size: 11px;
          letter-spacing: .12em;
        }
        .cg-front-folio {
          position: absolute;
          z-index: 1;
          right: 58px;
          bottom: 365px;
          color: #c4b189;
          font-size: 9px;
          letter-spacing: .16em;
        }

        /* Inside front: portrait as a warm human counterweight to the letter */
        .cg-welcome {
          background: var(--cg-paper);
        }
        .cg-welcome-portrait {
          position: absolute;
          inset: 0 auto 0 0;
          width: 207px;
          background: var(--cg-plum);
        }
        .cg-welcome-portrait::before {
          content: "";
          position: absolute;
          inset: 0 0 0 auto;
          width: 5px;
          background: var(--cg-gold);
          opacity: .8;
        }
        .cg-founder-image {
          position: absolute;
          left: 21px;
          top: 119px;
          width: 165px;
          height: 251px;
          display: block;
          object-fit: cover;
          object-position: center 30%;
          border: 1px solid rgba(237,222,194,.65);
        }
        .cg-founder-name {
          position: absolute;
          left: 24px;
          top: 394px;
          width: 155px;
          margin: 0;
          color: #f2eadc;
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 20px;
          line-height: 1.12;
          letter-spacing: -.02em;
        }
        .cg-welcome .cg-label {
          left: 235px;
          color: #857a7d;
        }
        .cg-letter-content {
          position: absolute;
          left: 238px;
          right: 34px;
          top: 76px;
          bottom: 35px;
        }
        .cg-letter-title {
          margin: 0 0 13px;
          color: var(--cg-plum);
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 34px;
          line-height: 1.02;
          letter-spacing: -.04em;
          font-weight: 500;
        }
        .cg-draft {
          display: inline-block;
          margin: 0 0 16px;
          padding: 6px 8px 5px;
          border: 1px solid rgba(67,44,71,.34);
          color: var(--cg-plum);
          font-size: 8.5px;
          line-height: 1;
          letter-spacing: .13em;
          font-weight: 500;
        }
        .cg-letter-copy {
          color: #51494e;
          font-size: 14px;
          line-height: 1.46;
          letter-spacing: .002em;
        }
        .cg-letter-copy p { margin: 0 0 10px; }
        .cg-letter-copy .cg-salutation { margin-bottom: 10px; color: var(--cg-plum); }
        .cg-signoff { margin-top: 13px; }
        .cg-signoff p { margin: 0; }
        .cg-founder-signoff {
          margin-top: 5px !important;
          color: var(--cg-plum);
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 20px;
          line-height: 1.1;
        }
        .cg-founder-role {
          color: var(--cg-muted);
          font-size: 10px;
          line-height: 1.45;
        }

        /* Inside back: quiet retrieval hierarchy, no enclosed contact card */
        .cg-inside-back {
          padding: 59px 47px 34px;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(184,155,105,.14), transparent 33%),
            var(--cg-paper);
        }
        .cg-inside-back .cg-label { left: 47px; }
        .cg-back-heading {
          margin: 0 0 26px;
          color: var(--cg-plum);
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 43px;
          line-height: 1;
          letter-spacing: -.045em;
          font-weight: 500;
        }
        .cg-phones {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
          padding: 0 0 17px;
          border-bottom: 1px solid rgba(67,44,71,.24);
        }
        .cg-contact-label {
          display: block;
          margin-bottom: 6px;
          color: #92794f;
          font-size: 9px;
          line-height: 1;
          letter-spacing: .15em;
          font-weight: 500;
          text-transform: uppercase;
        }
        .cg-phone {
          display: block;
          color: var(--cg-plum);
          font-size: 19px;
          line-height: 1.2;
          letter-spacing: .015em;
          white-space: nowrap;
        }
        .cg-detail-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 15px 18px;
          padding: 15px 0 0;
        }
        .cg-detail-grid .cg-contact-label { margin-bottom: 5px; }
        .cg-contact-detail {
          display: block;
          color: #504750;
          font-size: 11px;
          line-height: 1.4;
          overflow-wrap: anywhere;
        }
        .cg-notes {
          margin-top: 25px;
        }
        .cg-note-heading {
          display: flex;
          align-items: baseline;
          gap: 10px;
          margin: 0 0 7px;
          color: var(--cg-plum);
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.1;
          font-weight: 500;
        }
        .cg-note-heading::after {
          content: "";
          flex: 1;
          height: 1px;
          background: rgba(184,155,105,.8);
        }
        .cg-writing-lines {
          display: grid;
        }
        .cg-writing-line {
          height: 27px;
          border-bottom: 1px solid rgba(67,44,71,.28);
        }
        .cg-question-notes { margin-top: 19px; }
        .cg-review-mark {
          position: absolute;
          right: 46px;
          bottom: 20px;
          color: #877b80;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .14em;
          text-transform: uppercase;
        }

        /* Outside back: paired full-bleed landscape band beneath the colophon */
        .cg-outside-back {
          background: var(--cg-paper);
        }
        .cg-outside-back .cg-label { left: 35px; }
        .cg-outside-content {
          position: absolute;
          z-index: 2;
          inset: 0 0 auto;
          width: 100%;
          height: 535px;
          padding: 76px 42px 36px;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(184,155,105,.12), transparent 35%),
            var(--cg-paper);
        }
        .cg-outside-photo {
          position: absolute;
          inset: auto 0 0;
          width: 100%;
          height: 345px;
          display: block;
          object-fit: cover;
          object-position: center 76%;
        }
        .cg-outside-logo {
          display: block;
          width: 178px;
          height: auto;
          max-height: 95px;
          object-fit: contain;
          object-position: left center;
          margin-bottom: 32px;
          mix-blend-mode: multiply;
        }
        .cg-outside-rule {
          width: 31px;
          height: 2px;
          margin-bottom: 24px;
          background: var(--cg-gold);
        }
        .cg-colophon {
          margin: 0;
          color: var(--cg-plum);
          font-family: CompanyFraunces, Georgia, serif;
          font-size: 23px;
          line-height: 1.15;
          font-weight: 500;
        }
        .cg-outside-details {
          position: relative;
          left: auto;
          right: auto;
          bottom: auto;
          margin-top: 35px;
          color: #574e55;
          font-size: 11px;
          line-height: 1.55;
        }
        .cg-outside-details p { margin: 0 0 9px; }
        .cg-outside-website {
          margin-top: 16px !important;
          color: var(--cg-plum);
          font-size: 10px;
          letter-spacing: .09em;
        }
        @media screen and (max-width: 1200px) {
          .cg-front-logo { left: 8%; width: 28%; }
          .cg-front-title { left: 8%; font-size: clamp(35px, 2.1vw, 57px); }
          .cg-title-mark, .cg-front-tagline, .cg-front-site { left: 8%; }
          .cg-welcome-portrait { width: 30%; }
          .cg-founder-image { left: 10%; width: 80%; }
          .cg-letter-content { left: 34%; right: 5%; }
          .cg-welcome .cg-label { left: 34%; }
          .cg-letter-copy { font-size: clamp(11px, .85vw, 14px); }
        }
      `}</style>

      <section className="cg-surface cg-front" aria-label="Front cover">
        <img className="cg-front-photo" src="/__reviews-mockup/images/elh-patient-guide/botanical-coastal-meadow.jpg" alt="" />
        <p className="cg-label">Front cover</p>
        <img className="cg-front-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-cream.png" alt="Eternal Life Hospice" />
        <span className="cg-title-mark" aria-hidden="true" />
        <h1 className="cg-front-title">Patient &amp; Family<br />Guide</h1>
        <p className="cg-front-tagline">Care That Honors Life.</p>
        <p className="cg-front-site">eternallifehospice.com</p>
        <span className="cg-front-folio" aria-hidden="true">ELH</span>
      </section>

      <section className="cg-surface cg-welcome" aria-label="Inside front cover, founder letter draft">
        <div className="cg-welcome-portrait">
          <img className="cg-founder-image" src="/__reviews-mockup/images/elh-patient-guide/aleksandra-founder.jpg" alt="Aleksandra Dubina" />
          <p className="cg-founder-name">Aleksandra Dubina</p>
        </div>
        <p className="cg-label">Inside front cover</p>
        <div className="cg-letter-content">
          <h2 className="cg-letter-title">A note from<br />Aleksandra</h2>
          <p className="cg-draft">DRAFT FOR ALEKSANDRA’S REVIEW</p>
          <div className="cg-letter-copy">
            <p className="cg-salutation">Dear family,</p>
            <p>When someone you love is receiving hospice care, there can be a great deal to take in. This guide is here to help you understand your loved one’s care, know who to call and feel more prepared for what may come next.</p>
            <p>Inside, you will find information about your hospice team, comfort and symptom management, family support, safety, privacy and patient rights. You do not need to read it all at once. Begin with what feels most useful today and return to the other sections when you are ready.</p>
            <p>No guide can replace a conversation. Please share your questions, concerns and the details that make your loved one who they are. Your voice helps us understand what matters most to your family. Thank you for welcoming Eternal into your loved one’s care.</p>
            <div className="cg-signoff">
              <p>With warmth,</p>
              <p className="cg-founder-signoff">Aleksandra Dubina</p>
              <p className="cg-founder-role">Founder &amp; CEO<br />Certified Hospice Administrator</p>
            </div>
          </div>
        </div>
      </section>

      <section className="cg-surface cg-inside-back" aria-label="Inside back cover, contacts and family notes">
        <p className="cg-label">Inside back cover</p>
        <h2 className="cg-back-heading">Keep us close</h2>
        <div className="cg-phones">
          <div>
            <span className="cg-contact-label">Main</span>
            <span className="cg-phone">805.410.1151</span>
          </div>
          <div>
            <span className="cg-contact-label">Office</span>
            <span className="cg-phone">805.953.7273</span>
          </div>
        </div>
        <div className="cg-detail-grid">
          <div>
            <span className="cg-contact-label">Email</span>
            <span className="cg-contact-detail">info@eternallifehospice.com</span>
          </div>
          <div>
            <span className="cg-contact-label">Address</span>
            <span className="cg-contact-detail">4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</span>
          </div>
        </div>
        <div className="cg-notes">
          <h3 className="cg-note-heading">Your care team</h3>
          <div className="cg-writing-lines" aria-label="Five blank write-in lines">
            <div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" />
          </div>
        </div>
        <div className="cg-notes cg-question-notes">
          <h3 className="cg-note-heading">Questions to keep close</h3>
          <div className="cg-writing-lines" aria-label="Seven blank write-in lines">
            <div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" /><div className="cg-writing-line" />
          </div>
        </div>
        <span className="cg-review-mark">Design concept · For review</span>
      </section>

      <section className="cg-surface cg-outside-back" aria-label="Outside back cover">
        <p className="cg-label">Outside back cover</p>
        <div className="cg-outside-content">
          <img className="cg-outside-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png" alt="Eternal Life Hospice" />
          <div className="cg-outside-rule" aria-hidden="true" />
          <p className="cg-colophon">eternallifehospice.com</p>
          <div className="cg-outside-details">
            <p>805.410.1151<br />805.953.7273</p>
            <p>info@eternallifehospice.com</p>
            <p>4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</p>
            <p className="cg-outside-website">Care That Honors Life.</p>
          </div>
        </div>
        <img className="cg-outside-photo" src="/__reviews-mockup/images/elh-patient-guide/nature-olive-ocean.jpg" alt="Sunlit olive branches against a softly blue ocean." />
      </section>
    </main>
  );
}
