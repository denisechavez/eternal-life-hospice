---
name: Growth Intelligence source API rules
description: Non-obvious WhatConverts and Brevo reporting behaviors that affect aggregate dashboard accuracy.
---

WhatConverts lead reporting must always supply explicit `start_date` and `end_date` values. A request without them defaults to the current UTC date and can falsely appear to confirm zero leads. The supported lead range is up to 400 days.

**Why:** Authentication succeeded while an undated request returned zero; an explicit dated diagnostic returned reportable phone-call and form activity.

**How to apply:** Use an explicit reporting window for every dashboard request and a separate, bounded diagnostic window when validating historical availability. Keep all personal lead fields excluded.

Brevo email campaign totals must aggregate `statistics.campaignStats` across recipient lists. Do not treat `statistics.globalStats` as authoritative when it is present but zero.

**Why:** Historical sent campaigns had zeroed global statistics but populated per-list delivery, open, click, bounce and unsubscribe statistics.

**How to apply:** Sum per-list campaign rows for historical campaign performance, then filter campaigns by sent date for fixed-period baselines. Never infer activity for a period with no sends.