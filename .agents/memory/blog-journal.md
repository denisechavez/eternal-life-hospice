---
name: Journal (blog)
description: How the ELH "Eternal Journal" blog is structured, its conventions, and the backdating/compliance decisions behind it.
---

# The Eternal Journal (blog)

The site's blog is branded **"The Eternal Journal"** (display label "Journal"),
URL root **/blog**. Index = `blog.html` (root-level, inline-free — links the shared
`assets/elh.css`). Posts live in `blog/<slug>.html` and use the **same template
convention as `resources/` sub-pages**: `../assets/...` + `../<page>` relative
paths, `.article/.lede/.ask/.note-panel/.kicker/.cta/.related/.rgrid/.rc` classes,
header/footer extracted byte-exact from a resources sub-page (root pages derive
theirs via `.replace("../","")`).

## Publication boundary: Journal vs. Care Brief

The **Eternal Journal** and **The Eternal Care Brief** are separate publications
and must never share identity, cadence, attribution, or template labels:

- **Eternal Journal:** the website blog, with a daily publishing plan for the
  next 30 days.
- **Eternal Care Brief:** a bi-monthly publication. Only Issue One has been
  produced so far, and it comes from Aleksandra.

**Why:** Treating a Care Brief email as the Journal's email template falsely
combines two intentionally different editorial products and misstates the
Care Brief's authorship and publishing history.

**How to apply:** Keep separate dashboard sections, template names, campaign
labels, schedules, and source assets. Never call a Care Brief or Family Guide
email the approved Journal template. A Journal email template is not confirmed
until the user identifies or approves one specifically for the Journal.

## Conventions to keep consistent
- **Attribution:** Show the sender/author as **“The Eternal Life Hospice Team.”**
  Never invent individual staff names or use unverified placeholder identities.
- **Human connection:** Journal CTAs should speak as a team of real people who
  listen, answer questions, and stay with the family through the next step. Avoid
  institutional wording that makes Eternal Life Hospice sound like an impersonal
  company.
- **Positive assurance:** Never use double negatives or a negative contrast to
  support a positive statement. State the reassurance, benefit, or expectation
  directly—especially in article endings and family-facing calls to action.
- **Discoverability:** every post links from the site-wide footer "For Families"
  column (a `Journal` link sits between Resources and Volunteer on all pages).
  It is intentionally NOT in the top nav (that would touch ~28 files' nav markup).
- **Card meta:** blog cards carry a `.rc-meta` date line; index has a `.blog-featured`
  hero-overlap card (newest post) + `.rgrid` of the rest. Post pages have a
  `.blog-byline` (author + date + read time) under the hero.
- **CSS:** blog-only selectors are appended under `/* ===== JOURNAL / BLOG ===== */`
  in `elh.css`; blog pages request `elh.css?v=20260709` (bumped so new classes load).
  Other pages keep their older `?v=` and are unaffected (only new class names added).
- **SEO:** each post has canonical, OG/Twitter, `Article` + `BreadcrumbList` JSON-LD
  with `datePublished`/`dateModified`; index has `Blog` JSON-LD listing all posts.
  Add each new post to `sitemap.xml` (index priority 0.8, posts 0.6, lastmod = post date).

## Backdating decision
Launch posts are dated across the prior ~3 months (Apr–Jul 2026) at the user's
request, to present an active journal from day one.
**Why:** this is a display/content choice, fine for readers. Told the user plainly
that search engines record their own first-crawl date, so backdating does not
change how Google dates the content for ranking — it is cosmetic, not an SEO lever.

## Newest / featured post
The blog index (`blog.html`) features the single newest post in the `.blog-featured`
hero-overlap card; older posts fall into the `.rgrid` below. When adding a newer
post, move the prior featured post down into the grid and promote the new one.
The resources-page Journal grid holds 3 recent posts (swap the oldest when adding).

## Compliance guardrails (healthcare)
- Integrative-therapy posts (e.g. music) must frame everything as **comfort/quality
  of life, never treatment or cure** — include an explicit "not intended to diagnose,
  treat or cure" note, mirroring the site footer disclaimer.
- **Medicare accuracy:** do NOT claim hospice has "no copays." Accurate wording:
  covered in full with no deductible for the hospice benefit itself; possible small
  costs are up to ~$5 for some comfort meds and ~5% coinsurance on inpatient respite;
  Medi-Cal often makes it $0. Respite = up to 5 consecutive inpatient days.
  **Why:** an earlier draft's absolute "no deductibles and no copays" was inaccurate
  and a compliance risk; corrected in the myths post.
