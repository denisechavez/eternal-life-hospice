import React from "react";

/** Reuses the reviewed cover artwork without rebuilding or changing its content. */
export function CoverPrintSpreads({ children, name, plum }: {
  children: React.ReactNode;
  name: string;
  plum: string;
}) {
  return (
    <div className="cover-export" aria-label={`${name}, outside and inside spreads with half-inch spine`}>
      <style>{`
        .cover-export { margin: 0; width: 1400px; }
        .cover-export-sheet { width: 1400px; height: 880px; overflow: hidden; position: relative; }
        .cover-export-sheet > main {
          width: 1400px; height: 880px; min-height: 0;
          grid-template-columns: 680px 680px; column-gap: 40px;
          background: ${plum};
        }
        .cover-export-sheet > main > section { border-left: 0; }
        .cover-export-sheet .tp-surface-label,
        .cover-export-sheet .cg-label { display: none; }
        .cover-export-sheet[data-side="outside"] > main > section:nth-of-type(2),
        .cover-export-sheet[data-side="outside"] > main > section:nth-of-type(3),
        .cover-export-sheet[data-side="inside"] > main > section:nth-of-type(1),
        .cover-export-sheet[data-side="inside"] > main > section:nth-of-type(4) { display: none; }
        .cover-export-sheet[data-side="outside"] > main > section:nth-of-type(4) { order: 0; }
        .cover-export-sheet[data-side="outside"] > main > section:nth-of-type(1) { order: 1; }
        @page { size: 17.5in 11in; margin: 0; }
        @media print {
          html, body, #root { width: 17.5in !important; margin: 0 !important; padding: 0 !important; }
          .cover-export { width: 17.5in; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
          .cover-export-sheet { width: 17.5in; height: 11in; break-after: page; break-inside: avoid; }
          .cover-export-sheet:last-child { break-after: auto; }
          .cover-export-sheet > main { transform: scale(1.2); transform-origin: top left; }
        }
      `}</style>
      {(["outside", "inside"] as const).map(side => (
        <section className="cover-export-sheet" data-side={side} key={side}
          aria-label={side === "outside"
            ? "Outside back, half-inch spine, front cover"
            : "Inside front, half-inch spine, inside back"}>
          {children}
        </section>
      ))}
    </div>
  );
}
