---
status: ACTIVE
ticket: null
parent_chunk: landing_page_veng_dev
code_paths: ["site/src/pages/index.astro", "site/src/layouts/Layout.astro"]
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: ["landing_page_analytics_redirect"]
---

# Chunk Goal

## Minor Goal

Update the Umami analytics script tag on the veng.dev landing page to load from
our own domain. Replace the current Umami script tag with:

```html
<script defer src="https://analytics.veng.dev/script.js" data-website-id="45c5153f-764f-4e64-8ae3-21a8db285393"></script>
```

Find all analytics script tags across the site templates and pages. Ensure all
scripts load from `analytics.veng.dev`, not the old host. The script tag may be
in a layout file (e.g., `Layout.astro`) rather than individual pages.

## Success Criteria

- The Umami analytics script loads from `https://analytics.veng.dev/script.js`
- The `data-website-id` is `45c5153f-764f-4e64-8ae3-21a8db285393`
- No references to the old analytics host remain in the site source
- The script tag has the `defer` attribute

## Relationship to Parent

Parent chunk `landing_page_veng_dev` created the landing page and site structure.
All page structure, design, and content remain valid. This chunk only modifies
the analytics script tag — no layout, copy, or style changes.