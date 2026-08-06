# Eternal Life Hospice — Agent Guide

## What this site is
Eternal Life Hospice (eternallifehospice.com) is a **static informational website** for a Medicare-certified, CDPH-licensed, ACHC-accredited hospice provider serving Ventura and Los Angeles Counties in California.

The site is pre-rendered HTML with no REST or GraphQL interface. Contact and referral forms submit to Netlify Forms. One live programmatic endpoint is available for agent use — see **Live endpoints** below.

## Who it serves
- Families and patients considering or beginning hospice care
- Referring physicians, discharge planners, hospital social workers, and skilled nursing facilities
- Prospective clinical and support staff

## Live endpoints

### Coverage lookup
Check whether ELH serves a specific city — returns structured JSON, no auth required.

```
GET https://eternallifehospice.com/.netlify/functions/coverage?city=Pasadena
```

**Served city response:**
```json
{
  "served": true,
  "city": "Pasadena",
  "county": "Los Angeles County",
  "subregion": "San Gabriel Valley and nearby communities",
  "pageUrl": "https://eternallifehospice.com/hospice-pasadena-ca",
  "phone": "805.953.7273"
}
```

**Unknown city response:**
```json
{
  "served": false,
  "city": "San Francisco",
  "message": "Eternal Life Hospice does not have a published service-area page for \u201cSan Francisco\u201d. Please call 805.953.7273 to confirm coverage..."
}
```

- Matching is case-insensitive and diacritic-tolerant (`La Canada` → `La Cañada Flintridge`)
- A `served: false` response does not mean the city is definitively unserved — callers should direct to the phone number for confirmation
- Full OpenAPI spec: `https://eternallifehospice.com/.well-known/openapi.json`

## How to connect
- Phone (24/7): 805.953.7273
- Referral form: https://eternallifehospice.com/refer
- General inquiry form: https://eternallifehospice.com/#leadcap

## Key pages
- Coverage area: https://eternallifehospice.com/hospice-ventura-and-los-angeles-county-ca
- Resources for families: https://eternallifehospice.com/resources
- Care Kit: https://eternallifehospice.com/media-kit
- Journal (blog): https://eternallifehospice.com/blog
- Referral: https://eternallifehospice.com/refer

## Structured data
JSON-LD structured data (LocalBusiness, FAQPage, WebSite schema) is present on the homepage and key landing pages.
Sitemap: https://eternallifehospice.com/sitemap.xml
llms.txt: https://eternallifehospice.com/llms.txt

## Crawl policy
Search and answer assistants: allowed.
Training data collection: not permitted (see robots.txt).
