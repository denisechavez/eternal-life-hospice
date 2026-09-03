# SEO Strategy — Eternal Life Hospice

## Site overview
Static marketing website for Eternal Life Hospice, Inc., a Medicare-certified hospice serving Ventura and Los Angeles County, CA. Published through Replit Autoscale from `website/elh-preview/`. No JavaScript SPA — all pages are static HTML served directly.

## In scope
- Homepage (`index.html`) — primary referral-generation landing page
- Core public pages: `/refer`, `/careers`, `/family-guide`, `/resources`, `/volunteer`, `/sound-bath`, `/blog`, `/care-brief`
- Resource articles under `/resources/`
- Blog index and blog detail pages under `/blog/`
- 146 city/location pages (`/hospice-*-ca.html`) — programmatic local SEO
- County hub and regional hub pages
- Media Kit, referral eCard, and Care Brief pages for audit coverage, with exception status considered in prioritization

## Out of scope / exceptions
- Digital business cards (`/card-aleksandra-dubina`, `/card-denise-chavez`, `/aleksandradubina`) — not public marketing pages
- Internal social/asset working documents and agent/OpenAPI files — not normal public UI pages
- `privacy-policy.html`, `terms.html` — utility pages, low SEO priority
- `404.html` — error page
- `referral-card.html` — print/QR reference card; audit as an exception rather than a normal landing page
- `media-kit.html` — included in the current task but secondary priority as a press-kit page

## Target audience
1. **Physicians, hospital discharge planners, social workers, case managers** — primary referral sources
2. **Families** searching for hospice information for a loved one in Ventura or LA County
3. **Volunteers** and potential staff looking to join

## Primary keywords / topics
- "Hospice care [city] CA" — city-specific queries (146 city pages)
- "Hospice care Ventura County" / "Hospice care Los Angeles County"
- Condition-adjacent: Medicare hospice benefit, how to choose a hospice, when is it time for hospice
- Brand: Eternal Life Hospice, The Eternal Care Brief

## Primary conversion goal
Generate qualified hospice referrals that convert into admissions. Every page should answer: Why Eternal? Why now? What happens next? How do I refer?

## Crawler and AI assumptions
- Site is fully static HTML — all content visible to Googlebot and AI crawlers without JavaScript rendering
- HTTPS and the custom domain are managed by Replit Publishing
- www → non-www canonical is enforced at the domain/publishing layer
- `llms.txt` is present and the current source scan found links for all 146 city/location pages plus the principal public content routes; recheck when new pages are added
- No intentional AI crawler blocking in `robots.txt`; answer/search crawlers are allowed while training-only crawlers are separated according to current policy

## Dismissed categories
- HTTPS / SSL issues — handled by Replit Publishing
- JavaScript rendering issues — site is fully static HTML, not a SPA
- Missing favicon — confirmed custom branded favicon at `assets/favicon.png`
