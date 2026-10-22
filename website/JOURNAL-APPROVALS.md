# Journal approval and release

No deployment is authorized by this implementation. Care Brief and email sending
are unchanged.

## Authority

Studio uses the existing Clerk session cookie. The server verifies the signature,
issuer, expiry, session status, trusted origin and an explicitly authorized
reviewer's verified email address. Denise and Aleksandra are authorized; either
may approve a version independently. A signed-in account alone is not approval authority.
Journal browser-local statuses are ignored. Email review choices remain local.

The server supplies the complete review HTML and an SHA-256 revision covering
that document and its referenced local photographs. An approval includes the
expected revision; stale approvals are rejected. The submitted request cannot
choose article bytes or dates.

Approvals, frozen approved HTML and photographs, releases and an append-only decision audit use
the existing PostgreSQL database. The migration adds only Journal tables and
does not modify tracker data. Run `python3 website/migrate-journal.py` for development.
The next approved publish builds the existing Studio in its build step.
Autoscale startup only runs the idempotent migration and starts the site.

The workspace's database and Clerk accounts are separate from production.
For live publication use `/studio/` on the published domain after an approved
deployment. The same Studio UI signs in against that environment and saves to its
own database. Do not assume workspace approvals transfer across environments.
The public sign-in entry contains no draft copy: draft JavaScript chunks require
the verified reviewer session before the server delivers them. A managed Clerk
proxy serves authentication on the published domain.

## Release

Each approved version becomes eligible on its original editorial date at
06:30 in `America/Los_Angeles`. The server enforces this on requests, including
HEAD, so sleeping Autoscale instances need no midnight rebuild or resident timer.
UTC offsets are derived from the timezone, not hardcoded.

Approved content is snapshotted, not copied over source drafts. New source edits
need fresh approval; an already-approved version can still release without
silently approving the changed version. Late approval releases immediately after
explicit confirmation in Studio. Holding a version prevents pending publication
but cannot retract an already-published version.

The checked-in published-history snapshot came from the live sitemap, not an
inferred date cutoff. Do not regenerate it to "approve" new drafts. Published
originals remain available while revised SEO drafts await review. On a database
outage, originals remain available, new versions fail closed and the monitor
reports that verification is unavailable.

One release set controls article URLs, archive cards and structured data,
Resources picks, search, sitemap and request-time contextual recommendations.
Discovery headlines, summaries and photographs come from the released snapshot,
so a changed source for an already-published URL cannot leak pending revised copy.
Responses must revalidate; no immutable cache is used for dated discovery.

## Independent monitoring

GitHub Actions checks at 06:45 Pacific using two UTC schedules and a timezone
filter, so it works while Autoscale is asleep. It reads the production server's
actual approved-and-due set, then verifies article revision headers, archive,
search and sitemap. Deliberately held or unapproved drafts are not expected.
It never sends newsletter campaigns.

Failures email the existing operations reviewer through Brevo's transactional
email channel. Email delivery rejection makes the workflow fail visibly.
Before the user approves deployment, a missing monitor endpoint is reported as
`not-installed` and does not send a false missed-release alert.

The existing repository `BREVO_API` secret used by the identity-check workflow
must remain configured. No new secret is needed. Scheduled checks become active
when the workflow is on the repository's default branch; GitHub may delay cron
jobs, but public eligibility itself always changes at 06:30. Manual workflow runs
can retry failed email delivery. Persistent outages may send a daily reminder.

## Verification

`python3 website/test-journal-release.py` exercises real PostgreSQL transactions
in an isolated temporary schema, plus deterministic release/DST, authorization,
public discovery and email-monitor cases. It must not be run against production.
Studio's signed-in review requires an actual authorized Clerk account; automated
tests do not bypass application authentication.

### Opt-in large history benchmark

Run `python3 website/benchmark-journal-history.py --run` separately from the
normal correctness suite. It requires `psycopg`, `initdb` and `pg_ctl` on PATH
and a non-root user. It starts a disposable local PostgreSQL cluster with a
private Unix socket and no TCP listener, never reads `DATABASE_URL`, never
uses production data and removes its cluster on exit.

The default synthetic workload has 500 articles, 20,860 saved revisions and
419,700 repeated audit actions, including tied timestamps, old revisions,
unmatched legacy decisions and a hot article with ten times the revision depth.
Article HTML is synthetic too. Candidates, publication originals, clock and
reviewer names are supplied locally; real identity-provider calls and filesystem
article discovery are excluded. The actual `review_items()` and
`article_history()` paths, including their publication-maintenance queries, run
unchanged. This measures application responses plus JSON encoding, not HTTP,
authentication or network transfer.

The benchmark compares queue bytes before/after adding old history, verifies
that the queue does not query the audit log and checks bounded early/deep pages
at a 90%-depth cursor. It records `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for
the actual captured queries after collecting statistics with `VACUUM ANALYZE`.
Both pages must use `journal_audit_article_page` and
`journal_audit_saved_decision`; audit pagination must use ordered index access
and the deep cursor must be an index condition, not OFFSET or a residual filter.
No planner settings force index use. Fixture-only OFFSET locates the deep cursor
outside measured work.

The report includes row counts, PostgreSQL version, individual warm samples,
median/p95 latency, UTF-8 response bytes and full plans/buffer counters. By default
it is written to ignored `generated-artifacts/journal-history-benchmark.json`.
Use `--output` to keep runs separately and compare them on the same machine,
PostgreSQL version and workload. Five warm samples give a useful quick signal,
not a statistically rigorous service-level estimate.

There are **no default timing assertions**. To enforce latency budgets on a
controlled runner, use e.g.
`python3 website/benchmark-journal-history.py --run --samples 20 --max-history-ms 500 --max-queue-ms 500`.
These example budgets are not production promises. Index/payload regressions or
explicitly configured budget failures exit nonzero after writing the report.
`--articles`, `--revisions`, `--actions` and `--page-size` can scale the fixture;
keep enough events past the deep cursor to fill a page.

`python3 website/test-journal-history-benchmark.py` tests the harness with small
disposable clusters, including deliberately removed indexes and explicit budget
failures. It adds no performance threshold to the normal release suite.

## Reviewer-only history

### Authenticated loading regression gate

The publish build runs `bash website/check-studio-regressions.sh` after compiling
Studio. Run the same command from any directory for the focused security/browser
checks. It requires the installed Python/Node dependencies and Chromium, but no
database, real reviewer session or external provider access.

The browser fixture bundles the real `StudioSession` and `App` with synthetic
reviewer identities and a synthetic dynamically imported review component.
It checks deep links, backend verification before private import requests and
execution, public sign-in/error styles, rejected accounts, sign-out failure,
account change and retry recovery. No unpublished articles are bundled in it.
Provider responses are isolated and non-loopback browser requests are rejected.

The server checks exercise the real asset and API handlers, including encoded
private-chunk paths, anonymous/unauthorized reads and writes and public CSS.
Fresh synthetic RSA tokens verify both production domains' matching issuers and
proxy JWKS URLs, signatures, expiry, active sessions and verified reviewer
authority. Provider network I/O is intercepted; these are not live sign-in tests.
Both checks must exit successfully and print their completion sentinels for
publishing to proceed. Authentication and private-bundle protection are unchanged.

The authenticated `/api/studio/journal` response includes each article's
append-only audit history, its current review revision, the retained published
revision and any frozen pre-Studio original. Both verified reviewers can read it.
No history or reviewer details are added to public release monitoring or analytics.

Studio displays the persisted reviewer account ID and decision timestamp.
Optional names are current Clerk directory labels, not historical name
snapshots; unavailable or deleted accounts retain their recorded IDs.
Decision rows without audit entries are explicitly labeled saved decisions.
Publication dates are never represented as approval timestamps.

New audit entries record `production` or `workspace`. Older events without this
field remain “Event environment not recorded”; the environment of the database
being read is labeled separately and is not proof of a historical event's origin.
Frozen originals without reviewer records are labeled “Pre-Studio history.”
Neither these labels nor a decision on an older revision approve a changed draft.
The additive schema setup runs for development after merge.
