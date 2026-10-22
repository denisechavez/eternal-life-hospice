# Journal monitor and independent freshness check

The release monitor runs at **6:45 a.m. America/Los_Angeles**, 15 minutes
after the 6:30 a.m. release time. Its two UTC cron entries are filtered by
Pacific local date, including DST. It only reads publication state; neither
monitor approves drafts, changes holds or publishes anything.

The **separate** `journal-monitor-freshness.yml` workflow checks at **8:17
a.m. Pacific**, after a 90-minute scheduler grace period. It uses GitHub's
read-only Actions API to check that `journal-release.yml` is enabled and
that the appropriate scheduled run finished and produced a current receipt.
A successful workflow alone is insufficient: the other UTC-offset run is a
no-op and does not prove the daily check executed. Manual runs do not count
as scheduled execution.

## Separate outcomes

- **Publication gap**: the monitor ran but an article was not published.
  Review the exact revision's approval or hold in Studio. Never approve a
  draft merely to clear a monitoring alert.
- **Monitoring unavailable**: the monitor ran but could not check the site.
  This includes a missing release-status endpoint.
- **Monitor run missing or unverified**: the separate freshness check found
  a disabled workflow, no current completed receipt, a crashed run or no
  provider acceptance for a required notification. Check Actions scheduling,
  run logs and artifact upload first; article publication is not established
  either way.
- **Freshness check failed**: inability to read Actions is itself an
  unverified-monitor warning, not a healthy result.

An article-gap or monitoring-unavailable receipt with a Brevo message ID is
recognized as an executed check, even though its workflow correctly exits
with failure. The watchdog does not send a duplicate missing-run warning.
Brevo acceptance requires a 2xx response **and a nonempty messageId**;
acceptance is not proof of inbox delivery.

## Configuration and safe verification

After merge, both workflow files must be present on the repository's default
branch and Actions schedules must be enabled. Set `BREVO_API` in **GitHub
Actions secrets** as for the existing release monitor. Replit workspace
secrets alone do not configure GitHub. The watchdog's built-in GitHub token
needs `actions: read` and `contents: read`. Neither token is logged.

Run offline regression checks:

```sh
python3 website/test-journal-monitor-freshness.py
python3 website/test-journal-release.py
```

These use fake run histories, real ZIP receipts and a loopback fake email
provider. They cover scheduler disablement, missing/stuck/cancelled/manual
runs, wrong-offset skips, stale receipts, DST, email rejection and missing
provider IDs. They never send real mail or access approval APIs.

For deployed scheduling verification, inspect the two scheduled runs in
Actions after the next due time. Download `journal-monitor-result` from the
correct 6:45 Pacific run and check `checkedAt`, `scheduledCron`, `status`
and `alert`. Confirm the 8:17 freshness workflow verifies that receipt.
`alert: accepted` must have a `messageId`; `not-needed` is correct when
healthy and does not claim email acceptance was exercised.

Manual dispatch of either workflow defaults to **no email**. A manual
freshness check before 8:15 Pacific checks the previous due date.
Only explicitly select `send_alerts` if operational email is authorized;
do not use it to automatically send synthetic failure mail to real people.
Use existing operational receipt IDs to confirm Brevo acceptance; no live
provider acceptance or actual scheduler execution is claimed by offline tests.

## Recovery and limits

Re-enable the release workflow or fix the failed step, then inspect the next
scheduled run. A manual dry run helps diagnosis but cannot replace evidence
of the scheduler working. Correct missing GitHub secrets or provider errors
without relaxing Studio approval requirements.

The freshness workflow is independent of the release workflow's enabled
state, job, concurrency group and results. **Both still use GitHub Actions.**
A platform-wide outage, repository-wide schedule disablement or failure of
the watchdog itself needs an external dead-man service on a different
scheduler. These files do not claim to provide that cross-platform guarantee.
The watchdog retains daily alerts while a failure persists rather than
silently suppressing an unresolved outage.
