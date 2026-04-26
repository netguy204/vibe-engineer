---
status: ACTIVE
ticket: null
parent_chunk: landing_page_veng_dev
code_paths: ["site/src/pages/index.astro", "site/src/layouts/BaseLayout.astro"]
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

The veng.dev landing page loads its Umami analytics script from the
project's own domain (`analytics.veng.dev`) rather than a third-party host.
The single script tag lives in the shared layout so every page picks it up:

```html
<script defer src="https://analytics.veng.dev/script.js" data-website-id="45c5153f-764f-4e64-8ae3-21a8db285393"></script>
```

The script tag belongs in the shared layout (`BaseLayout.astro`) rather
than individual pages so any new page automatically inherits analytics.
Site-wide search for analytics script tags must return only the
`analytics.veng.dev` host — no third-party references.

## Success Criteria

- The Umami analytics script loads from `https://analytics.veng.dev/script.js`
- The `data-website-id` is `45c5153f-764f-4e64-8ae3-21a8db285393`
- No references to the old analytics host remain in the site source
- The script tag has the `defer` attribute

## Relationship to Parent

Parent chunk `landing_page_veng_dev` created the landing page and site structure.
All page structure, design, and content remain valid. This chunk only modifies
the analytics script tag — no layout, copy, or style changes.