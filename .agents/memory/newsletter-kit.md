---
name: Monthly newsletter kit
description: Structure, compliance framing, and print-render notes for the ELH monthly newsletter deliverable.
---

# Monthly newsletter kit

Lives in `exports/newsletter/` (collateral, NOT published to the site). Deliverable =
a review doc + three reusable layout templates, each rendered to a print-ready PDF and
zipped as `elh-newsletter-review-kit.zip` (HTML + PDFs + logos, self-contained).

- **Three layouts** (reusable templates, swap copy monthly): **Editorial** (warm
  single-column, family-facing) · **Digest** (compact scannable blocks, referral
  partners) · **Spotlight** (one bold hero feature — used for the Trust/fraud issue).
- **Three outlines**: A "Trust Issue" (Compliance-Led / consumer protection) → Spotlight;
  B "Care & Comfort" (family) → Editorial; C "Referral Partner Briefing" (B2B) → Digest.

## Fraud / "trust" angle — APPROVED framing (compliance-critical)
User wants to talk about LA/nationwide hospice fraud. Do it as **consumer education, not
attack**:
- **Why:** it showcases the Compliance-Led Care pillar and builds trust; but naming/implying
  a specific competitor is defamation risk, and unsourced fraud stats are legal risk.
- **How to apply:** frame as "how to recognize a *legitimate* hospice" (red flags +
  60-second verify checklist). Attribute facts to public authorities only — the **2022
  California State Auditor report** + the state's **2022 pause on new hospice licenses**.
  Soften absolutes ("widespread indicators of fraud", not hard counts). Never name a
  competitor. Keep a footer source/disclaimer line ("does not describe any specific
  provider"). For partner content keep it quality/integrity, never inducements (Anti-Kickback).

## Ongoing ops
Monthly cadence, fixed send day; Aleksandra = compliance sign-off + final approval.
ESP = MailerLite/Brevo (NOT Klaviyo — e-comm/HIPAA). Two segments: Families/Community vs
Referral Partners. No PHI ever. Templates carry placeholder `href="#"` unsubscribe —
must be swapped for real ESP merge tags before any live send (they are review drafts).
