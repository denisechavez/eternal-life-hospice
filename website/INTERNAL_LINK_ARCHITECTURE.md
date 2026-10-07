# Eternal Life Hospice internal-link architecture

## Purpose and topic owners

Help families find the next useful answer and reach care; help professionals reach
the referral form. Existing clinical copy, eligibility caveats, city neighbor
choices and shared navigation/footer design are not rewritten.

The authoritative curated relationships are in `content/internal-links.json`.
They are resolved by `internal_links.py` for authored pages, both publishing
generators and HTML responses. These are explicit page/topic relationships,
not automatic keyword substitutions.

| Topic / page family | Main destination | Supporting pages and return journey |
|---|---|---|
| Understanding hospice and eligibility | `/hospice-care` | When Is It Time, condition-focused Journal posts, evaluation guidance; return to care and practical family education |
| Clinical services | `/services` | Pain/symptom management, whole-person comfort, Sound Bath, end-of-life choices; return to services and coverage |
| Family education and caregiving | `/resources` | Family Guide, circle of support, presence, volunteers, caregiver and grief Journal articles |
| Medicare coverage | `/resources/medicare-hospice-benefit` | Coverage, equipment and benefit Journal articles; link to services and choosing care |
| Starting care | `/resources/first-48-hours` | Evaluation, discharge and first-days Journal articles; link to care, comfort and coverage |
| Choosing a provider | `/resources/how-to-choose-a-hospice` | Family Guide, choosing-care Journal posts; link to care and coverage |
| Whole-person comfort | `/resources/comfort-therapies` | Sound Bath, music and spiritual-care articles; return to services |
| Local coverage | `/hospice-ventura-and-los-angeles-county-ca` | All 145 currently published city/community guides, existing nearby neighbors and local Journal articles |
| Local Journal guidance | The corresponding city page where explicitly assigned | Thousand Oaks, Simi Valley, Camarillo and Moorpark mappings; broader regional content returns to the county owner |
| Journal discovery | `/blog` | Published campaign and legacy posts, topic-specific owner recommendations and Resources' latest three stories |
| Professional referrals | `/refer#referral-form` | Referral process articles, first-days and coverage guidance; Referral eCard stays professional |
| Care Brief | `/care-brief` | Only Issue One; separate identity from the Journal |

The JSON includes the per-page relationships, Journal category-to-topic choices,
explicit article-owner overrides, specialist support links and reasoned exceptions.
Legacy Journal stories without campaign records are family education unless an
explicit owner override assigns a narrower topic.

## Linking rules

- Use natural, descriptive anchors. Link an article to its topic owner; add only
  genuinely useful next answers. The curated group contains no more than five
  unique page destinations and does not link to itself.
- Preserve useful existing inline links and existing related-reading groups.
  Do not invent nearby communities, facilities, affiliations or service coverage.
- Use canonical root-relative page URLs, without `.html`, directory trailing
  slashes or historical aliases. Query strings and valid fragments are retained.
  Assets and downloads are not mistaken for page recommendations.
- Family Request Care: `/?lead=family#leadcap`. Provider action:
  `/refer#referral-form`. Calls remain `tel:` links. Employment, volunteering,
  newsletter and voice/session journeys retain their own routes.
- New resource/support pages require an explicit entry in `pages` and an incoming
  hub/content link. For a Journal article, select an existing mapped category and
  add `journalOwners` when a narrower service/resource/city page owns the topic.
- Unknown Journal categories use the documented family-education default;
  editors should assign an explicit owner for specialist or local topics.

## Public eligibility and timing

The corpus consists of actual HTML files whose canonical URL matches their route,
excluding redirect stubs, noindex content (except legal utilities), archived Journal
sources, business cards and pages without public canonical identity. Campaign dates
come from the same manifest used by the server. Publication uses the local
America/Los_Angeles date, including the existing `ELH_JOURNAL_DATE` test override.

Only published eligible articles can be recommended. Curated HTML slots are
refreshed at request time on authored pages, legacy posts and date-filtered archive
and Resources responses. HTML always revalidates; old source slots and conditional
requests cannot keep yesterday's recommendations or disclose tomorrow's story.
The serving path does not rely on a browser-side hide script or a nightly rebuild.

Staged article files can receive canonical links and owner journeys without being
eligible for incoming recommendations. Archived sources remain retained outside
the public corpus. Workspace drafts, review mockups and digital business cards
are never reading recommendations. Existing founder business-card discovery links
were redirected to the public founder biography.

## Controlled rollout report — 2026-10-07

The same **196-route corpus** and the same parser/method were used before and after.
Before HTML is read from the pre-rollout Git snapshot; after HTML uses the curated
date-filtered slots. Dated archive cards are interpreted at the report date in both.
Edges count unique source/destination pairs, not repeated link elements.

| Measure | Before | After |
|---|---:|---:|
| Main-content/hub-listing edges (breadcrumbs excluded) | 2,493 | 2,759 |
| Shared header/footer edges | 5,261 | 5,261 |
| All edges, including breadcrumb journeys | 6,199 | 6,204 |
| Content pages missing an incoming content link, excluding explicit exceptions | 1 | 0 |
| Routes reachable from home using content links only | 190 | 192 |
| Routes reachable using all links | 195 | 195 |
| Maximum content-only click depth | 4 | 3 |

The founder biography gained a genuine content incoming link. Care, resource,
service, city and Journal pages gained curated owner/next-answer journeys.
Relative and alias page anchors were canonicalized without replacing clinical
prose. Header/footer destinations and layouts remain unchanged apart from
canonicalizing destinations where necessary; their graph is identical.
The county hub already exposed every published city guide, so no new geography or
second directory was added.

Full per-route incoming content and chrome links, content/all click depth,
reachability, errors and graph edges are in:

- `reports/internal-links/before.json`
- `reports/internal-links/after.json`

### Deliberate exceptions

- `/` is the graph root.
- `/privacy-policy` and `/terms` are noindex legal utilities linked from the footer.
- `/sitemap` is a utility index, intentionally not recommended from family content.
- `/media-kit` is a press booklet, discoverable in shared resources navigation,
  not an indiscriminate family-reading recommendation.
- `/referral-card` is a professional QR/eCard utility; its specialist incoming
  connection is on Refer, not a family reading list.
- `/careers` retains the employment journey and Resources' existing incoming link.

Four routes are not content-reachable from home: the two legal utilities,
Sitemap and Media Kit. All except Sitemap are reachable through shared navigation.
None is silently excluded from the report. City pages are not exempt.

## Maintaining and validating

1. Edit the curated map or article source category/owner choice.
2. Generate city or Journal content from its existing authoritative source.
   Both generators apply curated slots and canonical anchor rules. Journal archive
   cards and their encoded featured payloads use root-relative URLs.
3. Run `python3 website/build-internal-links.py` after changes to authored
   pages or the city inventory. It updates only link slots and anchor destinations.
   The directory fallback adds only published inventory links if the county list
   is missing one; it does not alter county messaging.
4. Run `python3 website/check-internal-links.py`. It checks page targets,
   fragments, redirects, canonical content anchors, prohibited discovery,
   duplicate curated destinations, conversions and incoming content coverage.
   `--date YYYY-MM-DD` and `--report PATH` support controlled-date graph reports.
5. Run `bash website/test-predeploy-chain.sh` before publishing. The link checker
   and browser journey test both have required sentinels; an emptied check cannot
   silently pass.

The guard's known-bad fixtures cover relative/query/fragment resolution, broken
pages, missing fragments, aliases, `.html` targets, prohibited business cards/mockups,
chrome-only incoming links and wrong care destinations. Controlled-date cases
cover before/on publication, archived exclusions and replacing cached future slots.
Browser checks cover 390px and 1280px on care, Resources, a pilot city,
a legacy Journal post, Family Guide and Refer: readable responsive sections,
visible keyboard focus, Tab order and real Enter navigation. Existing mobile
header, footer, form, analytics, city, Journal and route-exposure checks remain
in the predeploy chain.

Bare `href="#"` cookie links with explicit click handlers are deliberate UI controls.
Breadcrumbs are checked for valid destinations/fragments but do not satisfy the
incoming main-content requirement. Telephone, email and external links are not
internal page graph edges.
