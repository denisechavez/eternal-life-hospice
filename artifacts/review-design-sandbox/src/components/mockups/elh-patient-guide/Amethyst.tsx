import React from "react";

export function Amethyst() {
  return (
    <main className="amethyst-cover" aria-label="Eternal Life Hospice Patient & Family Guide cover">
      <style>{`
        @font-face {
          font-family: ELHFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: ELHFraunces;
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 400 700;
          font-display: swap;
        }
        @font-face {
          font-family: ELHJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: ELHJost;
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-style: normal;
          font-weight: 500 700;
          font-display: swap;
        }
        .amethyst-cover, .amethyst-cover * { box-sizing: border-box; }
        .amethyst-cover {
          --paper: #f5f0e6;
          --plum: #3d2340;
          --gold: #b69a65;
          position: relative;
          width: 100%;
          height: 100%;
          min-height: 100dvh;
          overflow: hidden;
          background: var(--paper);
          color: var(--plum);
          font-family: ELHJost, sans-serif;
          isolation: isolate;
        }
        .amethyst-top {
          position: absolute;
          inset: 0 0 40% 0;
          background:
            radial-gradient(ellipse at 100% 0%, rgba(182,154,101,.11), transparent 36%),
            var(--paper);
        }
        .amethyst-logo {
          position: absolute;
          top: 5.6%;
          left: 8.2%;
          width: 27%;
          height: auto;
          display: block;
          mix-blend-mode: multiply;
        }
        .amethyst-title {
          position: absolute;
          z-index: 2;
          left: 8.2%;
          top: 24.1%;
          width: 83%;
          margin: 0;
          font-family: ELHFraunces, Georgia, serif;
          font-size: clamp(36px, 7.35vw, 57px);
          line-height: .99;
          letter-spacing: -.045em;
          font-weight: 500;
          color: var(--plum);
        }
        .amethyst-divider {
          position: absolute;
          left: 8.4%;
          top: 38.4%;
          width: 12.5%;
          height: 2px;
          background: var(--gold);
        }
        .amethyst-tagline {
          position: absolute;
          left: 8.2%;
          top: 40.6%;
          margin: 0;
          font-size: clamp(13px, 2.7vw, 18px);
          line-height: 1.2;
          letter-spacing: .025em;
          color: #684d67;
        }
        .amethyst-image {
          position: absolute;
          inset: 48.4% 0 8.4%;
          width: 100%;
          height: 43.2%;
          object-fit: cover;
          object-position: center 49%;
          display: block;
        }
        .amethyst-image-wash {
          position: absolute;
          z-index: 1;
          inset: 48.4% 0 8.4%;
          background: linear-gradient(180deg, rgba(47,29,45,.04) 60%, rgba(47,29,45,.26));
          pointer-events: none;
        }
        .amethyst-image-edge {
          position: absolute;
          z-index: 2;
          top: 48.4%;
          left: 8.2%;
          right: 8.2%;
          height: 1px;
          background: rgba(182,154,101,.8);
        }
        .amethyst-footer {
          position: absolute;
          inset: auto 0 0;
          height: 8.4%;
          display: flex;
          align-items: center;
          padding: 0 8.2%;
          background: var(--paper);
        }
        .amethyst-site {
          margin: 0;
          color: var(--plum);
          font-size: clamp(10px, 2vw, 13px);
          letter-spacing: .12em;
          text-transform: lowercase;
        }
        .amethyst-footer-rule {
          position: absolute;
          right: 8.2%;
          width: 17%;
          height: 1px;
          background: var(--gold);
          opacity: .8;
        }
        @media (max-aspect-ratio: 680/880) {
          .amethyst-title { font-size: 7.35vw; }
        }
      `}</style>
      <div className="amethyst-top" aria-hidden="true" />
      <img
        className="amethyst-logo"
        src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
        alt="Eternal Life Hospice"
      />
      <h1 className="amethyst-title">Patient &amp; Family<br />Guide</h1>
      <div className="amethyst-divider" aria-hidden="true" />
      <p className="amethyst-tagline">Care That Honors Life.</p>
      <img
        className="amethyst-image"
        src="/__reviews-mockup/images/elh-patient-guide/amethyst.png"
        alt="A large natural amethyst geode, its violet crystal interior catching warm light"
      />
      <div className="amethyst-image-wash" aria-hidden="true" />
      <div className="amethyst-image-edge" aria-hidden="true" />
      <footer className="amethyst-footer">
        <p className="amethyst-site">eternallifehospice.com</p>
        <span className="amethyst-footer-rule" aria-hidden="true" />
      </footer>
    </main>
  );
}
