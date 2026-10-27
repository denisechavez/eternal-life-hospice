import React from "react";

/** Read-only canvas view of the same proposed emails supplied in the review PDF. */
export function Acknowledgments() {
  return (
    <iframe
      title="Fourteen approved Eternal Life Hospice acknowledgment emails — unpublished development preview"
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
