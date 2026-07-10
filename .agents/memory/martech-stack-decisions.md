---
name: MarTech / platform stack decisions (ELH)
description: Which CRM, email, newsletter, and analytics tools ELH uses and why — cost & compliance rationale.
---

# ELH marketing/ops stack decisions

**Context:** cashflow is slow → cost containment is a hard constraint. Build-to-sell objective still stands.

**Confirmed accounts (owner-provided):**
- Domain registrar = **GoDaddy**.
- Business email = **Google Workspace** (info@eternallifehospice.com).
- Chat-bot **Anthropic key is on the owner's PERSONAL account** → must be MOVED to a company Anthropic account (billing/control). Set spend cap.

**Live third-party on the site (all free):** Google Analytics (G-JRLYCRC48G), Microsoft Clarity, Google Fonts, Resend (form auto-replies, free tier). Hosting = Netlify free tier.

**Platform recommendations (given to the owner in exports/ops/eternal-life-website-costs-and-roadmap.xlsx):**
- **Klaviyo: AVOID** for ELH. It's e-commerce-focused, priced by contact count, and NOT a HIPAA/BAA fit. Wrong tool for a hospice referral model. **Why:** cost scales badly + compliance risk.
- **CRM: HubSpot Free CRM** ($0) — referral-partner/enquiry tracking, no lock-in.
- **Newsletter/email marketing: MailerLite** (free ≤1,000 subs) or **Brevo** (free, bundles light CRM+email).
- **Transactional email: keep Resend.**
- **Blog: build as STATIC pages inside elh-preview** = $0 ongoing (no CMS subscription). Good for SEO + AI-search + reusable social content.
- **Paid SEO tools (Ahrefs/Semrush): DEFER** — ranking comes from content + technical SEO already done, not a subscription.

**Compliance guardrail:** keep patient/family PHI OUT of all marketing tools. B2B referral-partner newsletters = low risk; any family-facing list must respect HIPAA + no medical-efficacy claims.
