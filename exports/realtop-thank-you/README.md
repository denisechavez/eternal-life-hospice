# Eternal Life Hospice — Google PPC thank-you page review

Prepared for the Google PPC campaign landing page:
https://eternal-life-hospice.rt-go.com/.

RealTop helps Eternal understand PPC. This packet does not assume RealTop owns
the landing page or manages its form. Confirm who has form-settings access
before configuring the live confirmation flow.

## What is included

- `ELH-Google-PPC-Thank-You-Review.pdf`: two-page review packet. Page 1 is the
  proposed design; page 2 contains the implementation requirements.
- `ELH-Google-PPC-Thank-You-Review.html`: responsive, self-contained design
  reference with embedded official logo and fonts. It can be opened locally.
- `Google-PPC-Implementation-Notes.html`: printable implementation brief.

**This is a design review, not an active confirmation flow.** No form is
submitted, no email is sent and no tracking event is fired by these files.
The review disclosure is intentional. Do not publish this file unchanged or
remove the disclosure until Eternal Life Hospice approves the design and
the form administrator implements a genuine successful-submission flow.

## Approved wording to retain

Thank you. We’ve received your request.

A member of our care team will contact you to discuss your needs and next steps.

Need to speak with someone now?

We're here for you 24 hours a day, 7 days a week.

Call 805.409.9262

The phone link is `tel:+18054099262`. The owner has asked RealTop to revise
the external landing page from its landline to this tracking number. The review
now matches that requested correction; it does not establish that the live
landing page has been updated. Main-site and approved email phone placements
are outside this handoff.

## Information requested from RealTop

- Identify the landing-page/form administrator and form provider.
- Confirm available success redirect, inline confirmation or verified callback
  settings and share setup documentation, not credentials.
- Confirm where requests are saved/routed and how the form reports acceptance.
- Confirm existing Google Ads conversion ownership and Nimbata phone replacement.
- Coordinate a final HTTPS thank-you URL and hosting arrangement with Eternal.
  Creating this file alone does not connect the external form.
- Identify the person who can run an authorized synthetic test and verify receipt,
  response time, mobile click-to-call and conversion deduplication.

Show a sending status immediately and the confirmation as soon as acceptance is
verified, with no intentional delay. Staff review, email and analytics must not
block the thank-you screen. Measure actual timing during testing.

## Google PPC integration requirements

1. Display the confirmation only after the actual form provider confirms that
   the request was accepted and saved. A button click, attempted request, URL
   parameter or page view is not proof of receipt.
2. On a failed or pending submission, retain the form and show honest status
   and retry/call guidance. Do not show this successful-receipt message.
3. A direct visit without a verified submission must show neutral guidance,
   not claim a request was received. Reload, back/forward navigation, repeated
   callbacks and duplicate redirects must not create duplicate submissions or
   conversion events.
4. Inspect the existing Google Ads conversion setup before adding anything.
   Choose one confirmed-success event owner: the accepted form handler or a
   verified confirmation flow, not both. The supplied destination is
   `AW-18384023405/JC8lCKGQ9qsdEO3el75E`, value `1.0`, currency `USD`.
   Retain the existing tracking-consent requirements. Do not fire a conversion
   merely because this HTML was opened.
5. Use a non-personal opaque receipt reference if one is needed for deduplication.
   Never put patient details, names, email addresses, phone numbers or medical
   information into URLs, analytics payloads or browser logs.
6. A customer acknowledgment email is a separate integration. This package does
   not send or claim to send one. Any future receipt must preserve Eternal's
   approved copy and company-Gmail delivery requirement, not use Brevo.
7. Preserve keyboard access, readable contrast, mobile layout and clickable
   phone links. Bold phone text does not need an underline.
8. Obtain Eternal's approval before publication. Test accepted, rejected,
   pending and duplicate submissions using agreed synthetic test data in a
   controlled environment. Do not submit real patient requests or place calls
   without authorization.

## Rebuilding within this project

The visual source is the existing review sandbox's
`public/elh-realtop-thank-you-review.html`, not the main public website.
Run `python3 scripts/build-realtop-thank-you-review.py` to rebuild the PDF
and ZIP in the ignored `generated-artifacts/google-ppc-thank-you/` directory.
Internal source paths retain their original names to preserve existing review
links; all exported deliverables use the Google PPC name.
