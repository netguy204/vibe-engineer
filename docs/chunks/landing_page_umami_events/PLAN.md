

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The site currently has zero client-side JavaScript — all interactivity (hero
code comparison tabs, workflow step tabs) is implemented with CSS radio inputs
and `:checked` selectors. The Umami script (`analytics.veng.dev/script.js`) is
already loaded in `BaseLayout.astro` with `defer`, making `umami.track()`
available globally after page load.

**Strategy:** Add a single `<script>` tag at the bottom of `index.astro` that
attaches event listeners to all interactive elements. This keeps all tracking
logic co-located and easy to audit. Every `umami.track()` call is wrapped in a
defensive guard (`typeof umami !== 'undefined'`) so adblockers don't cause
errors.

**Why inline in index.astro, not a separate file:** The tracking is
page-specific (the landing page is the only page with these interactive
elements). A separate `.js` file would add a network request for code that's
only relevant here. An inline script keeps the tracking visibly coupled to the
markup it instruments.

**No tests needed:** This is pure client-side event tracking that calls an
external analytics API. There's no testable business logic — the correctness
criteria are: (1) events fire in the browser console's network tab, and (2) the
page doesn't break when Umami is blocked. Both are verified by manual browser
testing.

## Subsystem Considerations

No subsystems are relevant. This chunk adds client-side analytics to the
marketing site and does not touch the ve CLI or its subsystems.

## Sequence

### Step 1: Create the tracking helper and defensive guard

Add a `<script>` block at the end of `site/src/pages/index.astro` (after the
closing `</BaseLayout>` tag — Astro supports this). Define a helper function:

```javascript
function track(event, data) {
  if (typeof umami !== 'undefined') {
    umami.track(event, data);
  }
}
```

All subsequent tracking calls use `track()` instead of `umami.track()` directly,
ensuring silent failure when Umami is blocked.

Add a `// Chunk: docs/chunks/landing_page_umami_events` backreference comment at
the top of the script block.

Location: `site/src/pages/index.astro`

### Step 2: Instrument the hero code comparison tabs

Listen for `change` events on the radio inputs named `hero-view`
(`#tab-engineered` and `#tab-coded`). When a tab is selected, fire:

```javascript
track('code_compare_switch', { view: 'engineered' | 'coded' });
```

The radio inputs already exist at lines 15–16 of `index.astro`. Attach
listeners by querying `input[name="hero-view"]`.

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 3: Instrument the workflow visualization tabs

Listen for `change` events on the radio inputs named `workflow`
(`#wf-goal`, `#wf-plan`, `#wf-implement`, `#wf-complete`). When a step is
selected, fire:

```javascript
track('workflow_step_click', { step: 'goal' | 'plan' | 'implement' | 'complete' });
```

Extract the step name from the input's `id` attribute (strip the `wf-` prefix).

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 4: Instrument the CTA `<details>` expand/collapse

The "Other install methods" `<details>` element (line 131) fires a `toggle`
event. Instrument it:

```javascript
track('code_block_expand');   // when details.open becomes true
track('code_block_collapse'); // when details.open becomes false
```

Query `.cta-details` and listen for the `toggle` event.

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 5: Instrument GitHub / outbound link clicks

All GitHub links currently point to
`https://analytics.veng.dev/q/bMiDbOK78`. There are two: one in `Nav.astro`
and one in the CTA section of `index.astro`.

Attach `click` listeners to all `a[href*="analytics.veng.dev"]` links. Derive
a `location` data property from the link's context:

- Nav link → `{ location: 'nav' }`
- CTA link → `{ location: 'cta' }`

Determine location by checking if the link is inside `nav` (ancestor element)
or `.cta-links`.

```javascript
track('github_click', { location: 'nav' });
track('github_click', { location: 'cta' });
```

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 6: Instrument CTA button clicks

The primary CTA is the install command block (`.cta-command`). There isn't a
traditional button, but we should track clicks on the CTA section elements that
indicate engagement:

- Click on `.cta-command` → `track('cta_click', { label: 'uv-install' })`
- Click on `.alt-command` → `track('cta_click', { label: 'pip-install' })`

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 7: Instrument navigation link clicks

Add click listeners to all `nav a` elements. Fire:

```javascript
track('nav_click', { destination: link.textContent.trim().toLowerCase() });
```

This captures the nav logo ("ve" → home) and the GitHub link (already tracked
as `github_click` in Step 5, but `nav_click` provides navigation-specific
context).

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 8: Implement scroll depth tracking

Use an `IntersectionObserver` to fire scroll depth milestones at 25%, 50%,
75%, and 100%. Place four invisible sentinel `<div>` elements at those
positions in the page, or calculate based on `document.documentElement.scrollHeight`.

**Preferred approach:** Use a `scroll` event listener (throttled via
`requestAnimationFrame`) that calculates scroll percentage and fires each
milestone exactly once:

```javascript
const milestones = [25, 50, 75, 100];
const fired = new Set();

function checkScroll() {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const percent = Math.round((scrollTop / docHeight) * 100);
  for (const m of milestones) {
    if (percent >= m && !fired.has(m)) {
      fired.add(m);
      track('scroll_depth', { percentage: m });
    }
  }
}

window.addEventListener('scroll', () => requestAnimationFrame(checkScroll));
```

Location: `site/src/pages/index.astro` (within the script block from Step 1)

### Step 9: Manual browser verification

Open the site in a browser with the Network tab open. Verify:

1. Switching hero tabs fires `code_compare_switch` events
2. Clicking workflow steps fires `workflow_step_click` events
3. Expanding/collapsing install methods fires `code_block_expand`/`collapse`
4. GitHub links fire `github_click` with correct location
5. CTA commands fire `cta_click` with correct label
6. Nav links fire `nav_click`
7. Scrolling fires `scroll_depth` at 25/50/75/100%
8. With an adblocker enabled, no console errors appear

## Dependencies

- **`landing_page_analytics_domain`** (ACTIVE) — Umami script tag in
  BaseLayout.astro. Already present.
- **`landing_page_analytics_redirect`** (ACTIVE) — GitHub links already use
  the analytics redirect URL. Already present.
- **`landing_page_veng_dev`** (ACTIVE) — All interactive elements exist.
  Already present.

No new external libraries needed. Umami's `track()` API is provided by the
already-loaded script.

## Risks and Open Questions

- **Umami script load timing:** The Umami script is loaded with `defer`, so it
  runs after HTML parsing but potentially after our inline script. Wrapping
  calls in the `track()` helper handles this for click/change events (which
  happen well after page load). Scroll depth tracking starts on `scroll` events
  which also happen after load. No race condition expected.
- **Adblocker behavior:** Some adblockers remove the Umami script entirely;
  others block network requests but leave the global object. The `typeof umami
  !== 'undefined'` guard handles both cases.
- **Event name conventions:** Umami has no strict naming rules, but we should
  keep names lowercase with underscores for consistency. All event names in
  GOAL.md already follow this convention.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->