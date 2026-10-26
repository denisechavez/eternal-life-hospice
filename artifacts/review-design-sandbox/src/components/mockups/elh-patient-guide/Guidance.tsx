export function Guidance() {
  return (
    <main
      className="elh-guidance-cover"
      aria-label="Eternal Life Hospice Patient & Family Guide cover"
    >
      <style>{`
        @font-face {
          font-family: "ELH Guidance Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-latin.woff2") format("woff2");
          font-style: normal;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Guidance Fraunces";
          src: url("/__reviews-mockup/fonts/fraunces-italic-latin.woff2") format("woff2");
          font-style: italic;
          font-weight: 100 900;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Guidance Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Regular.woff2") format("woff2");
          font-weight: 400;
          font-display: swap;
        }
        @font-face {
          font-family: "ELH Guidance Jost";
          src: url("/__reviews-mockup/images/elh-patient-guide/JostELH-Medium.woff2") format("woff2");
          font-weight: 500;
          font-display: swap;
        }
        .elh-guidance-cover,
        .elh-guidance-cover * {
          box-sizing: border-box;
        }
        .elh-guidance-cover {
          --guidance-cream: #f6f0e5;
          --guidance-plum: #4c2943;
          --guidance-gold: #a77f43;
          position: relative;
          isolation: isolate;
          width: 100%;
          height: 100dvh;
          min-height: 100%;
          overflow: hidden;
          background:
            radial-gradient(ellipse at 92% 12%, rgba(205, 187, 155, .14), transparent 32%),
            var(--guidance-cream);
          color: var(--guidance-plum);
          font-family: "ELH Guidance Jost", sans-serif;
        }
        .elh-guidance-brand {
          position: absolute;
          top: 7.2%;
          left: 9.2%;
          display: flex;
          width: 30%;
          height: 8.5%;
          align-items: center;
        }
        .elh-guidance-brand img {
          display: block;
          width: 100%;
          max-height: 100%;
          object-fit: contain;
          object-position: left center;
        }
        .elh-guidance-top-rule {
          position: absolute;
          top: 18.2%;
          right: 9.2%;
          left: 9.2%;
          height: 1px;
          background: rgba(76, 41, 67, .2);
        }
        .elh-guidance-top-rule::before {
          position: absolute;
          top: -2px;
          left: 0;
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--guidance-gold);
          content: "";
        }
        .elh-guidance-route {
          position: absolute;
          z-index: -1;
          top: 22%;
          right: -1%;
          width: 29%;
          height: 59%;
          overflow: visible;
        }
        .elh-guidance-route path {
          fill: none;
          stroke: rgba(167, 127, 67, .55);
          stroke-width: 1.15;
          vector-effect: non-scaling-stroke;
        }
        .elh-guidance-route circle {
          fill: var(--guidance-gold);
        }
        .elh-guidance-title {
          position: absolute;
          top: 31%;
          left: 13.3%;
          width: 77%;
          margin: 0;
          color: var(--guidance-plum);
          font-family: "ELH Guidance Fraunces", Georgia, serif;
          font-size: clamp(52px, 10.4vw, 76px);
          font-weight: 500;
          letter-spacing: -.055em;
          line-height: .96;
        }
        .elh-guidance-title span {
          display: block;
          white-space: nowrap;
        }
        .elh-guidance-title .elh-guidance-final {
          position: relative;
          width: fit-content;
          margin-top: .03em;
          font-size: 1.34em;
          font-style: italic;
          font-weight: 400;
          letter-spacing: -.065em;
          line-height: 1.06;
        }
        .elh-guidance-title .elh-guidance-final::after {
          position: absolute;
          right: -.18em;
          bottom: .09em;
          left: .02em;
          z-index: -1;
          height: .11em;
          background: rgba(167, 127, 67, .45);
          content: "";
        }
        .elh-guidance-tagline {
          position: absolute;
          top: 70.5%;
          left: 13.7%;
          margin: 0;
          color: var(--guidance-plum);
          font-size: clamp(17px, 2.9vw, 22px);
          font-weight: 500;
          letter-spacing: .005em;
        }
        .elh-guidance-lower-rule {
          position: absolute;
          right: 9.2%;
          bottom: 11.1%;
          left: 9.2%;
          height: 1px;
          background: rgba(76, 41, 67, .2);
        }
        .elh-guidance-url {
          position: absolute;
          bottom: 5.9%;
          left: 9.3%;
          margin: 0;
          color: var(--guidance-plum);
          font-size: clamp(11px, 1.8vw, 13px);
          font-weight: 500;
          letter-spacing: .1em;
        }
        @media (max-aspect-ratio: 3 / 4) {
          .elh-guidance-title {
            top: 32%;
            left: 10%;
            width: 84%;
            font-size: clamp(48px, 10.2vw, 73px);
          }
          .elh-guidance-tagline {
            left: 10.4%;
          }
          .elh-guidance-route {
            right: -8%;
            width: 34%;
          }
        }
        @media (max-height: 620px) {
          .elh-guidance-title {
            top: 27%;
          }
          .elh-guidance-tagline {
            top: 76%;
          }
        }
      `}</style>
      <div className="elh-guidance-brand">
        <img
          src="/__reviews-mockup/images/elh-patient-guide/logo-plum.png"
          alt="Eternal Life Hospice"
        />
      </div>
      <div className="elh-guidance-top-rule" aria-hidden="true" />
      <svg
        className="elh-guidance-route"
        viewBox="0 0 180 520"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path d="M148 0 C116 88 154 147 121 226 C90 302 130 359 89 433 C70 467 42 492 12 520" />
        <circle cx="148" cy="3" r="3" />
      </svg>
      <h1 className="elh-guidance-title">
        <span>Patient &amp;</span>
        <span>Family</span>
        <span className="elh-guidance-final">Guide</span>
      </h1>
      <p className="elh-guidance-tagline">Care That Honors Life.</p>
      <div className="elh-guidance-lower-rule" aria-hidden="true" />
      <p className="elh-guidance-url">eternallifehospice.com</p>
    </main>
  );
}
