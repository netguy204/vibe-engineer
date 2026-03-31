---
status: ACTIVE
ticket: null
parent_chunk: landing_page_veng_dev
code_paths:
- site/src/pages/index.astro
- site/src/components/Nav.astro
code_references:
  - ref: site/src/pages/index.astro#track
    implements: "Defensive Umami event helper that silently fails when adblockers remove the analytics script"
  - ref: site/src/pages/index.astro#checkScroll
    implements: "Scroll depth milestone tracking (25/50/75/100%) with fire-once semantics"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_analytics_domain
---

# Chunk Goal

## Minor Goal

Instrument all interactive elements on the veng.dev marketing site with Umami
custom events using the `umami.track()` API. This enables measuring user
engagement with specific page elements.

### Events to instrument

1. **Code comparison widget** — Track when users:
   - Switch between before/after views
   - Expand/collapse code blocks
   - Interact with the comparison UI
   - Event names: `code_compare_switch`, `code_block_expand`, `code_block_collapse`

2. **Chunk workflow visualization** — Track when users:
   - Step through workflow stages
   - Click on chunk examples
   - Interact with the workflow diagram
   - Event names: `workflow_step_click`, `chunk_example_click`

3. **GitHub links** — Track all outbound clicks to GitHub:
   - Repo link, stars badge, CTA buttons pointing to GitHub
   - Event name: `github_click` with data property for link location
   - Note: GitHub links now use the analytics redirect URL
     (`https://analytics.veng.dev/q/bMiDbOK78`) from the
     `landing_page_analytics_redirect` chunk — instrument the click event
     in addition to the redirect tracking

4. **Other interactive elements**:
   - CTA buttons (event: `cta_click` with button label)
   - Navigation links (event: `nav_click` with destination)
   - Scroll depth milestones (event: `scroll_depth` with percentage: 25, 50, 75, 100)

### Implementation reference

Use the Umami track events API: https://docs.umami.is/docs/track-events

```javascript
// Basic event
umami.track('event-name');

// Event with data properties
umami.track('github_click', { location: 'hero-cta' });
```

The Umami script is already loaded on the page (set up by
`landing_page_analytics_domain` chunk) from
`https://analytics.veng.dev/script.js`. The `umami.track()` function is
available globally once the script loads.

## Success Criteria

- All code comparison widget interactions fire Umami events
- All workflow visualization interactions fire Umami events
- All GitHub/outbound link clicks fire Umami events with location data
- CTA button clicks fire events with button labels
- Scroll depth milestones (25/50/75/100%) fire events
- Events use descriptive names and include relevant data properties
- No errors in browser console from event tracking
- Events are defensive — if `umami` is not loaded (adblocker), calls
  fail silently without breaking the page

## Relationship to Parent

Parent chunk `landing_page_veng_dev` created the site and all interactive
elements. `landing_page_analytics_domain` set up the Umami script tag.
`landing_page_analytics_redirect` added analytics redirect URLs for GitHub
links. This chunk adds event tracking on top of the existing page without
modifying layout, design, or functionality.