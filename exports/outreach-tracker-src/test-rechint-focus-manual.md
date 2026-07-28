# Manual QA: `#recHint` focus-ring (keyboard vs mouse)

The CSS rule `#recHint:focus-visible { outline: 2px solid var(--slate); outline-offset: 2px }`
limits the focus ring to keyboard navigation only.  The element also carries `tabindex="0"` in
`index.html` so that keyboard Tab navigation can actually reach it.

The automated test (`test-rechint-focus.js`) guards the CSS rule and the `tabindex` attribute
statically; this checklist covers the live browser behaviour that only a human can verify.

---

## Prerequisites

- The app is running locally (`python3 website/devserver.py` or via the outreach-tracker workflow).
- You have logged in so that `#recHint` is visible on the Log Visit tab.

---

## Test A — Mouse click must NOT show an outline on `#recHint`

1. Open the app in a desktop browser (Chrome or Firefox).
2. On the **Log Visit** tab, locate the **Record instead of typing** button.
3. **Click the button with your mouse** (do not use the keyboard).
4. Observe the grey hint text that appears beneath the button (`#recHint`).

**Expected:** No visible outline / focus ring around the hint text.  
**Fail if:** A coloured rectangle appears around the hint paragraph after the click.

---

## Test B — Keyboard Tab MUST show an outline on `#recHint`

1. Click somewhere neutral on the page (e.g. the page heading) so focus starts
   away from the form controls.
2. Press **Tab** repeatedly until `#recHint` receives focus.  
   *(The element has `tabindex="0"` in the HTML, making it reachable by keyboard.)*
3. Observe the hint text while it is focused.

**Expected:** A 2 px slate-blue outline appears around the hint paragraph.  
**Fail if:** No outline is visible when the element is focused via Tab.

---

## Why `:focus-visible` not `:focus`

`:focus-visible` is honoured by all modern browsers (Chrome ≥ 86, Firefox ≥ 85, Safari ≥ 15.4).
It shows the ring only when the browser's heuristic decides the user is navigating by keyboard,
so mouse clicks do not trigger it even though the element has `tabindex="0"`.

The automated test catches two common regressions:

| Regression | How the test catches it |
|---|---|
| `:focus-visible` replaced by `:focus` in styles.css | Checks the selector name exactly |
| `tabindex="0"` removed from `#recHint` in index.html | Checks the attribute on the element |

---

## Running the automated check

```
node exports/outreach-tracker-src/test-rechint-focus.js
```

Or via npm from within the `exports/outreach-tracker-src/` directory:

```
npm run test:focus
```
