---
name: Disposable PostgreSQL fixture encoding
description: Why local PostgreSQL fault-test clusters must explicitly use UTF-8.
---

Use an explicit UTF-8 encoding when creating disposable PostgreSQL clusters
with locale disabled.

**Why:** On this environment, `initdb --no-locale` without an encoding created
SQL_ASCII storage. Psycopg returned database text as bytes, so saved slugs did
not compare equal to Python strings and idempotency tests reported duplicate
approval audits despite correct production logic.

**How to apply:** Keep locale-independent fixtures, but specify
`--encoding=UTF8`; do not alter approval/retry semantics to accommodate an
accidentally SQL_ASCII test database.
