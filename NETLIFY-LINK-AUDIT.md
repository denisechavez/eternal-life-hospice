# Old Netlify Hostname Link Audit

**Checked:** 2026-09-01  
**Hostname audited:** `https://eternallifehospice.netlify.app`  
**Canonical destination:** `https://eternallifehospice.com`

## Result

The tracked website source and scanned exported collateral contain no active
user-facing link to the old Netlify hostname, so no repository replacement was
required. This does **not** prove that external account settings, distributed
materials, or staff devices are clear; those surfaces remain unverified and must
be checked before the old deployment is retired.

The old hostname remains only in historical evidence and internal operational
materials that need to identify the deployment being retired. Those references
are listed below and are intentionally retained.

## Surface checks

| Surface | Evidence checked | Result |
|---|---|---|
| Website source | `website/elh-preview/` HTML, assets, scripts, and metadata | **Clear in repository.** No old Netlify hostname in user-facing markup or page assets. Canonical absolute URLs use `eternallifehospice.com`. |
| Email signatures | The three HTML signature files, `email-signature-HOW-TO.txt`, and `exports/email/email-signatures.zip` | **Clear in repository.** Website and logo URLs use the canonical domain. Active Gmail/Outlook/Apple Mail signature settings outside these files remain unverified. |
| QR codes | Current website QR masters and QR generator scripts | **Clear for current repository masters.** Payloads decode to the canonical homepage, `/refer`, or `/media-kit` paths. QR materials already printed or distributed in the field remain unverified. |
| Printed collateral | Exported print PDFs and representative rendered pages | **Clear for scanned marketing collateral.** Referral cards, business cards, press-kit pieces, and the Family Guide use the canonical domain. The cutover workbook is an internal operational exception listed below. Physical distribution and older untracked print runs remain unverified. |
| Social profiles/content | Social content kits, social preview/share markup, and public exact-hostname search | **Clear in repository/public search only.** Draft CTAs and share URLs use the canonical domain; no public search result exposed the old Netlify hostname. Active profile bio/link fields require owner login and remain unverified. |
| Google Business Profile | Site organization markup/footer links and canonical listing record | **Clear in code only.** Links use the canonical CID listing, not the old Netlify host. The GBP dashboard website field and scheduled post links were not directly inspected and remain unverified. |
| Ads | Repository ad creative and campaign-related source | **No old-host match in repository.** The local referral ad creative contains no visible URL. Ad-platform destination settings require account access and remain unverified. |
| Partner/directories | Repository partner/listing references and public search | **No old-host match in repository/public search.** Some external directories still expose the separately tracked `eternalhospice.com` legacy domain; that is not the Netlify hostname and remains an external citation-cleanup item. External listing fields remain unverified. |
| Staff bookmarks | Repository/browser-export search | **No repository bookmark export available.** Staff browser bookmarks require a manual check on each managed device/account and remain unverified. |

## Intentionally retained operational references

These are not links shipped to families or referral sources. They identify the
old deployment so the team can verify, freeze, redirect, or preserve it safely:

| Reference | Why it remains |
|---|---|
| `HOSTING-SPLIT-INVESTIGATION.md` | Historical host comparison and deployment evidence. |
| `FORM-SUBMISSION-ROUTING-VERIFICATION.md` | Historical evidence that the Netlify copy and Replit form processor differ. |
| `exports/print/elh-replit-netlify-cutover-checklist.pdf` | Internal go/no-go workbook; its old-host checks must name the site being tested. |
| `website/elh-preview/_redirects` | Netlify-only DNS/CNAME instruction comment and deployment configuration. It is not rendered as site content. |
| `.local/tasks/` task notes and `.agents/memory/` hosting notes | Internal planning and durable hosting context. |

Do not delete or rewrite these references as part of a user-facing link cleanup;
update them only when the corresponding Netlify freeze/retirement operation is
approved and complete.

## Follow-up checks requiring account access

This audit cannot authorize retirement until an owner verifies:

1. Website URLs in Instagram, Facebook, LinkedIn, YouTube, and any other active
   profile bios.
2. The Google Business Profile website field and any scheduled GBP posts.
3. Active Google/social ad destination URLs and URL parameters.
4. Partner, referral-network, and directory listing website fields.
5. Staff browser bookmarks, QR codes already distributed in the field, and any
   saved email templates outside `exports/email/`.

These are account/device checks, not repository changes. The canonical target for
any replacement is the matching path on `https://eternallifehospice.com`.