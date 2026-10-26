import React from "react";

export function TogetherPremium() {
  return (
    <main className="together-premium" aria-label="Eternal Life Hospice patient and family guide design concept">
      <style>{`
        @font-face {
          font-family: TogetherFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: TogetherFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: TogetherJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: TogetherJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .together-premium, .together-premium * { box-sizing: border-box; }
        .together-premium {
          --tp-paper: #f4efe5;
          --tp-paper-deep: #e9dfcf;
          --tp-plum: #402841;
          --tp-plum-soft: #624a60;
          --tp-gold: #b59a69;
          width: 100%;
          height: 100%;
          min-height: 100dvh;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          overflow: hidden;
          color: var(--tp-plum);
          background: var(--tp-paper);
          font-family: TogetherJost, sans-serif;
          isolation: isolate;
        }
        .tp-panel {
          min-width: 0;
          height: 100%;
          position: relative;
          overflow: hidden;
        }
        .tp-panel + .tp-panel { border-left: 1px solid rgba(64,40,65,.22); }
        .tp-surface-label {
          position: absolute;
          z-index: 4;
          top: 22px;
          left: 42px;
          margin: 0;
          color: var(--tp-plum-soft);
          font-size: 9px;
          line-height: 1;
          letter-spacing: .17em;
          text-transform: uppercase;
        }
        .tp-cover {
          background: var(--tp-paper);
        }
        .tp-cover-photo {
          position: absolute;
          inset: 0 0 32% 0;
          width: 100%;
          height: 68%;
          display: block;
          object-fit: cover;
          object-position: 51% 45%;
        }
        .tp-photo-wash {
          position: absolute;
          inset: 0 0 31.7% 0;
          background: linear-gradient(180deg, rgba(244,239,229,.13), rgba(244,239,229,0) 28%, rgba(64,40,65,.1));
        }
        .tp-cover-label {
          color: #513b4e;
          top: 24px;
          left: 43px;
          padding: 8px 10px;
          background: rgba(244,239,229,.86);
          backdrop-filter: blur(4px);
        }
        .tp-cover-logo {
          position: absolute;
          z-index: 2;
          top: 67px;
          left: 43px;
          width: 165px;
          height: auto;
          display: block;
          mix-blend-mode: multiply;
        }
        .tp-cover-paper {
          position: absolute;
          z-index: 2;
          inset: auto 0 0;
          height: 35%;
          padding: 35px 43px 28px;
          background:
            radial-gradient(ellipse at 94% 0%, rgba(181,154,105,.14), transparent 42%),
            var(--tp-paper);
        }
        .tp-cover-paper::before {
          content: "";
          position: absolute;
          width: 118px;
          height: 118px;
          right: -59px;
          top: -59px;
          border-radius: 50%;
          background: var(--tp-paper);
        }
        .tp-cover-rule {
          width: 43px;
          height: 2px;
          margin: 1px 0 14px;
          background: var(--tp-gold);
        }
        .tp-cover-title {
          position: relative;
          z-index: 1;
          max-width: 545px;
          margin: 0;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: clamp(38px, 5.6vw, 52px);
          font-weight: 500;
          line-height: .99;
          letter-spacing: -.045em;
        }
        .tp-cover-bottom {
          position: absolute;
          right: 43px;
          bottom: 28px;
          left: 43px;
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 12px;
        }
        .tp-cover-tagline, .tp-cover-site {
          margin: 0;
          font-size: 12px;
          line-height: 1.2;
          letter-spacing: .015em;
        }
        .tp-cover-tagline { color: var(--tp-plum-soft); }
        .tp-cover-site {
          color: var(--tp-plum);
          font-size: 10px;
          letter-spacing: .075em;
        }
        .tp-letter {
          padding: 51px 54px 34px;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(181,154,105,.11), transparent 34%),
            var(--tp-paper);
        }
        .tp-letter .tp-surface-label { left: 54px; }
        .tp-letter-content {
          position: relative;
          height: 100%;
          display: flex;
          flex-direction: column;
          padding-top: 24px;
        }
        .tp-draft {
          align-self: flex-start;
          margin: 0 0 17px;
          padding: 7px 10px 6px;
          border: 1px solid rgba(181,154,105,.75);
          color: #775d37;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .12em;
          font-weight: 500;
        }
        .tp-letter h2 {
          margin: 0 0 18px;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 35px;
          line-height: 1.04;
          letter-spacing: -.035em;
          font-weight: 500;
        }
        .tp-letter-copy {
          color: #554950;
          font-size: 14px;
          line-height: 1.48;
          letter-spacing: .002em;
        }
        .tp-letter-copy p { margin: 0 0 12px; }
        .tp-letter-copy .tp-salutation { margin-bottom: 13px; color: var(--tp-plum); }
        .tp-letter-signoff {
          margin-top: auto;
          padding-top: 4px;
        }
        .tp-with-warmth {
          margin: 0 0 4px;
          color: var(--tp-plum-soft);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 17px;
          font-style: italic;
          line-height: 1.2;
        }
        .tp-name {
          margin: 0;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 22px;
          line-height: 1.1;
          letter-spacing: -.02em;
        }
        .tp-title-lines {
          margin: 6px 0 0;
          color: #786c70;
          font-size: 10px;
          line-height: 1.45;
          letter-spacing: .025em;
        }
        .tp-back {
          padding: 51px 49px 33px;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(181,154,105,.12), transparent 38%),
            var(--tp-paper);
        }
        .tp-back .tp-surface-label { left: 49px; }
        .tp-back-content {
          position: relative;
          height: 100%;
          display: flex;
          flex-direction: column;
          padding-top: 20px;
        }
        .tp-back-heading-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 17px;
        }
        .tp-back h2 {
          margin: 0;
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 40px;
          line-height: .98;
          font-weight: 500;
          letter-spacing: -.045em;
        }
        .tp-orbit {
          flex: 0 0 49px;
          width: 49px;
          height: 49px;
          margin-top: 1px;
          border: 1px solid rgba(181,154,105,.78);
          border-radius: 50%;
          position: relative;
        }
        .tp-orbit::before, .tp-orbit::after {
          content: "";
          position: absolute;
          background: var(--tp-gold);
        }
        .tp-orbit::before { width: 1px; height: 28px; left: 23px; top: 10px; transform: rotate(37deg); }
        .tp-orbit::after { width: 24px; height: 1px; left: 12px; top: 24px; transform: rotate(-27deg); }
        .tp-contact-card {
          position: relative;
          margin: 0 -49px 18px;
          padding: 17px 49px 16px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 13px 18px;
          background: var(--tp-plum);
          color: var(--tp-paper);
        }
        .tp-contact-card::after {
          content: "";
          position: absolute;
          right: 49px;
          bottom: 0;
          width: 40px;
          height: 2px;
          background: var(--tp-gold);
        }
        .tp-contact-item { min-width: 0; }
        .tp-contact-label {
          display: block;
          margin-bottom: 4px;
          color: #d5c4a2;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        .tp-contact-value {
          margin: 0;
          color: var(--tp-paper);
          font-size: 12px;
          line-height: 1.28;
          overflow-wrap: anywhere;
        }
        .tp-contact-address { grid-column: 1 / -1; }
        .tp-back-site {
          margin: -8px 0 18px;
          color: var(--tp-plum-soft);
          font-size: 10px;
          letter-spacing: .075em;
        }
        .tp-writing-section { margin: 0 0 16px; }
        .tp-writing-title {
          display: flex;
          align-items: center;
          gap: 9px;
          margin: 0 0 8px;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 19px;
          line-height: 1.1;
          font-weight: 500;
        }
        .tp-writing-title::after {
          content: "";
          height: 1px;
          flex: 1;
          background: rgba(181,154,105,.65);
        }
        .tp-write-line {
          height: 25px;
          border-bottom: 1px solid rgba(98,74,96,.32);
        }
        .tp-questions { margin-top: 0; }
        .tp-questions .tp-write-line { height: 27px; }
        .tp-review-note {
          position: absolute;
          right: 0;
          bottom: 0;
          margin: 0;
          color: #8c7d75;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .14em;
        }
        @media (max-width: 900px) {
          .together-premium { grid-template-columns: 1fr; height: auto; min-height: 100dvh; overflow: visible; }
          .tp-panel { min-height: 100dvh; }
          .tp-panel + .tp-panel { border-left: 0; border-top: 1px solid rgba(64,40,65,.22); }
          .tp-cover-photo, .tp-photo-wash { bottom: 31%; }
          .tp-cover-paper { height: 35%; }
          .tp-cover-title { font-size: clamp(42px, 10vw, 58px); }
          .tp-letter-copy { font-size: 16px; line-height: 1.55; }
          .tp-letter { padding-right: max(32px, 8vw); padding-left: max(32px, 8vw); }
          .tp-letter .tp-surface-label { left: max(32px, 8vw); }
          .tp-letter-content { min-height: calc(100dvh - 90px); }
          .tp-back { padding-right: max(32px, 7vw); padding-left: max(32px, 7vw); }
          .tp-back .tp-surface-label { left: max(32px, 7vw); }
          .tp-contact-card { margin-right: calc(max(32px, 7vw) * -1); margin-left: calc(max(32px, 7vw) * -1); padding-right: max(32px, 7vw); padding-left: max(32px, 7vw); }
        }
      `}</style>

      <section className="tp-panel tp-cover" aria-label="Front cover">
        <img className="tp-cover-photo" src="/__reviews-mockup/images/elh-patient-guide/premium-together.jpg" alt="An older mother and adult daughter sit close together in the soft light of a home, looking out into a garden." />
        <div className="tp-photo-wash" aria-hidden="true" />
        <p className="tp-surface-label tp-cover-label">Front cover</p>
        <img className="tp-cover-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png" alt="Eternal Life Hospice" />
        <div className="tp-cover-paper">
          <div className="tp-cover-rule" aria-hidden="true" />
          <h1 className="tp-cover-title">Patient &amp; Family<br />Guide</h1>
          <div className="tp-cover-bottom">
            <p className="tp-cover-tagline">Care That Honors Life.</p>
            <p className="tp-cover-site">eternallifehospice.com</p>
          </div>
        </div>
      </section>

      <section className="tp-panel tp-letter" aria-label="Inside front cover, founder welcome draft">
        <p className="tp-surface-label">Inside front cover</p>
        <div className="tp-letter-content">
          <p className="tp-draft">DRAFT FOR ALEKSANDRA’S REVIEW</p>
          <h2>A note from<br />Aleksandra</h2>
          <div className="tp-letter-copy">
            <p className="tp-salutation">Dear family,</p>
            <p>When someone you love needs hospice care, there can be a great deal to take in. You may have questions you have not yet found words for. You do not need to have every answer today.</p>
            <p>At Eternal, we begin by getting to know the person at the center of care—and the family beside them. What brings comfort? What matters most? What would make today feel more like their own?</p>
            <p>My hope is that this guide gives you a place to begin, return to and make your own. Bring us your questions, concerns and the small details that help us understand your loved one.</p>
          </div>
          <div className="tp-letter-signoff">
            <p className="tp-with-warmth">With warmth,</p>
            <p className="tp-name">Aleksandra Dubina</p>
            <p className="tp-title-lines">Founder &amp; CEO<br />Certified Hospice Administrator</p>
          </div>
        </div>
      </section>

      <section className="tp-panel tp-back" aria-label="Inside back cover, contact and notes">
        <p className="tp-surface-label">Inside back cover</p>
        <div className="tp-back-content">
          <div className="tp-back-heading-row">
            <h2>Keep us<br />close</h2>
            <span className="tp-orbit" aria-hidden="true" />
          </div>
          <div className="tp-contact-card">
            <div className="tp-contact-item">
              <span className="tp-contact-label">Main</span>
              <p className="tp-contact-value">805.410.1151</p>
            </div>
            <div className="tp-contact-item">
              <span className="tp-contact-label">Office</span>
              <p className="tp-contact-value">805.953.7273</p>
            </div>
            <div className="tp-contact-item">
              <span className="tp-contact-label">Email</span>
              <p className="tp-contact-value">info@eternallifehospice.com</p>
            </div>
            <div className="tp-contact-item tp-contact-address">
              <span className="tp-contact-label">Visit</span>
              <p className="tp-contact-value">4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</p>
            </div>
          </div>
          <p className="tp-back-site">eternallifehospice.com</p>

          <div className="tp-writing-section">
            <h3 className="tp-writing-title">Your care team</h3>
            <div className="tp-write-line" />
            <div className="tp-write-line" />
          </div>
          <div className="tp-writing-section tp-questions">
            <h3 className="tp-writing-title">Questions to keep close</h3>
            <div className="tp-write-line" />
            <div className="tp-write-line" />
            <div className="tp-write-line" />
            <div className="tp-write-line" />
          </div>
          <p className="tp-review-note">DESIGN CONCEPT · FOR REVIEW</p>
        </div>
      </section>
    </main>
  );
}
