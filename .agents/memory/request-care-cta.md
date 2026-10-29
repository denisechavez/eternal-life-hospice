---
name: Request Care CTA
description: The canonical destination and audience selection for the primary Request Care call to action.
---

Every family-facing Request Care CTA should open the homepage lead section with the Family · Seeking care audience selected, including callback and evaluation variants.

**Why:** The CTA serves families seeking hospice care and should not send them into the provider referral flow or the Share Your Voice form.

**How to apply:** Use the family-targeted homepage URL for Request Care, Request a Call Back, Request a Free Evaluation, and equivalent family-facing labels: `/?lead=family#leadcap`. Keep direct phone CTAs as phone links, provider referrals routed to `/refer`, and professional voice/education requests routed separately.

Throughout the website, present the header's Request Care button as a direct
action without an adjacent dropdown arrow or submenu.

**Why:** After the homepage-only change, the owner still saw the arrow on
Resources and requested its removal there too. The direct-action treatment
must be consistent across pages.

**How to apply:** Keep the family-request destination intact and leave the other
navigation dropdowns unchanged. Refresh the served header-script URL when its
contents change so cached copies do not preserve an obsolete control.