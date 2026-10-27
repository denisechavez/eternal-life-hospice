import React from "react";

/** Read-only canvas view of the same proposed emails supplied in the review PDF. */
export function Acknowledgments() {
  return (
    <iframe
      title="Eight proposed Eternal Life Hospice acknowledgment emails — drafts only"
      src="/__reviews-mockup/email-acknowledgments-review.html#family"
      style={{
        display: "block",
        width: "100%",
        height: "100dvh",
        border: 0,
        background: "#f5f0eb",
      }}
    />
  );
}
