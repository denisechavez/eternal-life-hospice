import React from "react";

export function AmethystInside() {
  return (
    <main className="amethyst-insides" aria-label="Eternal Life Hospice inside cover comparison">
      <style>{`
        @font-face {
          font-family: ELHInsideFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: ELHInsideFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: ELHInsideJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: ELHInsideJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .amethyst-insides, .amethyst-insides * { box-sizing: border-box; }
        .amethyst-insides {
          --inside-paper: #f5f0e6;
          --inside-plum: #3d2340;
          --inside-muted: #684d67;
          --inside-gold: #b69a65;
          width: 100%;
          height: 100%;
          min-height: 100dvh;
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          overflow: hidden;
          background: var(--inside-paper);
          color: var(--inside-plum);
          font-family: ELHInsideJost, sans-serif;
          isolation: isolate;
        }
        .amethyst-inside-panel {
          position: relative;
          min-width: 0;
          height: 100dvh;
          max-height: 100dvh;
          overflow: hidden;
          padding: 49px 66px 34px;
          display: flex;
          flex-direction: column;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(182,154,101,.09), transparent 34%),
            var(--inside-paper);
        }
        .amethyst-inside-panel + .amethyst-inside-panel {
          border-left: 1px solid rgba(61,35,64,.24);
          box-shadow: inset 1px 0 0 rgba(255,255,255,.65);
        }
        .amethyst-inside-topline {
          height: 2px;
          width: 100%;
          position: absolute;
          left: 0;
          top: 0;
          background: var(--inside-gold);
          opacity: .85;
        }
        .amethyst-inside-label {
          margin: 0 0 28px;
          color: var(--inside-muted);
          font-size: 11px;
          line-height: 1.2;
          font-weight: 500;
          letter-spacing: .16em;
        }
        .amethyst-inside-logo {
          display: block;
          width: 124px;
          height: 48px;
          object-fit: contain;
          object-position: left center;
          margin: 0 0 18px;
          mix-blend-mode: multiply;
        }
        .amethyst-inside-title {
          margin: 0 0 17px;
          font-family: ELHInsideFraunces, Georgia, serif;
          color: var(--inside-plum);
          font-size: 39px;
          line-height: 1.04;
          font-weight: 500;
          letter-spacing: -.035em;
        }
        .amethyst-inside-copy {
          max-width: 490px;
          margin: 0;
          color: #51434f;
          font-size: 15px;
          line-height: 1.58;
          letter-spacing: .005em;
        }
        .amethyst-inside-copy + .amethyst-inside-copy {
          margin-top: 11px;
        }
        .amethyst-own-heading {
          margin: 22px 0 8px;
          color: var(--inside-plum);
          font-family: ELHInsideFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.15;
          font-weight: 500;
          letter-spacing: -.02em;
        }
        .amethyst-write-field {
          min-height: 62px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding-top: 8px;
        }
        .amethyst-write-label {
          color: #594b58;
          font-size: 13px;
          line-height: 1.25;
          letter-spacing: .01em;
        }
        .amethyst-write-rule {
          display: block;
          width: 100%;
          height: 1px;
          background: rgba(61,35,64,.43);
        }
        .amethyst-inside-closing {
          margin: auto 0 14px;
          padding-top: 14px;
          color: var(--inside-muted);
          font-family: ELHInsideFraunces, Georgia, serif;
          font-size: 19px;
          line-height: 1.2;
          font-style: italic;
          letter-spacing: .005em;
        }
        .amethyst-inside-footer {
          flex: 0 0 auto;
          padding-top: 11px;
          border-top: 1px solid rgba(182,154,101,.7);
          color: #766b70;
          font-size: 9px;
          line-height: 1.2;
          font-weight: 500;
          letter-spacing: .13em;
        }
        .amethyst-contact-content {
          display: flex;
          flex-direction: column;
          min-height: 0;
          flex: 1;
        }
        .amethyst-contact-intro {
          position: relative;
          margin-bottom: 25px;
        }
        .amethyst-contact-intro::after {
          content: "";
          position: absolute;
          width: 78px;
          height: 78px;
          right: 0;
          top: 7px;
          border-radius: 50%;
          background: url("/__reviews-mockup/images/elh-patient-guide/amethyst.png") center / cover no-repeat;
          opacity: .19;
          mix-blend-mode: multiply;
          pointer-events: none;
        }
        .amethyst-contact-intro .amethyst-inside-label { margin-bottom: 29px; }
        .amethyst-contact-intro .amethyst-inside-title {
          margin-bottom: 0;
          font-size: 39px;
        }
        .amethyst-contact-stack {
          display: grid;
          grid-template-columns: 1fr 1fr;
          column-gap: 20px;
          row-gap: 15px;
          padding: 19px 0 18px;
          border-top: 1px solid rgba(182,154,101,.85);
          border-bottom: 1px solid rgba(182,154,101,.85);
        }
        .amethyst-contact-item {
          min-width: 0;
        }
        .amethyst-contact-item--wide {
          grid-column: 1 / -1;
        }
        .amethyst-contact-label {
          display: block;
          margin-bottom: 3px;
          color: var(--inside-muted);
          font-size: 10px;
          line-height: 1.2;
          font-weight: 500;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        .amethyst-contact-value {
          display: block;
          color: var(--inside-plum);
          font-size: 15px;
          line-height: 1.35;
          letter-spacing: .005em;
          overflow-wrap: anywhere;
        }
        .amethyst-contact-value--phone {
          font-size: 20px;
          line-height: 1.2;
          font-weight: 500;
          letter-spacing: .01em;
        }
        .amethyst-address-line {
          display: block;
        }
        .amethyst-notes-heading {
          margin: 24px 0 10px;
          color: var(--inside-plum);
          font-family: ELHInsideFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.18;
          font-weight: 500;
          letter-spacing: -.02em;
        }
        .amethyst-notes-rules {
          display: flex;
          flex: 1;
          min-height: 170px;
          flex-direction: column;
          justify-content: space-between;
          padding: 2px 0 10px;
        }
        .amethyst-notes-rules span {
          display: block;
          height: 1px;
          width: 100%;
          background: rgba(61,35,64,.31);
        }
        @media (max-width: 900px) {
          .amethyst-inside-panel { padding-left: 5.5vw; padding-right: 5.5vw; }
          .amethyst-inside-title, .amethyst-contact-intro .amethyst-inside-title { font-size: clamp(30px, 5.75vw, 39px); }
          .amethyst-inside-copy { font-size: clamp(13px, 2.2vw, 15px); }
          .amethyst-contact-value { font-size: clamp(12px, 2.2vw, 15px); }
          .amethyst-contact-value--phone { font-size: clamp(16px, 2.9vw, 20px); }
        }
        @media (max-height: 760px) {
          .amethyst-inside-panel { padding-top: 34px; padding-bottom: 24px; }
          .amethyst-inside-label { margin-bottom: 19px; }
          .amethyst-inside-logo { height: 39px; margin-bottom: 12px; }
          .amethyst-inside-title { font-size: 34px; margin-bottom: 12px; }
          .amethyst-inside-copy { font-size: 14px; line-height: 1.45; }
          .amethyst-own-heading { margin-top: 15px; }
          .amethyst-write-field { min-height: 52px; }
          .amethyst-contact-intro { margin-bottom: 18px; }
          .amethyst-contact-intro .amethyst-inside-label { margin-bottom: 19px; }
          .amethyst-contact-stack { row-gap: 10px; padding: 13px 0; }
          .amethyst-notes-heading { margin-top: 17px; }
          .amethyst-notes-rules { min-height: 130px; }
        }
      `}</style>

      <section className="amethyst-inside-panel amethyst-welcome-panel" aria-label="Inside front cover">
        <span className="amethyst-inside-topline" aria-hidden="true" />
        <p className="amethyst-inside-label">INSIDE FRONT COVER</p>
        <img
          className="amethyst-inside-logo"
          src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
          alt="Eternal Life Hospice"
        />
        <h1 className="amethyst-inside-title">Welcome to Eternal</h1>
        <p className="amethyst-inside-copy">
          This guide is a place to keep information, questions and notes as you and your family receive hospice care.
        </p>
        <p className="amethyst-inside-copy">
          You do not need to take everything in at once. Keep it nearby and bring your questions to your care team.
        </p>
        <h2 className="amethyst-own-heading">Make this guide your own</h2>
        <div className="amethyst-write-field">
          <span className="amethyst-write-label">Patient name</span>
          <span className="amethyst-write-rule" aria-hidden="true" />
        </div>
        <div className="amethyst-write-field">
          <span className="amethyst-write-label">Preferred name</span>
          <span className="amethyst-write-rule" aria-hidden="true" />
        </div>
        <div className="amethyst-write-field">
          <span className="amethyst-write-label">A person to contact</span>
          <span className="amethyst-write-rule" aria-hidden="true" />
        </div>
        <p className="amethyst-inside-closing">Care That Honors Life.</p>
        <footer className="amethyst-inside-footer">DRAFT COPY · FOR REVIEW</footer>
      </section>

      <section className="amethyst-inside-panel amethyst-contacts-panel" aria-label="Inside back cover">
        <span className="amethyst-inside-topline" aria-hidden="true" />
        <div className="amethyst-contact-content">
          <div className="amethyst-contact-intro">
            <p className="amethyst-inside-label">INSIDE BACK COVER</p>
            <h2 className="amethyst-inside-title">Keep us close</h2>
          </div>
          <div className="amethyst-contact-stack">
            <div className="amethyst-contact-item">
              <span className="amethyst-contact-label">Main</span>
              <span className="amethyst-contact-value amethyst-contact-value--phone">805.410.1151</span>
            </div>
            <div className="amethyst-contact-item">
              <span className="amethyst-contact-label">Office</span>
              <span className="amethyst-contact-value amethyst-contact-value--phone">805.953.7273</span>
            </div>
            <div className="amethyst-contact-item amethyst-contact-item--wide">
              <span className="amethyst-contact-value">info@eternallifehospice.com</span>
            </div>
            <div className="amethyst-contact-item amethyst-contact-item--wide">
              <span className="amethyst-contact-value">
                <span className="amethyst-address-line">4165 E Thousand Oaks Blvd, Ste 325B</span>
                <span className="amethyst-address-line">Westlake Village, CA 91362</span>
              </span>
            </div>
            <div className="amethyst-contact-item amethyst-contact-item--wide">
              <span className="amethyst-contact-value">eternallifehospice.com</span>
            </div>
          </div>
          <h2 className="amethyst-notes-heading">Questions for your care team</h2>
          <div className="amethyst-notes-rules" aria-label="Blank writing lines for notes">
            <span /><span /><span /><span /><span /><span />
          </div>
        </div>
        <footer className="amethyst-inside-footer">DRAFT COPY · FOR REVIEW</footer>
      </section>
    </main>
  );
}
