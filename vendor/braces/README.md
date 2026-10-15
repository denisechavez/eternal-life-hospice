# Local braces security backport

Based on the MIT-licensed `braces@3.0.3` source from
https://github.com/micromatch/braces/tree/3.0.3.
This is **not** an upstream patched release. The distinct local package name
and prerelease version identify our maintained backport, not a published fix.

As of 2026-10-15, upstream's latest release is still vulnerable to
GHSA-vfj7-8cjw-p6xm (CVE-2026-93687). Both design sandboxes require its API
through micromatch; upgrading their compatible parents does not remove it.
An npm override installs this source in place of `braces`, without fetching
an unaudited third-party fork or keeping a vulnerable fallback.

The parser caps structural nesting (braces **and parentheses**) at 100 levels.
Recursive compile, expand, stringify, append and flatten walkers independently
enforce the same cap, including callers passing an AST instead of a string.
Violations throw a deliberate `RangeError` with `code = BRACES_MAX_DEPTH`,
before JavaScript's call stack is exhausted. The cap cannot be disabled by
caller options. Ordinary pattern behavior and the existing range limit remain
unchanged. Source comments were shortened; the original license is retained.

The sandboxes use `install-links=true` so npm packs this file dependency rather
than symlinking outside their dependency trees. Keep that setting for `npm ci`.
The vendored source must be present when installing either sandbox.

Run `node scripts/test-dependency-security.cjs` after installing dependencies.
It exercises benign patterns, deep inputs, direct AST inputs, dependency
versions and the override wiring. Replace this backport with the official
package once upstream publishes an equivalent fix, regenerate both lockfiles
and keep the regression tests.
