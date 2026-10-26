import React from "react";

export function GardenPremium() {
  return (
    <main className="garden-premium" aria-label="Eternal Life Hospice patient and family guide, front cover, inside covers and outside back cover">
      <style>{`
        @font-face {
          font-family: GardenFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: GardenFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: GardenJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: GardenJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .garden-premium, .garden-premium * { box-sizing: border-box; }
        .garden-premium {
          --gp-plum: #442b43;
          --gp-ink: #443c3c;
          --gp-paper: #f5efe4;
          --gp-parchment: #eee4d3;
          --gp-gold: #b99c66;
          --gp-muted: #806f68;
          width: 100%;
          height: 100%;
          min-height: 100dvh;
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          overflow: hidden;
          background: var(--gp-paper);
          color: var(--gp-ink);
          font-family: GardenJost, sans-serif;
          isolation: isolate;
        }
        .gp-panel {
          height: 100%;
          min-width: 0;
          position: relative;
          overflow: hidden;
        }
        .gp-panel + .gp-panel { border-left: 1px solid rgba(185,156,102,.82); }
        .gp-label {
          position: absolute;
          z-index: 5;
          top: 2.1%;
          left: 7.2%;
          margin: 0;
          font-size: clamp(8px, 1.26vw, 10px);
          line-height: 1;
          font-weight: 500;
          letter-spacing: .18em;
          text-transform: uppercase;
        }
        .gp-cover {
          background: var(--gp-plum);
          color: var(--gp-paper);
        }
        .gp-cover:before {
          content: "";
          position: absolute;
          inset: 0;
          background:
            linear-gradient(180deg, rgba(52,33,50,.97) 0%, rgba(61,39,57,.94) 35%, rgba(55,37,51,.1) 65%, rgba(50,34,47,.12) 100%),
            url("/__reviews-mockup/images/elh-patient-guide/premium-garden.jpg") center 54% / cover;
        }
        .gp-cover:after {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background: linear-gradient(180deg, transparent 62%, rgba(39,26,38,.44) 100%);
          box-shadow: inset 0 0 0 13px rgba(185,156,102,.18);
        }
        .gp-cover .gp-label { color: rgba(247,239,224,.73); }
        .gp-cover-inner {
          position: absolute;
          z-index: 2;
          inset: 8.4% 8.2% 7.2%;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
        }
        .gp-cover-logo {
          display: block;
          width: 45%;
          height: auto;
          max-height: 10%;
          object-fit: contain;
          object-position: left center;
          margin-bottom: 9.8%;
          filter: brightness(0) invert(1);
          opacity: .96;
        }
        .gp-cover-title {
          margin: 0;
          max-width: 100%;
          color: #fbf4e9;
          font: 500 clamp(35px, 6.5vw, 48px)/.99 GardenFraunces, Georgia, serif;
          letter-spacing: -.045em;
          text-wrap: balance;
        }
        .gp-cover-rule {
          width: 20%;
          height: 1px;
          margin: 7.5% 0 4.6%;
          background: var(--gp-gold);
        }
        .gp-cover-tagline {
          margin: 0;
          font: italic 400 clamp(16px, 2.85vw, 21px)/1.25 GardenFraunces, Georgia, serif;
          color: #f2e8d8;
        }
        .gp-cover-bottom {
          position: absolute;
          z-index: 2;
          left: 8.2%;
          right: 8.2%;
          bottom: 5.1%;
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          color: #fff8eb;
          font-size: clamp(9px, 1.55vw, 12px);
          letter-spacing: .12em;
        }
        .gp-cover-bottom:before {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          top: -11px;
          height: 1px;
          background: rgba(229,208,168,.72);
        }
        .gp-cover-bottom span:last-child { color: #e5d0a8; font-size: 10px; }

        .gp-letter {
          background:
            radial-gradient(ellipse at 94% 2%, rgba(185,156,102,.12), transparent 31%),
            var(--gp-paper);
        }
        .gp-letter:after, .gp-notes:after {
          content: "";
          pointer-events: none;
          position: absolute;
          inset: 0;
          opacity: .16;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.13'/%3E%3C/svg%3E");
        }
        .gp-letter .gp-label { color: var(--gp-muted); }
        .gp-letter-content {
          position: absolute;
          z-index: 2;
          inset: 8.4% 8.2% 6.3%;
          display: flex;
          flex-direction: column;
        }
        .gp-overline {
          margin: 0 0 2.8%;
          color: #8b7354;
          text-transform: uppercase;
          letter-spacing: .2em;
          font-size: clamp(8px, 1.3vw, 10px);
          font-weight: 500;
        }
        .gp-letter h2, .gp-notes h2 {
          margin: 0;
          color: var(--gp-plum);
          font: 500 clamp(27px, 5.05vw, 37px)/1.04 GardenFraunces, Georgia, serif;
          letter-spacing: -.035em;
        }
        .gp-letter-title-rule {
          width: 18%;
          height: 2px;
          background: var(--gp-gold);
          margin: 4.4% 0 4.4%;
        }
        .gp-letter-intro {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 14px;
        }
        .gp-letter-intro-copy {
          min-width: 0;
          flex: 1;
        }
        .gp-founder-photo {
          display: block;
          flex: 0 0 29%;
          width: 29%;
          aspect-ratio: .78;
          object-fit: cover;
          object-position: center 28%;
          border: 1px solid rgba(185,156,102,.8);
          padding: 4px;
          background: #e9dfd0;
        }
        .gp-letter-copy {
          display: flex;
          flex-direction: column;
          gap: 10px;
          color: #504748;
          font-size: clamp(11px, 2vw, 14px);
          line-height: 1.5;
          letter-spacing: .003em;
        }
        .gp-letter-copy p { margin: 0; }
        .gp-letter-copy .gp-salutation { color: var(--gp-plum); font-weight: 500; }
        .gp-signoff {
          margin-top: auto;
          padding-top: 3.2%;
        }
        .gp-signoff p { margin: 0; }
        .gp-with-warmth {
          color: var(--gp-muted);
          font-size: clamp(10px, 1.7vw, 12px);
          margin-bottom: 1.3% !important;
        }
        .gp-name {
          color: var(--gp-plum);
          font: 500 clamp(17px, 3vw, 22px)/1.05 GardenFraunces, Georgia, serif;
        }
        .gp-role {
          color: #71645e;
          font-size: clamp(9px, 1.5vw, 11px);
          line-height: 1.38;
        }
        .gp-draft {
          position: absolute;
          z-index: 3;
          left: 8.2%;
          right: 8.2%;
          bottom: 2.1%;
          padding-top: 1.6%;
          border-top: 1px solid rgba(185,156,102,.55);
          color: #806c4c;
          font-size: clamp(7px, 1.2vw, 9px);
          letter-spacing: .17em;
          font-weight: 500;
          text-align: center;
        }

        .gp-notes {
          background:
            linear-gradient(160deg, rgba(185,156,102,.1), transparent 43%),
            #f0e7d8;
        }
        .gp-notes .gp-label { color: #796a5b; }
        .gp-notes-content {
          position: absolute;
          z-index: 2;
          inset: 8.4% 8.2% 5.5%;
          display: flex;
          flex-direction: column;
        }
        .gp-notes h2 { margin-bottom: 5.2%; }
        .gp-contact-card {
          background: var(--gp-plum);
          color: #f6efe3;
          padding: 5.7% 6.4% 5.5%;
          position: relative;
          box-shadow: 0 8px 18px rgba(65,42,58,.1);
        }
        .gp-contact-card:after {
          content: "";
          position: absolute;
          top: 0;
          right: 0;
          width: 18%;
          height: 1px;
          background: var(--gp-gold);
        }
        .gp-contact-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 3.5%;
          border-bottom: 1px solid rgba(229,208,168,.32);
          margin-bottom: 3.5%;
        }
        .gp-contact-head span:first-child {
          text-transform: uppercase;
          letter-spacing: .18em;
          color: #d8c296;
          font-size: clamp(8px, 1.35vw, 10px);
        }
        .gp-contact-head span:last-child {
          color: rgba(247,239,224,.58);
          font-size: 9px;
          letter-spacing: .08em;
        }
        .gp-phone-row {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 7px;
          margin-bottom: 2.2%;
          font-size: clamp(9px, 1.55vw, 11px);
        }
        .gp-phone-row strong {
          color: #fff7e9;
          font: 500 clamp(15px, 2.65vw, 19px)/1.1 GardenFraunces, Georgia, serif;
          letter-spacing: .015em;
          white-space: nowrap;
        }
        .gp-email {
          margin: 4% 0 3.8%;
          font-size: clamp(9px, 1.52vw, 11px);
          letter-spacing: .025em;
          color: #f2e8d8;
        }
        .gp-address {
          margin: 0;
          padding-top: 3.4%;
          border-top: 1px solid rgba(229,208,168,.32);
          color: rgba(247,239,224,.86);
          font-size: clamp(9px, 1.5vw, 11px);
          line-height: 1.45;
        }
        .gp-address em {
          display: block;
          margin-top: 2.3%;
          color: #d8c296;
          font-style: normal;
          letter-spacing: .045em;
        }
        .gp-team {
          margin-top: 6.4%;
          padding-bottom: 4.8%;
          border-bottom: 1px solid rgba(117,94,78,.35);
        }
        .gp-section-title {
          margin: 0;
          color: var(--gp-plum);
          font: 500 clamp(18px, 3.25vw, 24px)/1.1 GardenFraunces, Georgia, serif;
        }
        .gp-team-line {
          margin-top: 4.7%;
          height: 21px;
          border-bottom: 1px solid rgba(117,94,78,.5);
        }
        .gp-questions {
          margin-top: 5.6%;
          flex: 1;
          display: flex;
          flex-direction: column;
        }
        .gp-question-lines {
          flex: 1;
          margin-top: 2.5%;
          min-height: 76px;
          background: repeating-linear-gradient(
            to bottom,
            transparent 0,
            transparent 22px,
            rgba(117,94,78,.45) 22px,
            rgba(117,94,78,.45) 23px
          );
        }
        .gp-review {
          position: absolute;
          z-index: 3;
          bottom: 1.5%;
          left: 8.2%;
          color: #806c4c;
          font-size: clamp(7px, 1.1vw, 8px);
          letter-spacing: .16em;
          text-transform: uppercase;
        }
        .gp-back {
          background: var(--gp-plum);
          color: var(--gp-paper);
        }
        .gp-back .gp-label { color: #e1cfb4; }
        .gp-back-image {
          position: absolute;
          inset: 0 0 auto;
          height: 39%;
          width: 100%;
          object-fit: cover;
          object-position: center 45%;
        }
        .gp-back-image-shade {
          position: absolute;
          inset: 0 0 auto;
          height: 39%;
          background: linear-gradient(180deg, rgba(35,24,34,.45), transparent 45%, rgba(68,43,67,.18));
          border-bottom: 1px solid var(--gp-gold);
        }
        .gp-back-content {
          position: absolute;
          inset: 44% 8.2% 8.2%;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
        }
        .gp-back-logo { width: 145px; height: auto; display: block; }
        .gp-back-tagline {
          font: italic 400 27px/1.25 GardenFraunces, Georgia, serif;
          margin: 27px 0 26px;
          color: #f7efdf;
        }
        .gp-back-contacts {
          width: 100%;
          border-top: 1px solid rgba(225,207,180,.5);
          padding-top: 20px;
          font-size: 14px;
          line-height: 1.65;
        }
        .gp-back-contacts p { margin: 0 0 9px; }
        .gp-back-contacts strong { font-size: 21px; font-weight: 500; }
        .gp-back-contacts small { font-size: 11px; letter-spacing: .1em; color: #e1cfb4; margin-left: 12px; }
        .gp-back-site {
          margin: auto 0 0;
          padding-top: 18px;
          font-size: 13px;
          letter-spacing: .09em;
          color: #e1cfb4;
        }
        .gp-back .gp-review { color: #e1cfb4; }
        @media (max-width: 700px) {
          .garden-premium { min-height: 100dvh; }
          .gp-letter-copy { line-height: 1.42; }
        }
      `}</style>

      <section className="gp-panel gp-cover" aria-label="Front cover">
        <p className="gp-label">Front cover</p>
        <div className="gp-cover-inner">
          <img
            className="gp-cover-logo"
            src="/__reviews-mockup/images/elh-patient-guide/logo-cream.png"
            alt="Eternal Life Hospice"
          />
          <h1 className="gp-cover-title">Patient &amp;<br />Family Guide</h1>
          <span className="gp-cover-rule" aria-hidden="true" />
          <p className="gp-cover-tagline">Care That Honors Life.</p>
        </div>
        <div className="gp-cover-bottom">
          <span>eternallifehospice.com</span>
          <span>VENTURA · LOS ANGELES</span>
        </div>
      </section>

      <section className="gp-panel gp-letter" aria-label="Inside front cover, founder welcome draft">
        <p className="gp-label">Inside front cover</p>
        <div className="gp-letter-content">
          <p className="gp-overline">A personal welcome</p>
          <div className="gp-letter-intro">
            <div className="gp-letter-intro-copy">
              <h2>A note from<br />Aleksandra</h2>
            </div>
            <img
              className="gp-founder-photo"
              src="/__reviews-mockup/images/elh-patient-guide/aleksandra-founder.jpg"
              alt="Portrait of Aleksandra Dubina"
            />
          </div>
          <span className="gp-letter-title-rule" aria-hidden="true" />
          <div className="gp-letter-copy">
            <p className="gp-salutation">Dear family,</p>
            <p>When someone you love needs hospice care, there can be a great deal to take in. You may have questions you have not yet found words for. You do not need to have every answer today.</p>
            <p>At Eternal, we begin by getting to know the person at the center of care—and the family beside them. What brings comfort? What matters most? What would make today feel more like their own?</p>
            <p>My hope is that this guide gives you a place to begin, return to and make your own. Bring us your questions, concerns and the small details that help us understand your loved one.</p>
          </div>
          <div className="gp-signoff">
            <p className="gp-with-warmth">With warmth,</p>
            <p className="gp-name">Aleksandra Dubina</p>
            <p className="gp-role">Founder &amp; CEO<br />Certified Hospice Administrator</p>
          </div>
        </div>
        <div className="gp-draft">DRAFT FOR ALEKSANDRA’S REVIEW</div>
      </section>

      <section className="gp-panel gp-notes" aria-label="Inside back cover, contacts and family notes">
        <p className="gp-label">Inside back cover</p>
        <div className="gp-notes-content">
          <p className="gp-overline">A place to return</p>
          <h2>Keep us close</h2>
          <div className="gp-contact-card">
            <div className="gp-contact-head">
              <span>Eternal Life Hospice</span>
              <span>CONTACT</span>
            </div>
            <div className="gp-phone-row"><span>Main</span><strong>805.410.1151</strong></div>
            <div className="gp-phone-row"><span>Office</span><strong>805.953.7273</strong></div>
            <p className="gp-email">info@eternallifehospice.com</p>
            <p className="gp-address">
              4165 E Thousand Oaks Blvd, Ste 325B
              <em>Westlake Village, CA 91362</em>
            </p>
          </div>
          <div className="gp-team">
            <h3 className="gp-section-title">Your care team</h3>
            <div className="gp-team-line" aria-hidden="true" />
          </div>
          <div className="gp-questions">
            <h3 className="gp-section-title">Questions to keep close</h3>
            <div className="gp-question-lines" aria-hidden="true" />
          </div>
        </div>
        <div className="gp-review">eternallifehospice.com <span aria-hidden="true"> · </span> DESIGN CONCEPT · FOR REVIEW</div>
      </section>

      <section className="gp-panel gp-back" aria-label="Outside back cover">
        <img
          className="gp-back-image"
          src="/__reviews-mockup/images/elh-patient-guide/seated-coastal-view.jpg"
          alt="A seated-height view across the ocean toward coastal hills"
        />
        <div className="gp-back-image-shade" aria-hidden="true" />
        <p className="gp-label">Outside back cover</p>
        <div className="gp-back-content">
          <img
            className="gp-back-logo"
            src="/__reviews-mockup/images/elh-patient-guide/logo-cream.png"
            alt="Eternal Life Hospice"
          />
          <p className="gp-back-tagline">Care That Honors Life.</p>
          <div className="gp-back-contacts">
            <p><strong>805.410.1151</strong><small>MAIN</small></p>
            <p>805.953.7273<small>OFFICE</small></p>
            <p>info@eternallifehospice.com</p>
            <p>4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</p>
          </div>
          <p className="gp-back-site">eternallifehospice.com</p>
        </div>
        <div className="gp-review">DESIGN CONCEPT · FOR REVIEW</div>
      </section>
    </main>
  );
}
