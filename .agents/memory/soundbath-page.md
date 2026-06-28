---
name: Sound Bath page
description: How the dedicated sound-bath.html page is built and the compliance framing that keeps it from being flagged.
---

# Sound Bath page (sound-bath.html → clean URL /sound-bath)

Dedicated, self-contained page for the integrative Sound Bath offering. Links in from the
signature-features band on every city page and a "Visit the Sound Bath page" link in the
home-page modalities card.

## Audio is synthesized, not files
- No mp3s. The 3 "journeys" are generated live via Web Audio API. The engine (sbCtx, mkDrone,
  mkBin, mkStrike, SB_TRACKS[3], window.toggleSound, progress/timer) is duplicated from
  index.html into an inline `<script>` on sound-bath.html. Player markup uses ids
  playerEl-0..2 / btn- / prog- / timer-. Previews are 30s (DUR=30).
- **If the engine changes, update BOTH index.html and sound-bath.html** — they are independent copies.
- Player CSS (.players/.player/.fpill/.progress-track etc.) is inline in index.html lines ~368-392
  and was copied inline into sound-bath.html (NOT in elh.css). Same for the page's own .sb-* CSS.

## Compliance framing (the reason this page is "handle with care")
**Why:** It's a complementary comfort offering at an end-of-life hospice; medical-efficacy claims
risk being flagged. User is SEO-savvy and explicitly wants no claims, Medicare-not-covered stated,
and nothing flaggable.
**How to apply — keep these rules on this page and the home modalities card:**
- No efficacy verbs: never "pain relief", "healing frequencies", "treats/relieves/reduces/cures".
  Frequency pill labels describe tones, attributed to "the sound-healing tradition", not effects
  (e.g. "174 Hz — grounding", "963 Hz — openness"). The old home pill "174 Hz — pain relief" was
  softened to "grounding".
- Benefits are framed as experiential family reports ("families tell us the room felt calmer"),
  always paired with "not a treatment for any condition" / "everyone responds differently".
- A prominent `.sb-note` disclaimer states: complementary comfort, not medical care, not intended
  to diagnose/treat/cure/prevent, never a substitute for medical care, and **not covered by the
  Medicare hospice benefit** (offered at no additional cost).
- JSON-LD uses WebPage + BreadcrumbList only — deliberately NOT MedicalProcedure/Therapy, so the
  page does not assert a medical service.

## "Open to a calming sound" — entry orb, not autoplay
**Why:** Browsers block audio on load (AudioContext starts suspended; needs a user gesture), so true
autoplay is silently blocked.
**How to apply:** The hero shows a `.sb-veil` overlay with a glowing `.sb-orb` ("Press for a moment of
calm") + a "Continue without sound" skip. Clicking the orb resumes the ctx, starts a continuous, low-gain
ambient soundscape (startAmbient: soft drones 110/164.81/220 + slow binaural, NO timeout strikes, no DUR
stop) and fades the veil. A fixed bottom-left `.sb-soundtoggle` ("Play calm"/"Sound on") toggles ambient
anytime (bottom-LEFT to avoid the bottom-right chat bubble). Starting any 30s journey calls stopAmbient()
so they never overlap.

## Note on benign matches
A site-wide grep for "cure" legitimately hits the required negative disclaimer
("diagnose, treat, cure or prevent") and standard hospice phrasing ("from cure to comfort") — those
are fine, not claims. The risky strings to keep at zero are: "healing frequencies", "pain relief".
