import React from "react";

export function TogetherPremium() {
  return (
    <main className="together-premium" aria-label="Held Together patient and family guide, four cover surfaces">
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
          --tp-paper-deep: #e8ddcc;
          --tp-plum: #402841;
          --tp-plum-soft: #624a60;
          --tp-gold: #b59a69;
          width: 100%;
          height: 100%;
          min-height: 100dvh;
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          overflow: hidden;
          color: var(--tp-plum);
          background: var(--tp-paper);
          font-family: TogetherJost, sans-serif;
          isolation: isolate;
        }
        .tp-panel {
          position: relative;
          height: 100%;
          min-width: 0;
          overflow: hidden;
        }
        .tp-panel + .tp-panel { border-left: 1px solid rgba(64,40,65,.24); }
        .tp-surface-label {
          position: absolute;
          z-index: 6;
          top: 22px;
          left: 35px;
          margin: 0;
          color: var(--tp-plum-soft);
          font-size: 9px;
          line-height: 1;
          letter-spacing: .17em;
          text-transform: uppercase;
        }
        .tp-cover {
          display: flex;
          align-items: stretch;
          background: #ece3d6;
        }
        .tp-cover-photo {
          position: absolute;
          inset: 0 0 0 auto;
          width: 44%;
          height: 100%;
          display: block;
          object-fit: cover;
          object-position: 48% center;
        }
        .tp-cover-wash {
          position: absolute;
          inset: 0 44% 0 0;
          background: var(--tp-paper);
        }
        .tp-cover-top {
          position: absolute;
          z-index: 2;
          top: 0;
          left: 0;
          width: 56%;
          height: 245px;
          padding: 51px 37px 20px;
          background: transparent;
        }
        .tp-cover-label {
          top: 24px;
          left: 37px;
          color: #725e4d;
        }
        .tp-cover-logo {
          display: block;
          width: 165px;
          height: auto;
          mix-blend-mode: multiply;
        }
        .tp-title-plaque {
          position: absolute;
          z-index: 3;
          left: 0;
          bottom: 0;
          width: 56%;
          height: 72%;
          padding: 20px 37px 75px;
          background: transparent;
        }
        .tp-title-rule {
          width: 43px;
          height: 2px;
          margin: 0 0 23px;
          background: var(--tp-gold);
        }
        .tp-cover-title {
          margin: 0;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 48px;
          font-weight: 500;
          line-height: 1.01;
          letter-spacing: -.045em;
        }
        .tp-cover-tagline {
          margin: 22px 0 0;
          color: var(--tp-plum-soft);
          font-size: 13px;
          line-height: 1.2;
          letter-spacing: .045em;
        }
        .tp-cover-site {
          position: absolute;
          left: 37px;
          bottom: 30px;
          margin: 0;
          color: var(--tp-plum);
          font-size: 9px;
          letter-spacing: .075em;
        }

        .tp-letter {
          display: grid;
          grid-template-columns: 35% 65%;
          background: var(--tp-paper);
        }
        .tp-letter-aside {
          position: relative;
          padding: 105px 20px 39px;
          background:
            radial-gradient(ellipse at 0 100%, rgba(181,154,105,.16), transparent 46%),
            var(--tp-plum);
          color: var(--tp-paper);
        }
        .tp-letter-aside::after {
          content: "";
          position: absolute;
          top: 109px;
          right: 0;
          width: 2px;
          height: 48px;
          background: var(--tp-gold);
        }
        .tp-letter .tp-surface-label { left: auto; right: 30px; color: #ded0b8; }
        .tp-founder-photo-frame {
          width: 100%;
          height: 263px;
          overflow: hidden;
          border: 6px solid rgba(244,239,229,.92);
          background: #d1bfa9;
          box-shadow: 0 10px 26px rgba(24,14,24,.17);
        }
        .tp-founder-photo {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: 50% 26%;
        }
        .tp-founder-caption {
          margin: 16px 0 0;
          color: var(--tp-paper);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.1;
          letter-spacing: -.02em;
        }
        .tp-founder-role {
          margin: 8px 0 0;
          color: #d6c5a6;
          font-size: 10px;
          line-height: 1.45;
          letter-spacing: .025em;
        }
        .tp-letter-main {
          position: relative;
          padding: 79px 31px 36px;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .tp-draft {
          align-self: flex-start;
          margin: 0 0 16px;
          padding: 7px 9px 6px;
          border: 1px solid rgba(181,154,105,.84);
          color: #775d37;
          font-size: 8px;
          line-height: 1;
          letter-spacing: .105em;
          font-weight: 500;
        }
        .tp-letter-heading {
          margin: 0 0 15px;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 32px;
          line-height: 1;
          letter-spacing: -.04em;
          font-weight: 500;
        }
        .tp-letter-copy {
          color: #554950;
          font-size: 14.5px;
          line-height: 1.45;
          letter-spacing: .001em;
        }
        .tp-letter-copy p { margin: 0 0 11px; }
        .tp-letter-copy .tp-salutation { margin-bottom: 11px; color: var(--tp-plum); }
        .tp-letter-signoff { margin-top: 15px; padding-top: 5px; }
        .tp-with-warmth {
          margin: 0 0 4px;
          color: var(--tp-plum-soft);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 16px;
          font-style: italic;
          line-height: 1.2;
        }
        .tp-name {
          margin: 0;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.1;
          letter-spacing: -.02em;
        }
        .tp-title-lines {
          margin: 5px 0 0;
          color: #786c70;
          font-size: 9px;
          line-height: 1.4;
          letter-spacing: .02em;
        }

        .tp-notes {
          padding: 70px 42px 45px;
          background:
            radial-gradient(ellipse at 0 100%, rgba(181,154,105,.11), transparent 38%),
            var(--tp-paper);
        }
        .tp-notes .tp-surface-label { left: 42px; }
        .tp-notes-head {
          position: relative;
          min-height: 157px;
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          margin: 0 -42px 28px;
          padding: 23px 42px 19px;
          border-bottom: 1px solid rgba(181,154,105,.62);
        }
        .tp-notes-heading {
          margin: 16px 0 0;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 41px;
          line-height: .98;
          letter-spacing: -.045em;
          font-weight: 500;
        }
        .tp-note-group { margin: 0 0 28px; }
        .tp-note-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 0 0 7px;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 21px;
          line-height: 1.1;
          font-weight: 500;
        }
        .tp-note-title::after {
          content: "";
          height: 1px;
          flex: 1;
          background: rgba(181,154,105,.72);
        }
        .tp-note-line {
          height: 39px;
          border-bottom: 1px solid rgba(98,74,96,.35);
        }
        .tp-question-lines .tp-note-line { height: 49px; }
        .tp-notes-foot {
          position: absolute;
          right: 42px;
          bottom: 23px;
          left: 42px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: #857875;
          font-size: 8px;
          letter-spacing: .11em;
          text-transform: uppercase;
        }
        .tp-notes-foot::after {
          content: "";
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--tp-gold);
        }

        .tp-back-cover {
          background: var(--tp-paper);
        }
        .tp-back-photo {
          position: absolute;
          top: 0;
          right: 0;
          width: 32%;
          height: 100%;
          object-fit: cover;
          object-position: 50% center;
          display: block;
        }
        .tp-back-photo-shade {
          position: absolute;
          top: 0;
          right: 32%;
          width: 0;
          height: 100%;
          background: transparent;
        }
        .tp-back-content {
          position: absolute;
          inset: 0 auto 0 0;
          width: 68%;
          padding: 81px 35px 33px;
          background: var(--tp-paper);
        }
        .tp-back-label { left: 35px; }
        .tp-back-logo {
          display: block;
          width: 154px;
          height: auto;
          margin: 0 0 32px;
          mix-blend-mode: multiply;
        }
        .tp-back-heading {
          margin: 0 0 24px;
          color: var(--tp-plum);
          font-family: TogetherFraunces, Georgia, serif;
          font-size: 37px;
          line-height: .98;
          letter-spacing: -.045em;
          font-weight: 500;
        }
        .tp-back-rule {
          width: 100%;
          height: 1px;
          margin: 0 0 21px;
          background: rgba(181,154,105,.74);
        }
        .tp-contact-list { margin: 0; }
        .tp-contact-row {
          display: grid;
          grid-template-columns: 74px 1fr;
          gap: 8px;
          align-items: baseline;
          margin: 0 0 18px;
        }
        .tp-contact-label {
          margin: 0;
          color: #887668;
          font-size: 8px;
          line-height: 1.2;
          letter-spacing: .11em;
          text-transform: uppercase;
        }
        .tp-contact-value {
          margin: 0;
          color: var(--tp-plum);
          font-size: 13px;
          line-height: 1.35;
          overflow-wrap: anywhere;
        }
        .tp-back-site {
          position: absolute;
          bottom: 35px;
          left: 35px;
          margin: 0;
          color: var(--tp-plum);
          font-size: 10px;
          letter-spacing: .085em;
        }
        .tp-review {
          position: absolute;
          right: 19px;
          bottom: 22px;
          z-index: 3;
          margin: 0;
          color: rgba(244,239,229,.94);
          font-size: 8px;
          line-height: 1;
          letter-spacing: .14em;
          writing-mode: vertical-rl;
        }

        @media (max-width: 1050px) {
          .together-premium { grid-template-columns: 1fr; height: auto; min-height: 100dvh; overflow: visible; }
          .tp-panel { min-height: 100dvh; }
          .tp-panel + .tp-panel { border-left: 0; border-top: 1px solid rgba(64,40,65,.24); }
          .tp-cover-photo { inset: auto 0 0; width: 100%; height: 48%; object-position: center 42%; }
          .tp-cover-wash { inset: 0; background: linear-gradient(180deg, var(--tp-paper) 0 52%, transparent 52%); }
          .tp-cover-top { width: 100%; height: auto; padding: 52px 8vw 20px; }
          .tp-cover-label { left: 8vw; }
          .tp-title-plaque { width: 100%; height: 58%; padding: 15px 8vw 74px; }
          .tp-cover-title { font-size: clamp(47px, 10vw, 65px); }
          .tp-cover-site { left: 8vw; }
          .tp-letter-main { padding-right: 8vw; padding-left: 8vw; }
          .tp-letter-copy { font-size: 15px; line-height: 1.55; }
          .tp-founder-photo-frame { height: min(42vh, 330px); }
          .tp-notes { padding-right: max(32px, 8vw); padding-left: max(32px, 8vw); }
          .tp-notes-head { margin-right: calc(max(32px, 8vw) * -1); margin-left: calc(max(32px, 8vw) * -1); padding-right: max(32px, 8vw); padding-left: max(32px, 8vw); }
          .tp-notes .tp-surface-label { left: max(32px, 8vw); }
          .tp-back-photo { width: 40%; }
          .tp-back-content { width: 60%; padding-right: 6vw; padding-left: 6vw; }
        }
      `}</style>

      <section className="tp-panel tp-cover" aria-label="Front cover">
        <img className="tp-cover-photo" src="/__reviews-mockup/images/elh-patient-guide/together-family-no-faces.jpg" alt="An older woman and her adult son seated close together at home, photographed below the shoulders with no faces visible." />
        <div className="tp-cover-wash" aria-hidden="true" />
        <div className="tp-cover-top">
          <p className="tp-surface-label tp-cover-label">Front cover</p>
          <img className="tp-cover-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png" alt="Eternal Life Hospice" />
        </div>
        <div className="tp-title-plaque">
          <div className="tp-title-rule" aria-hidden="true" />
          <h1 className="tp-cover-title">Patient &amp;<br />Family Guide</h1>
          <p className="tp-cover-tagline">Care That Honors Life.</p>
          <p className="tp-cover-site">eternallifehospice.com</p>
        </div>
      </section>

      <section className="tp-panel tp-letter" aria-label="Inside front cover, founder letter draft">
        <aside className="tp-letter-aside">
          <p className="tp-surface-label">Inside front cover</p>
          <div className="tp-founder-photo-frame">
            <img className="tp-founder-photo" src="/__reviews-mockup/images/elh-patient-guide/aleksandra-founder.jpg" alt="Aleksandra Dubina, founder and CEO of Eternal Life Hospice." />
          </div>
          <p className="tp-founder-caption">Aleksandra<br />Dubina</p>
          <p className="tp-founder-role">Founder &amp; CEO<br />Certified Hospice Administrator</p>
        </aside>
        <div className="tp-letter-main">
          <p className="tp-draft">DRAFT FOR ALEKSANDRA’S REVIEW</p>
          <h2 className="tp-letter-heading">A note from<br />Aleksandra</h2>
          <div className="tp-letter-copy">
            <p className="tp-salutation">Dear family,</p>
            <p>When someone you love is receiving hospice care, there can be a great deal to take in. This guide is here to help you understand your loved one’s care, know who to call and feel more prepared for what may come next.</p>
            <p>Inside, you will find information about your hospice team, comfort and symptom management, family support, safety, privacy and patient rights. You do not need to read it all at once. Begin with what feels most useful today and return to the other sections when you are ready.</p>
            <p>No guide can replace a conversation. Please share your questions, concerns and the details that make your loved one who they are. Your voice helps us understand what matters most to your family. Thank you for welcoming Eternal into your loved one’s care.</p>
          </div>
          <div className="tp-letter-signoff">
            <p className="tp-with-warmth">With warmth,</p>
            <p className="tp-name">Aleksandra Dubina</p>
            <p className="tp-title-lines">Founder &amp; CEO<br />Certified Hospice Administrator</p>
          </div>
        </div>
      </section>

      <section className="tp-panel tp-notes" aria-label="Inside back cover, family notes">
        <p className="tp-surface-label">Inside back cover</p>
        <div className="tp-notes-head">
          <h2 className="tp-notes-heading">Your<br />notes</h2>
        </div>
        <div className="tp-note-group">
          <h3 className="tp-note-title">Your care team</h3>
          <div className="tp-note-line" />
          <div className="tp-note-line" />
        </div>
        <div className="tp-note-group tp-question-lines">
          <h3 className="tp-note-title">Questions to keep close</h3>
          <div className="tp-note-line" />
          <div className="tp-note-line" />
          <div className="tp-note-line" />
          <div className="tp-note-line" />
        </div>
        <div className="tp-notes-foot">
          <span>DESIGN CONCEPT · FOR REVIEW</span>
        </div>
      </section>

      <section className="tp-panel tp-back-cover" aria-label="Outside back cover with contact details">
        <p className="tp-surface-label tp-back-label">Outside back cover</p>
        <img className="tp-back-photo" src="/__reviews-mockup/images/elh-patient-guide/together-family-no-faces.jpg" alt="An older woman and her adult son seated close together at home, photographed below the shoulders with no faces visible." />
        <div className="tp-back-photo-shade" aria-hidden="true" />
        <div className="tp-back-content">
          <img className="tp-back-logo" src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png" alt="Eternal Life Hospice" />
          <h2 className="tp-back-heading">Keep us<br />close</h2>
          <div className="tp-back-rule" aria-hidden="true" />
          <dl className="tp-contact-list">
            <div className="tp-contact-row">
              <dt className="tp-contact-label">Main</dt>
              <dd className="tp-contact-value">805.410.1151</dd>
            </div>
            <div className="tp-contact-row">
              <dt className="tp-contact-label">Office</dt>
              <dd className="tp-contact-value">805.953.7273</dd>
            </div>
            <div className="tp-contact-row">
              <dt className="tp-contact-label">Email</dt>
              <dd className="tp-contact-value">info@eternallifehospice.com</dd>
            </div>
            <div className="tp-contact-row">
              <dt className="tp-contact-label">Address</dt>
              <dd className="tp-contact-value">4165 E Thousand Oaks Blvd, Ste 325B<br />Westlake Village, CA 91362</dd>
            </div>
          </dl>
          <p className="tp-back-site">eternallifehospice.com</p>
        </div>
        <p className="tp-review">DESIGN CONCEPT · FOR REVIEW</p>
      </section>
    </main>
  );
}
