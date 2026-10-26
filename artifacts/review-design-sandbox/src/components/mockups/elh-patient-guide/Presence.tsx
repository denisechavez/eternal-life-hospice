export function Presence() {
  return (
    <main className="elh-presence-cover" aria-label="Eternal Life Hospice Patient & Family Guide cover">
      <style>{`
        @font-face {
          font-family: "ELH Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-weight: 500;
          font-display: swap;
        }
        .elh-presence-cover,
        .elh-presence-cover * {
          box-sizing: border-box;
        }
        .elh-presence-cover {
          --presence-cream: #f6f0e5;
          --presence-plum: #4c2943;
          --presence-gold: #a77f43;
          position: relative;
          isolation: isolate;
          width: 100%;
          height: 100dvh;
          min-height: 100%;
          overflow: hidden;
          background: var(--presence-cream);
          color: var(--presence-plum);
          font-family: "ELH Jost", sans-serif;
        }
        .elh-presence-cover::before {
          position: absolute;
          z-index: -1;
          top: 19%;
          right: -18%;
          width: 50%;
          height: 54%;
          border: 1px solid rgba(167, 127, 67, .28);
          border-radius: 50%;
          content: "";
          transform: rotate(-18deg);
        }
        .elh-presence-brand {
          position: absolute;
          top: 4.5%;
          left: 50%;
          display: flex;
          width: 42%;
          height: 13%;
          align-items: center;
          justify-content: center;
          transform: translateX(-50%);
        }
        .elh-presence-brand img {
          display: block;
          width: 100%;
          max-height: 100%;
          object-fit: contain;
        }
        .elh-presence-photo {
          position: absolute;
          top: 20%;
          left: 5.3%;
          width: 89.4%;
          height: 49%;
          overflow: hidden;
          border-radius: 2px 2px 15% 2px;
          background: #d8c8ad;
        }
        .elh-presence-photo img {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: 52% 43%;
        }
        .elh-presence-photo::after {
          position: absolute;
          inset: 0;
          border: 1px solid rgba(76, 41, 67, .11);
          border-radius: inherit;
          content: "";
          pointer-events: none;
        }
        .elh-presence-title {
          position: absolute;
          top: 72.7%;
          left: 8.5%;
          width: 83%;
          margin: 0;
          font-family: "ELH Fraunces", Georgia, serif;
          font-size: clamp(34px, 7.3vw, 58px);
          font-weight: 500;
          letter-spacing: -.045em;
          line-height: .98;
        }
        .elh-presence-title span {
          display: block;
        }
        .elh-presence-tagline {
          position: absolute;
          top: 87.5%;
          left: 8.8%;
          margin: 0;
          color: var(--presence-gold);
          font-family: "ELH Fraunces", Georgia, serif;
          font-size: clamp(17px, 3vw, 22px);
          font-style: italic;
          font-weight: 400;
          letter-spacing: -.01em;
        }
        .elh-presence-rule {
          position: absolute;
          right: 8.5%;
          bottom: 7.2%;
          left: 8.5%;
          height: 1px;
          background: rgba(167, 127, 67, .52);
        }
        .elh-presence-url {
          position: absolute;
          bottom: 3.1%;
          left: 8.7%;
          margin: 0;
          color: var(--presence-plum);
          font-size: clamp(10px, 1.75vw, 12px);
          font-weight: 500;
          letter-spacing: .12em;
        }
        @media (max-aspect-ratio: 3 / 4) {
          .elh-presence-title {
            font-size: clamp(31px, 8vw, 54px);
          }
        }
      `}</style>
      <div className="elh-presence-brand">
        <img
          src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
          alt="Eternal Life Hospice"
        />
      </div>
      <div className="elh-presence-photo">
        <img
          src="/__reviews-mockup/images/elh-patient-guide/care.webp"
          alt="A nurse sharing a warm, attentive moment with an older man at home"
        />
      </div>
      <h1 className="elh-presence-title">
        <span>Patient &amp;</span>
        <span>Family Guide</span>
      </h1>
      <p className="elh-presence-tagline">Care That Honors Life.</p>
      <div className="elh-presence-rule" aria-hidden="true" />
      <p className="elh-presence-url">eternallifehospice.com</p>
    </main>
  );
}
