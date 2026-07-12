---
name: The Eternal Care Brief
description: Bi-monthly care publication library on the site; rebuilt from user's Base44 prototype; email version pending.
---

# The Eternal Care Brief (bi-monthly publication)

- Library landing: `care-brief.html`; issues live in `care-brief/` (Issue One = `hospice-is-part-of-life-a-continuation-of-care.html`). Footer-linked sitewide under "For Providers".
- Fixed 8-section format per issue: Founder Note · Lead Article · Care Team Spotlight · Whole-Person Comfort · Eternal Standard Spotlight · Current Care Conversation · Family Section · Resources. Keep this structure for every future issue.
- Source of truth for Issue One was the user's Base44 prototype (eternal-care-brief.base44.app); site version is canonical now — do not re-sync from Base44.
- **Compliance rule:** the prototype's "Source Note" placeholder (unverified CMS/OIG/NHPCO citations) was deliberately dropped. Never publish citations without verification. Sound-comfort section must keep non-efficacy framing.
- **Why:** healthcare marketing compliance — no efficacy claims, no unverified sources, no referral inducements.
- Cadence decision: brief = bi-monthly on-site; weekly email lives in MailerLite/Brevo (not on the site). First intro email (table-based HTML, like exports/email/) still TO DO after user finishes content edits.
- Founder portrait `assets/img/aleksandra-dubina-founder.jpg` + `care-brief-sound.jpg` came from the Base44 CDN (may go away — local copies are canonical).
- Admin workflow decided: admin drafts/sends email in the ESP; bi-monthly site issues get added via a thread in this App.
- Issue-page "publication" chrome (user-approved, Axios-AM-inspired — keep for every issue): split hero (plum band left = cream logo/issue/date/pill; cream right = title+CTAs) + fixed left numbered rail 01–08 with IntersectionObserver scrollspy. Rail fades in only after scrolling past the hero and must stay `visibility:hidden` while hidden (keyboard a11y), hidden <1280px and in print.
- Editorial tradition (user decision): every volume's cover features a person who "introduces" the issue — portrait + "Introduced by" in the plum band. Volume One = Aleksandra Dubina (founder). Issue Two introducer = Barbara Colella (user-confirmed, first outside professional voice; she also brings an extensive contact database — those contacts need consent review before any email import). Pick the introducer when planning each new issue.
- Dev preview parity: the static site is served by `website/devserver.py` (outside the publish folder) which mimics Netlify pretty URLs (extensionless → .html). Plain `python -m http.server` breaks clean internal links and shows directory listings — don't revert to it. Trailing-slash dirs (blog/, care-brief/, resources/) have noindex redirect stubs.

- Fresh-first navigation (user decision): sitewide footer "Care Brief" link points to the NEWEST issue directly, not the library page. Library (/care-brief) stays as archive/SEO hub, reachable via the issue page backlink. Publish-an-issue checklist: repoint footer link sitewide + sitemap + read time in hero meta ("N sections · N min read"), byline, AND per-section "N min read" spans in each .cb-head (compute at ~210 wpm; total = sum of section times so numbers agree).

- Portrait treatment (user iterated: circle="cookie cutter", arch="church setting"): introducer portraits use a FEATHERED VIGNETTE — CSS mask-image radial-gradient ellipse fade (no border/keyline/shadow) + soft gold radial halo + a RIBBON MOTIF (user-requested, echoes the infinity logo's tone, not literal): inline SVG tapered metallic champagne-gold band sweeping behind the lower portrait, fine filament echo line, thin front strand crossing the lower edge. Fuller/brighter on the plum hero band; subtler on the cream library card (card needs overflow:hidden so the ribbon clips at its rounded edge). Standard for all future introducers.
