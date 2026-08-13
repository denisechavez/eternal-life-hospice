---
name: elh-design-system
description: Complete Eternal Life Hospice brand and design system rules. Load this skill on ANY design, collateral, print, social, or web task for ELH — city pages, social graphics, print flyers, blog headers, email templates, rack cards, or any branded surface. Encodes palette, typography, logo lockup, The Five visual system, voice rules, and compliance constraints so they apply automatically without re-specification.
---

# ELH Design System — Eternal Life Hospice

> **Always load this skill first on any ELH design or collateral task.** It is the single source of truth for visual and voice decisions. Every surface must ladder back to it.

---

## 1. Brand Platform

**The Eternal Standard** — four pillars (canonical; do not use any other list):

| # | Pillar | What it means |
|---|--------|---------------|
| 01 | **Clinical Confidence** | The nurse who answers at 2 AM; evidence-based protocols; ACHC accreditation |
| 02 | **Guided Presence** | Being *with* families — the social worker, chaplain, coordinator who stays |
| 03 | **Whole-Person Comfort** | Full integrative program at no additional expense to families |
| 04 | **Compliance-Led Care** | Medicare-certified, CDPH-licensed, ACHC-accredited; decisions made within the rules |

**Taglines in active use:**
- *"Care That Honors Life"* (emotional — use on print, hero sections)
- *"We Are Here. Always."* (reassurance)
- *"Here in Moments That Matter Most"* (social/digital)
- *"The First 72 Hours"* (family/referral guide context)
- *"Compliance is patient protection"* (professional/referral audience)

**Three differentiators (travel on all collateral):**
Founder-led · Independent · Integrative (8 modalities)

**Eight integrative modalities:** music, massage, reiki, aromatherapy, pet, audiology, holistic medicine, doula

**The Eternal Difference (referral collateral bullet set):**
1. A full line of integrative services
2. Clinical & mobile services at no additional expense to families
3. Zero complaints in 11 years of care *(owner-substantiated — do not extend to new channels without confirmation)*

---

## 2. Brand Palette

### Canonical Hex Values (site + print confirmed identical)

| Name | Hex | Role |
|------|-----|------|
| **Deep Plum** | `#3C1C3B` | Primary backgrounds, print card backgrounds, darkest brand element |
| **Plum** | `#5B2E59` | Mid-tone accents, secondary backgrounds |
| **Accent Plum** | `#5C2474` | Used in digital/social contexts (equivalent to deep plum at screen gamma) |
| **Light Plum** | `#7A3B8E` | Mid-tones, pill tags, table headers in digital docs |
| **Gold** | `#C9B07E` | Headlines, borders, decorative elements, warmth; never used as background behind body text |
| **Cream** | `#F5F0EB` | Body text on dark backgrounds; light page backgrounds |
| **Stone** | `#7A7068` | Neutral mid-tone for secondary text, metadata |
| **Dark Text** | `#1a0a18` | Primary body text on light backgrounds |

### Print CMYK (verified round-trips)
- Deep Plum `#3C1C3B` → CMYK verified via Ghostscript; round-trips exactly
- Always use `-dDownsample*=false -dAutoFilter*=false -dColorImageFilter=/FlateEncode` in Ghostscript or it silently drops image resolution

### Usage constraints
- Never use Gold as a background behind body text — it is a decorative/headline color only
- Deep Plum + Cream + Gold is the flagship dark colorway (print front covers, hero backgrounds)
- Cream background + Plum type is the flagship light colorway (print backs, body pages)
- Never place gradient marks on dark/plum backgrounds — cream infinity mark only on plum; gradient mark only on light/cream backgrounds

---

## 3. Typography

### Typefaces
| Family | Role | Source |
|--------|------|--------|
| **Fraunces** (serif) | Headlines, pull quotes, brand voice; the "voice" | Google Fonts (free) |
| **Jost** (sans-serif) | Body text, labels, navigation, data, eyebrows | Google Fonts (free) |

### Key weights in use
- Fraunces 300 (light) — large display headlines
- Fraunces 400 — section headers
- Fraunces 600 — emphasis in display
- Jost 300 — body text
- Jost 400/500 — navigation, labels
- Jost 600 — eyebrow caps, table headers

### Critical print wordmark spec (LOCKED)
The "Eternal" wordmark in the logo lockup must use:
- **Font:** Fraunces
- **Weight:** 455
- **`font-variation-settings: 'opsz' 58`** at 30pt display
- Chromium does NOT auto-apply optical sizing — this must be set explicitly
- Default weight 480 / auto opsz renders visibly chunkier than the brand master
- Verified width/height ratio of master wordmark = 4.335; this setting renders 4.25–4.31 (closest match)

### Eyebrow / label style
- Jost, 7.5–8.5pt, weight 400–500
- Letter-spacing: 0.2–0.28em
- ALL CAPS
- Color: Gold `#C9B07E` on dark backgrounds; Light Plum `#7A3B8E` on light backgrounds

---

## 4. Logo Lockup Rules

### Official proportions (LOCKED — never wider)
1. **Infinity mark** (cream hi-res PNG on plum; gradient mark on light backgrounds)
2. **"Eternal"** — Fraunces 30pt cream, weight 455, opsz 58
3. **"LIFE HOSPICE"** — Jost 600, 8.2pt, letters justified across **73% of "Eternal"'s width**, centered

**Symbol proportion rule:** symbol = 85% of "Eternal" width; "LIFE HOSPICE" = 73% of "Eternal" — NEVER wider

### Colorway constraints
- On plum/dark backgrounds: cream infinity mark (`brand-assets/Medical/eternal-life-hospice-infinity-cream-hires.png`, 1111×490)
- On light/cream backgrounds: gradient mark
- Source master: `brand-assets/Medical/eternal-life-hospice-logo-cream-gold-subtitle.png`

### Founder portrait rule (Three Rules)
- Portrait must be small, contextual, never > 2.5in on print
- Never lead with founder's face on brand surfaces (depresses acquisition valuation)
- In the field she is the face; on brand surfaces she is the voice
- Title is always two lines: **Founder & CEO** / **Certified Hospice Administrator**

---

## 5. The Five Visual System

Five AI-generated images + labels forming the ELH Care Brief content system.

### The Five Elements

| Image file | Label | Subject | Notes |
|------------|-------|---------|-------|
| `elh-amethyst.png` | **The Stone** | Raw amethyst geode, violet crystal | Grounding. What doesn't move. |
| `elh-bowl.png` | **The Energy** | Bronze singing bowl on cream linen | Vibration. Resonance long after it stops. |
| `elh-pen.png` | **The Word** | Gold-nib pen on handwritten script | The care plan. The note. The call returned. |
| `elh-eye.png` | **The Touch** | Macro amber iris, warm catchlight | Being looked at and not looked away from. |
| `elh-stillness.png` | **Stillness.** | Single candle in absolute darkness | A state, not a thing. Arrives last. |

**CRITICAL NAMING RULE:** The first four carry "The" — they are acts/objects/forces. **Stillness has NO "The"** — it is a state. Never add "The" to Stillness. This is intentional and must never be "corrected."

Canonical sequence: *The Stone · The Energy · The Word · The Touch · Stillness.*

All source files: `website/elh-preview/assets/social/` (not published to live site)

### Mosaic Progression — Care Brief Schedule

| Care Brief Month | Layout | What appears |
|-----------------|--------|--------------|
| Month 1 | Single image, full frame | The Stone alone |
| Month 3 | Two images, gold seam | + The Energy |
| Month 5 | Three images, asymmetric | + The Word (Stone tall-left, Energy+Word stacked right) |
| Month 7 | 2×2 grid, gold crosshair + diamond | + The Touch (all four) |
| Month 9 | 2×2 + wide bottom strip | + Stillness (candle spans full width below the four) |

### Extended uses for The Five
- Caption openers (e.g., *"The Stone. Some things hold."*)
- Reel end cards (white text on deep plum, one phrase centered)
- Care Brief section headers
- Story frames (one word/phrase per frame, 5-frame sequence)
- Website section dividers (italic Fraunces, gold rule beneath)
- Pull quotes (e.g., *"The Touch is not always a hand."*)

---

## 6. Photo Standards

### The Five-Filter Test (every photo must pass all five)
1. **Safe** — feels like someone knows what they're doing and won't leave
2. **Protected** — clinical confidence; steady, not cold
3. **Loved** — not professionally served; actually known
4. **Premium** — quality worthy of trust at the most significant moment
5. **Relatable** — real, not staged, not stock

If a photo fails any one filter: do not use it.

### Four Color Treatments for Photography

| Treatment | What it is | Best for |
|-----------|-----------|---------|
| **The Duotone** | Photo in two brand colors — shadows → deep plum; highlights → gold or cream | Faces, hands, amethyst |
| **The Color Wash** | Semi-transparent brand color at 20–40% opacity over photo | Hero images, carousel backgrounds |
| **The Graphic Pop** | Natural photo + brand-colored elements: gold underline, plum block, cream panel | Quote cards, carousel slides |
| **The Split** | Half = natural photo; half = solid brand color. Subject in photo half, text in color half | LinkedIn carousels, Pinterest pins |

### B&W photography — use sparingly
**Works for:** faces (honest, unmediated), hands (oldest visual language of care), amethyst in high contrast, quiet aftermath (empty chair, folded blanket)

**Does NOT work for:** comfort therapy images (music, pet, singing bowl — their warmth is the point), nature imagery (golden hour reads as peace; B&W makes it absence), any welcoming/inviting image

**Instagram feed rhythm (every 9):** Warm · Warm · Text-on-plum · Warm · **B&W** · Warm · Close-up · Warm · **B&W** → repeat

---

## 7. Brand Voice Rules

### The register
Calm, refined, clinically credible, warm without sentimentality. Premium/warm/organic — luxury *felt*, never *claimed*. Peers use scale-and-protocol language; Eternal uses presence-and-attention language.

### Show, don't claim
Write this: *"When a family calls at 2 in the morning, a nurse answers. Not a service. A person who can assess and act. Right then."*

Not this: *"We provide compassionate care."*

The test: if the sentence could appear on any healthcare organization's website in America — rewrite it until it couldn't.

### Institutional framing (always)
- ✅ "At Eternal Life Hospice, we…"
- ✅ "Here is what our team does…"
- ✅ "She has been in hospice for eleven years. She could have practiced anywhere. She stayed."
- ❌ "I started this because…" (use sparingly)
- ❌ "My team…" (use "our team")
- ❌ "When I…" (minimize first-person singular)

### Narration voice (video/audio)
- **Pace:** slower than feels natural; let sentences breathe
- **Tone:** warm, measured, authoritative — not clinical, not corporate
- **No filler:** no "um," no "so," no "you know"
- **The pause:** 1 second after key statements
- **Emotional register:** calm grief is welcome; sentimentality is not; this is sacred work, not sad work

### Who is on camera

| Person | On camera? |
|--------|-----------|
| Registered Nurse | ✅ Safe |
| Social Worker | ✅ Safe |
| Chaplain | ✅ Safe |
| Hospice Aide | ✅ Safe |
| Music Therapist | ✅ Safe |
| End-of-Life Doula | ✅ Safe |
| Volunteer | ✅ Safe |
| **Founder (Aleksandra)** | **Voiceover only — not on screen** |

The team is the face of the care. The founder is the voice of the standard.

---

## 8. Banned Words and Phrases

These are overused in hospice marketing until they mean nothing. Never use:

| Banned | Why | Replace with |
|--------|-----|--------------|
| Compassionate / compassion | Every hospice uses it | Show the 2 AM nurse answering; show the handwritten note |
| Caring / caring team | Circular | Describe the specific act, the consistency, the presence |
| Passionate | Applies equally to hospice and pizza | Name what drives the specific person — what they came from, what they stayed for |
| Holistic approach | Medical jargon co-opted by marketing | Name the specific therapies: "Music therapy. Massage. Reiki. Aromatherapy." |
| Journey | "Your journey." Hollow. | Name the actual thing: the season, the passage, the final chapter. Or simply: *this.* |
| Dignity (as a claim) | Everyone says this | Show the aide who knows exactly how a patient likes their hair |
| Seamless | Corporate | Describe what actually happens: same-day admission, one phone call |
| World-class | Claim without evidence | Name the credential (ACHC), the specific service, the specific outcome |
| Loved ones | Hollow across all of hospice | The family. The daughter. The husband. The people in that room. |

---

## 9. Compliance Hard Rules

Apply to ALL content — social, print, web, email.

| Rule | Constraint |
|------|-----------|
| **No medical-efficacy claims for integrative therapies** | Never say music therapy "treats" or "heals." Say it provides comfort or is offered as part of whole-person care. These are NOT covered by Medicare as a core benefit — Eternal pays for them. |
| **Cost wording** | Say "at no additional expense to families" or "at no additional cost to families." Never "free." Leave core-benefit and clinical-services cost wording intact. |
| **No Medicare "no copay" claim** | Say "covered under the Medicare Hospice Benefit" or "no out-of-pocket cost for eligible patients." Never "free" or "no cost" without qualification. |
| **Only held credentials** | List only: Medicare-Certified · CDPH-Licensed · ACHC-Accredited. Do not list association memberships not currently held. |
| **No inducements in referral content** | Highlight quality of care — never offer gifts, incentives, or payment themes near referral content (Anti-Kickback / Stark). |
| **Geographic scope** | Ventura County + Los Angeles County only. Never imply broader geographic coverage. |
| **End of Life Option Act** | In service inventory — use only with careful, legally-reviewed positioning; never lead with it. |
| **Third-party logos** | Partner logos on print collateral = nominative use only. Only print if ELH actively uses the platform. Anti-Kickback / false-affiliation applies. |

---

## 10. Print Production Rules

### Standard rack card spec (referral card format)
- **Trim:** 3.5×7.75 in (or MOO: 3.67×8.5 in)
- **Bleed file:** 3.75×8 in (0.125 in bleed) / MOO bleed: 3.83×8.66 in
- **Crop marks:** in sheet coordinates, NOT bleed-local coordinates
- **Image resolution:** all embedded images ≥ 750 dpi in the CMYK file
- **Type:** all vector (embedded CID TrueType / Type 3 outlines) — never rasterized text
- **Ghostscript CMYK conversion:** always include `-dDownsample*=false -dAutoFilter*=false -dColorImageFilter=/FlateEncode`

### Credential display (as of July 2026)
Front band: **CREDENTIALS & CERTIFICATIONS** label + CMS · CDPH · ACHC logos (Epic removed)
Footer bar text: **MEDICARE-CERTIFIED · CDPH-LICENSED · ACHC-ACCREDITED**

### Print colorway
- Card front: Deep Plum background, Cream and Gold type
- Card back: Cream background, Plum and Gold type
- QR codes: decode to `https://eternallifehospice.com/refer`; infinity mark badge centered

---

## 11. Social Production Format

### Platform format summary

| Platform | Format | Audience |
|----------|--------|---------|
| TikTok / Reels | Voiceover + stills + text overlay | Families, general public |
| YouTube | Voiceover + stills OR team on camera | Families + professionals |
| LinkedIn | Written posts + document carousels | Healthcare professionals, referral sources |
| Instagram Feed | Curated photo + graphic + text posts | Families, community |
| Instagram Stories | Brand templates + behind-the-scenes | Existing followers |
| Facebook | Warm written posts + comfort imagery | Families, community |
| Pinterest | Tall pins (2:3), editorial, warm | Families researching, caregivers |
| Google Business Profile | Short posts 2–3× per week | Local search traffic |

### Production format rule
**Voice + still image overlays.** Narration recorded by the founder (or a voiceover artist). CapCut (or equivalent) layers it over still images, brand graphics, and text overlays. No talking head. No founder's face. The result feels like premium documentary — not a personal vlog.

---

## 12. Organization Facts (always use these exactly)

- **Full legal name:** Eternal Life Hospice, Inc.
- **Address:** 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362
- **Phone:** 805.953.7273
- **Fax:** 805.953.8530
- **Referral email:** referral@eternallifehospice.com
- **General email:** info@eternallifehospice.com
- **Website:** eternallifehospice.com (canonical domain; do not use eternalhospice.com or eternallifehospiceinc.com)
- **Service area:** Ventura County and Los Angeles County, California
- **Certifications:** Medicare-Certified · CDPH-Licensed · ACHC-Accredited
- **Referral line:** 24/7 answered by a hospice nurse
- **Founder:** Aleksandra — title = **Founder & CEO / Certified Hospice Administrator** (two lines)
- **Experience:** 11+ years hospice experience, 20+ years in healthcare

---

## 13. Asset Locations

| Asset | Path |
|-------|------|
| Cream infinity mark (hi-res, for plum BG) | `brand-assets/Medical/eternal-life-hospice-infinity-cream-hires.png` |
| Logo master (cream+gold+subtitle) | `brand-assets/Medical/eternal-life-hospice-logo-cream-gold-subtitle.png` |
| Partner/affiliate logos | `brand-assets/ELH-affiliates-and-partners/` |
| The Five source images | `website/elh-preview/assets/social/` |
| Social brand brief (HTML reference) | `website/elh-preview/assets/social/elh-social-brand-brief.html` |
| Print exports | `exports/print/` (RGB) and `exports/print/print-ready-cmyk/` (CMYK) |
| Referral card build script | `scripts/build-referral-card5-print.py` |

---

## Quick-reference design decisions

- **Logo lockup:** cream mark on plum; gradient mark on light BG — never swap these
- **Wordmark "Eternal":** Fraunces weight 455, opsz 58 at 30pt — explicit setting required in Chromium
- **"LIFE HOSPICE" width:** always 73% of "Eternal" width — never wider
- **Stillness:** never "The Stillness" — the absence of "The" is the entire point
- **Founder face:** voiceover only on brand surfaces
- **Integrative therapy cost wording:** "at no additional expense to families" — never "free"
- **Banned credentials:** only Medicare-Certified, CDPH-Licensed, ACHC-Accredited (no association badges)
