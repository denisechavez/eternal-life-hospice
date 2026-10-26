import React from "react";
import { GardenPremium } from "./GardenPremium";

type Side = "outside" | "inside";

/** Two flat cover spreads, not an imposition of the handbook's interior pages. */
export function GardenPrintSpreads({ side }: { side?: Side }) {
  const sides: Side[] = side ? [side] : ["outside", "inside"];
  return (
    <div className="garden-print-proof" aria-label="17.5 by 11 inch guide cover proof with a half-inch spine">
      <style>{`
        .garden-print-proof { width: 100%; margin: 0; background: #f5efe4; }
        .garden-sheet { width: 1400px; height: 880px; overflow: hidden; position: relative; }
        .garden-sheet .garden-premium {
          width: 1400px; height: 880px; min-height: 0;
          grid-template-columns: 680px 680px;
          column-gap: 40px;
          background: var(--gp-plum);
        }
        .garden-sheet .gp-label { display: none; }
        .garden-sheet .gp-panel { border-left: 0; }
        .garden-sheet[data-side="outside"] .gp-letter,
        .garden-sheet[data-side="outside"] .gp-notes,
        .garden-sheet[data-side="inside"] .gp-cover,
        .garden-sheet[data-side="inside"] .gp-back { display: none; }
        .garden-sheet[data-side="outside"] .gp-back { order: 0; }
        .garden-sheet[data-side="outside"] .gp-cover { order: 1; }
        .garden-sheet[data-side="inside"] .gp-letter { order: 0; }
        .garden-sheet[data-side="inside"] .gp-notes { order: 1; }
        @page { size: 17.5in 11in; margin: 0; }
        @media print {
          html, body, #root { width: 17.5in !important; margin: 0 !important; padding: 0 !important; }
          .garden-print-proof { width: 17.5in; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
          .garden-sheet {
            width: 17.5in; height: 11in;
            break-after: page; break-inside: avoid;
          }
          .garden-sheet:last-child { break-after: auto; }
          .garden-sheet .garden-premium {
            transform: scale(1.2); transform-origin: top left;
          }
        }
      `}</style>
      {sides.map((value) => (
        <section
          className="garden-sheet"
          data-side={value}
          key={value}
          aria-label={value === "outside"
            ? "Outside: 8.5-inch back cover, half-inch plum spine, 8.5-inch front cover"
            : "Inside: 8.5-inch inside front, half-inch plum spine, 8.5-inch inside back"}
        >
          <GardenPremium />
        </section>
      ))}
    </div>
  );
}
