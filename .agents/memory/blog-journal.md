---
name: Journal (blog)
description: How the ELH "Eternal Journal" blog is structured, its conventions, and the backdating/compliance decisions behind it.
---

# The Eternal Journal (blog)

The site's approved public display name is **"The Eternal Journal/Blog"**.
Keep the URL root **/blog** and existing article URLs unchanged.

**Why:** The owner explicitly confirmed this exact replacement name. It remains
separate from The Eternal Care Brief.

**How to apply:** Use the complete display name in public navigation, headings,
footers and metadata. Preserve existing approval snapshots; refresh shared
branding at response time rather than invalidating signed articles.

Index = `blog.html` (root-level, inline-free — links the shared
`assets/elh.css`). Posts live in `blog/<slug>.html` and use the **same template
convention as `resources/` sub-pages**: `../assets/...` + `../<page>` relative
paths, `.article/.lede/.ask/.note-panel/.kicker/.cta/.related/.rgrid/.rc` classes,
header/footer extracted byte-exact from a resources sub-page (root pages derive
theirs via `.replace("../","")`).

## Publication boundary: Journal vs. Care Brief

The **Eternal Journal** and **The Eternal Care Brief** are separate publications
and must never share identity, cadence, attribution, or template labels:

- **Eternal Journal:** the website blog, with its own editorial schedule.
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
The resources-page Journal grid holds 3 recent published posts. Treat the archive
as its editorial source rather than maintaining a second hand-picked list.
**Why:** Separate selections drift behind the publishing schedule and create
another place where future stories could be promoted too early.
**How to apply:** Keep Resources aligned with published archive content and leave
the separate Care Brief publication card outside the Journal selection.

For date-scheduled Journal campaigns, "newest" means the latest article actually
published as of the local publication date, not the last article pre-rendered
for the campaign. Keep the archive's featured treatment and its regular cards
in sync as scheduled articles become public.
**Why:** A pre-rendered featured card can remain stuck on an older article or
point to a future article while later articles are already available.
**How to apply:** When changing the Journal generator or publication gate,
verify the featured article on dates before, during and after the scheduled
campaign; the featured article should occur only once on the archive.

For image-only Journal updates, preserve the existing editorial HTML rather
than fully rebuilding posts from campaign JSON. Each published Journal story
should also have its own actual photo, including legacy stories.
**Why:** Some live article copy and links were refined after initial generation;
a full rebuild silently replaces those edits, while recycled photos make the
Journal look repetitive.
**How to apply:** Use the image-only campaign refresh for photo changes, check
article hero/share metadata and archive cards together, and reject duplicate
images across published stories.

Every new Journal image must be a photograph or convincing photoreal image
without an AI-looking appearance. Prefer licensed real photographs. Distinct
image filenames are not enough: adjacent Journal cards must also feel
visually different. Review the archive as a contact sheet and vary subjects,
settings and composition rather than filling a run of posts with similar
bedrooms, bedside hands or consultation scenes.
**Why:** The user identified visually repeated imagery as unacceptable even
when every article technically had a different image file, and explicitly asked
for unique photographic or photoreal imagery that does not look like AI.
**How to apply:** Review new images beside their archive neighbors before
publishing; choose article-specific scenes and preserve the calm, credible
healthcare tone without implying a depicted person is an actual patient. Inspect
the actual image and its license, not just search metadata: a matching result
can be a postcard, photographed artwork or a different place mentioned in an itinerary.

## Editorial positioning

Mix national family questions and narrow local topics, vary article length and
writing structure, and use contextual internal links throughout. Foreground
sound bathing and end-of-life/death doula support where relevant while explaining
that personalization begins with listening from the first call.
**Why:** The user explicitly describes Eternal as personalized from the first
call and wants these integrative offerings prominent in the Journal, reflecting
families' questions rather than repeated city-name versions of service copy.
**How to apply:** Keep each article focused on a distinct practical question.
Do not turn these business priorities into unsupported claims about societal
trends, clinical efficacy or guaranteed service availability.

## Published summary authority

Use the visible hero heading and summary as the authority for archive copy once
a Journal page exists. Keep scheduling and archival decisions editorial-source
controlled. Do not infer a summary from the lede or SEO metadata when the hero
is missing or ambiguous.
**Why:** Published articles have editorial refinements that intentionally differ
from the original campaign copy; treating that copy as authoritative reverses
those refinements on archive cards.
**How to apply:** Sync archive copy after page edits without rewriting the article.
Article-level search/social metadata remains a separate editorial responsibility.

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
