# Journal approval and release

No deployment is authorized by this implementation. Care Brief and email sending
are unchanged.

## Authority

Studio uses the existing Clerk session cookie. The server verifies the signature,
issuer, expiry, session status, trusted origin and the designated reviewer's
verified email address. A signed-in account alone is not approval authority.
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
