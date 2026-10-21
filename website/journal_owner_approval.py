"""Version-pinned owner instructions; not a login or general approval bypass.

The project owner explicitly requested approval/publication of the October 15
Journal post while Studio sign-in was unavailable. Do not add other articles
without a separate explicit request. This runs only on an approved publication,
records its actual source and freezes the exact reviewed content and imagery.
The owner's subsequent "post it now" instruction authorizes immediate release
of this one version. Every other article keeps its existing schedule.

On 2026-10-21 the owner separately authorized reconciliation through October 31.
That bounded set is pinned below and retains the regular 6:30 a.m. schedule.
"""
import journal_release as journal

REQUEST = {
    "slug": "when-a-parent-refuses-hospice",
    "date": "2026-10-15",
    "revision": "5b39a6afbd08264218de419d3960c9b5cc88cb9fe27db6f989eec765839e5153",
    "reviewer": "Owner request — October 15, 2026 (outside Studio)",
}

# Explicit October reconciliation requested on 2026-10-21. These exact versions
# are authorized outside Studio, not attributed to an authenticated reviewer.
# Changes to text or image bytes invalidate the pin. Never extend automatically.
OCTOBER_REQUESTS = (
    ("2026-10-10", "what-medical-equipment-can-hospice-provide", "418456b211a209285305b84969abd6c6840f8f80bfb5fb9419b55f43c93b2dfb"),
    ("2026-10-11", "what-24-7-on-call-hospice-support-means", "ef367a1ec85bb6efee4e33975060c7e6af63b717bf6a46099d5727810c0b3529"),
    ("2026-10-12", "what-is-hospice-respite-care", "e4b50b4d17eb5a84b8ce8475264af69a4fe0015cd8d98ae849d78f62572191a3"),
    ("2026-10-13", "how-a-hospice-social-worker-supports-the-family", "2c908d6fbaa3763fc8e901a378e41aec63aeb2c37133c687b0e9350541a93c5c"),
    ("2026-10-14", "spiritual-care-in-hospice-support-without-pressure", "4b211d826f62ac76e8e8d7b48c977188f5f67551ab485a7617b2f3b7bc5438da"),
    ("2026-10-16", "how-to-choose-a-hospice-provider", "927c8f53d52e51d17b33db71e66c2ff9407e4dc1d1c684b02bb300541f715818"),
    ("2026-10-17", "questions-to-ask-a-doctor-about-hospice", "29c7645db198017a08e156312367daa924995cb4b465fb3a75edb3f68f68d4a9"),
    ("2026-10-18", "eating-and-drinking-changes-near-the-end-of-life", "f05f9225fec4db11c4431fd126c200c496725710118f8c2122fa11c484ddab5b"),
    ("2026-10-19", "grief-support-before-and-after-a-loss", "6d48c6f53eba9419a3f933fd95cd51a739df969782921c4e3de36aa7a0f31569"),
    ("2026-10-20", "how-physicians-and-facilities-refer-a-patient-to-hospice", "b8b53ebbec86255be8895b6e1f3347ff013cb373197ca314f3743fc8ba8c65d5"),
    ("2026-10-21", "preparing-for-a-hospice-care-plan-conversation", "f726c2a6b6b1745528858785bbc300041ae677fbcf1c1e1c87ef7f298702cbeb"),
    ("2026-10-22", "before-the-first-hospice-visit-share-the-person-not-just-the-diagnosis", "25a13b7308e7199a0e7dd9e3fe87c9469f49ce2843400e2d3a4f6d99b1073c20"),
    ("2026-10-23", "a-death-doula-and-a-hospice-nurse-different-roles-shared-support", "e623e88f7f645092ed2de36ce88504578e067389cafcbf54dc453ec9ca2bf23b"),
    ("2026-10-24", "thousand-oaks-families-coordinating-care-when-relatives-live-far-away", "58b41d50441b10b8e00c480659bd16dc2e481987e561c582a0e4c361942cc5bc"),
    ("2026-10-25", "what-to-ask-before-trying-a-sound-bath-during-hospice-care", "a7d2fb5cc2b3c027da0ffaaf11fae678aec48fdbf8585331f3aba646efd5b7e7"),
    ("2026-10-26", "hospice-and-home-health-which-questions-clarify-the-difference", "e77a2074ae86848d0537d298d15a8fc665c8bd05381a49cf27d7dd946250f8a3"),
    ("2026-10-27", "westlake-village-who-will-be-home-between-hospice-visits", "0b5fb43baf416921d79591cbc4b92c0fa6f12d9fa43858fb63e838468554dc4c"),
    ("2026-10-28", "the-hospice-election-statement-read-it-as-a-conversation", "572a9c99aba57fe2ca106b27516f3331f1e8c0da57187e3993ba1c28e9402e4b"),
    ("2026-10-29", "personalized-comfort-starts-with-permission", "b5d2e3914021040444bf25a556d22aaee8794c74036ac878c8c3222cd34ac703"),
    ("2026-10-30", "calabasas-plan-a-calm-handoff-between-home-and-assisted-living", "7c01187408b5d19a743c8c0a6ee4e9d848f01c031ce1144f16cfd42accc9ff01"),
    ("2026-10-31", "keeping-ordinary-traditions-during-hospice-care", "753c1e7553b5e6f8beebf21f8b093add4b32115096d7110c626e3375ce42a0bb"),
)


def apply_october():
    """Apply once per undecided URL on publication, retaining the normal clock."""
    if journal.environment() != "production":
        return 0
    applied = 0
    for day, slug, revision in OCTOBER_REQUESTS:
        try:
            saved = journal.decide(
                slug, revision, "approve",
                "Owner-directed October reconciliation — 2026-10-21 (outside Studio)",
                only_if_undecided=True, expected_date=day)
        except ValueError:
            print(f"October reconciliation skipped changed article: {slug}")
            continue
        applied += bool(saved)
    print(f"October reconciliation: {applied} newly saved approvals; existing decisions preserved.")
    return applied


def apply():
    if journal.environment() != "production":
        return False
    try:
        applied = journal.decide(
            REQUEST["slug"], REQUEST["revision"], "approve", REQUEST["reviewer"],
            only_if_undecided=True, expected_date=REQUEST["date"], release_immediately=True)
    except ValueError:
        # A later editorial change is not authorized by this request. Keep the
        # site available but never approve different bytes automatically.
        print("Owner-requested October 15 approval not applied: article version changed.")
        return False
    if applied:
        print("Owner-requested October 15 Journal version approved and released immediately.")
    return applied
