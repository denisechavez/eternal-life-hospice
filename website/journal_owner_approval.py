"""Version-pinned owner instructions; not a login or general approval bypass.

The project owner explicitly requested approval/publication of the October 15
Journal post while Studio sign-in was unavailable. Do not add other articles
without a separate explicit request. This runs only on an approved publication,
records its actual source and freezes the exact reviewed content and imagery.
The owner's subsequent "post it now" instruction authorizes immediate release
of this one version. Every other article keeps its existing schedule.

On 2026-10-21 the owner separately authorized reconciliation through October 31.
That bounded set is pinned below and retains the regular 6:30 a.m. schedule.

The owner subsequently extended consent through December 31, 2026. November
and December documents are pinned by their complete content digest below;
their canonical URLs and image references are part of those hashed bytes.
Catch-up retains article dates, never backdates approval or release audit time.
"""
import journal_release as journal

# Frozen at the explicit through-December-31 request. Never regenerate on startup.
YEAR_END_REVISIONS = dict(line.split() for line in """
2026-11-01 b373c5ccd9897f111cc070b8e4b60533bab8fca1e719c85e5aa6f29ddaa2a444
2026-11-02 15898c9211d04a431c14d9d2c665e4a34c6c70c2c3117ce681db507be421cc7d
2026-11-03 0f6ca8d98f787ecc6ecce717e9e3b4ff4dda8b5fd0593bc61ab90195ee0327b8
2026-11-04 41b2333293ce06765906065eb6a7c5409246c42799aa3cbd230e3924b4457218
2026-11-05 78f6d657e4e752e6e43062cd95052245bb05899bf21a9432eac0fc2a0b47df95
2026-11-06 94059144dc9609cad38162ce5b481559a69223b88c4c6f5e196c0cc326bc7b33
2026-11-07 8e93a614718ba1261e561aa2aaf5b15f356ed6b592d6a4b6300a56c96f59ca6f
2026-11-08 f2daace34598da63d850711a4df501adbecc37f6ec1fa161bd5a162fe17e0391
2026-11-09 6177d1a93bfd4377c85ae70b3040d5170f1ab62e964b4458a93b56a30ecd721a
2026-11-10 ad99d95af19da38c2ee5ea76f8782b46f43464345fa9892ecfefe579efd3e4f6
2026-11-11 8639b8741acc228c8f96a1b638de312fff3474bd4fc59f6a084e3a04666d17b4
2026-11-12 4d7060be14f4d30f449d33c627f9f56a10848756d510bee15c50bd8e78f5d896
2026-11-13 02c1e5e21bf29ef006a69dd1e05295c7dcf140aa6082b233e122cc993f64540a
2026-11-14 0fc5e212e728b0c0ea7fe0d6d17e90409278c4a67c819e51be79c5e20a95f614
2026-11-15 12fa0ac6ca610f6a40f2b52ca1b63aedd20f8d730d874129d22e2ba917524771
2026-11-16 d0aaa211c4f2945365392b7e47422c4a7b43c5c006c396fc208cb85d1f33940e
2026-11-17 6ac498ee06405014cfa9fdf153f3434fdb160c3d54e5999b0e011fb6f020a2d6
2026-11-18 6c5911a054781d0c945bf7df0b5b2d26127038d17f28f40edf3983d304919c99
2026-11-19 c04c211a951af4d447d5394ed262573bb14693ddda7bf76e8d09156fe23ca9a5
2026-11-20 53fddd9b54d4ad60a2385de6c1f189ee28832c35ae98e3f1f7fd2653593d9dc5
2026-11-21 2fb94fe3146a165d694b7ef844c418f932feb4c6e826bcb44c3b3db5fcf5109c
2026-11-22 e38e2bf79dc2a87282c90e4c93a8349a5748e79ec7dc27ba686e529be8c2a1d1
2026-11-23 20da68e6bfda27d129f15eaa2bd296f47e7ee1fd58b7390e8624d0df29e1f87f
2026-11-24 533e81fb8a50341fa1217ee7ad32a385354d30b1f6f58d5f7323cddf4d430dab
2026-11-25 39657be4f7da816fb754f701dd70192bc0396c09e444afcd1513d32a95e17814
2026-11-26 7856d7c4121cac8a8bda9f6174fba7dc4c6592a24f1b79da7893a85ddb2e4d61
2026-11-27 97e807cb83e4dcd7c80f37e9989827a782984e691bc08ef129c1f3859e4567ff
2026-11-28 9d5bcd1e6639aed6b82c02547db2fc7457845db76ff43526ebb9861d5bb075e6
2026-11-29 adddc10b51a04a760dfb7af26bd2474c627722704fbadd583e3b4637fe3d2e8c
2026-11-30 5cbf56155a2a90badac2e0f8ad322da3df7ea378b70ffc67ce7f8e5ddb7aefac
2026-12-01 d748b4ff4a2f35eecaa99bdadb6badbfbf2b582728451e29586146fb954a5823
2026-12-02 4df7b503c7971e8a5708bb56232c97eea5c3b4736df0ddfacfe452f953d54267
2026-12-03 069667d2c8028dbdf4cc5aaf8b4099bbca0055850f9f0aa3ee930cf7f0bfdbc6
2026-12-04 c3e9d4b9103d712b5da7403d7f4efeecb3d0c0bcf9e7bcf1c9584371e2d37d1c
2026-12-05 dbe919d1684f681428408489127c250bb01b73d0988d179dfa4f4704cb2c0f5c
2026-12-06 b270414716ac715fdb2c1d5400de132f48491791718c2054837c876e7f096ee0
2026-12-07 699db47509eb96613cb4af64f12b2c759b76bf96b7c0bd4b30c14c3eb9c851fe
2026-12-08 04601c4af4205d822fc8c319bdabe2e2fbce42681a8e4d994761328e683197ce
2026-12-09 983023f2f3763bb782e75afc1a1b6fabe8b9c53534da4a5d6d0e49aa3e11d141
2026-12-10 f92314a98a188f8645f49e1af6d61d2af28d7cff8c9ef4264c4c91fc35de604a
2026-12-11 8ad8aff882fb01cee180844d1edb9ee4c64b1e42c62e844afa6369a8f9fff15e
2026-12-12 d11e0962c02107b59c2cc4c51530422dba1eb65ca1b0a8f943077c3da6b593fe
2026-12-13 450f477002e3f7036ebdb1d1e7c8a1484b828533833fe148ead93d3269783eb0
2026-12-14 cd9a6adba361730708560d29e5835c5ff5da86b38a5f6a8fbb1b2308dcce05a8
2026-12-15 6a6e5cb4ac0ae4e23e3b6467f8088e6e33fefc478c350485db7fbca36d4439bc
2026-12-16 601c6d4540bc5ae347581623c7bfd5ea51463e16f3cc9e8fc6105c1f337a8358
2026-12-17 d03a79c4ee58815246d6dae8a8ffcd141f75ed470747c4d78a3444207abe30bd
2026-12-18 aad8f6e7d460e14c5615075b59274db4e596e3689881fa652d867ae1ea4abec8
2026-12-19 190368e0e7db667801b59e328dfd9a64e2a4a34a7018213b2921c8a186ea84a6
2026-12-20 5464fdff701df60cc28406af9a5808a1a95bf07b0a7101be365104a8a405835f
2026-12-21 0f9b378225c76171d9e45da3d45675b08151c970e5cdcfecca46a9d651283a86
2026-12-22 40a178507e7b09d3b4ffa51ef05d368b1d204f8b9562aa5a423d793affe5a78f
2026-12-23 f46d756cbc210d7ee15578b87780277c345220a02347bc82253f6dfdc358147e
2026-12-24 7153ed43b1494ea34ca5ef06a67e1064658bb0e4a6b3f94b35db1f0a84d1a50d
2026-12-25 996c42d45c564ff61fc87ca184f65abc3bed7d9204b9983a12a5b2b74905be9a
2026-12-26 053a2d801f4ba7ccd7a9bd99bc14df559de59b3517a6742c4dab46b6e707fac5
2026-12-27 3ef04921a5d0d3511d809b27c1e33b402c4a2537cd1a6f8fb7af048a7e4ba734
2026-12-28 23df782cb630e06de72b1cb1c8ce19ca06d43f619d02d0d69d090560d42c6a52
2026-12-29 8080c4bd0e1fbb5b13b5d0ff139b4745c85fa2b361e493e6698ef8749fddd72c
2026-12-30 9fb8624f91cdd6b82d8d8e0f70c4a3373cab4bb9905104484fbc32bf00364439
2026-12-31 73fab61430369f19eb46447bf1d183a6437a3d3fef55d7c046d2a6948f2e3c98
""".strip().splitlines())


def apply_year_end():
    """Apply bounded owner consent without altering dates or existing decisions."""
    if journal.environment() != "production":
        return 0
    records = list(journal.candidates().values())
    applied = 0
    for day, revision in sorted(YEAR_END_REVISIONS.items()):
        matches = [r for r in records if r["date"] == day]
        if (not "2026-11-01" <= day <= "2026-12-31"
                or len(matches) != 1 or matches[0]["revision"] != revision):
            print(f"Year-end reconciliation skipped changed/missing article: {day}")
            continue
        try:
            saved = journal.decide(
                matches[0]["slug"], revision, "approve",
                "Owner-directed through-December-31 approval (outside Studio)",
                only_if_undecided=True, expected_date=day)
        except ValueError:
            print(f"Year-end reconciliation skipped changed article: {day}")
            continue
        applied += bool(saved)
    print(f"Year-end reconciliation: {applied} newly saved approvals; existing decisions preserved.")
    return applied

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


def apply_all():
    """Production startup: one scan/transaction, not 83 serial full scans."""
    if journal.environment() != "production":
        return 0
    requests = [(REQUEST["date"], REQUEST["slug"], REQUEST["revision"],
                 REQUEST["reviewer"], True)]
    requests.extend(
        (day, slug, revision,
         "Owner-directed October reconciliation — 2026-10-21 (outside Studio)", False)
        for day, slug, revision in OCTOBER_REQUESTS)
    # Resolve the fixed dates to fixed URLs without scanning article/image bytes.
    import json
    manifest = json.loads(
        (journal.BASE / "content/30-day-journal-manifest.json").read_text())["articles"]
    for day, revision in sorted(YEAR_END_REVISIONS.items()):
        matches = [r for r in manifest if r["date"] == day]
        if "2026-11-01" <= day <= "2026-12-31" and len(matches) == 1:
            requests.append((day, matches[0]["slug"], revision,
                             "Owner-directed through-December-31 approval (outside Studio)", False))
    applied = journal.apply_owner_batch(requests)
    print(f"Owner reconciliation ready: {applied} newly saved approvals.", flush=True)
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
