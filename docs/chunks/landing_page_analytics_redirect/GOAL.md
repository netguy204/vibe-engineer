---
status: ACTIVE
ticket: null
parent_chunk: landing_page_veng_dev
code_paths:
- site/src/pages/index.astro
- site/src/components/Nav.astro
code_references:
  - ref: site/src/components/Nav.astro
    implements: "Analytics redirect URL for GitHub link in navigation bar"
  - ref: site/src/pages/index.astro
    implements: "Analytics redirect URL for GitHub link in CTA section"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- artifact_demote_to_project
---
# Chunk Goal

## Minor Goal

Every GitHub repository link on the veng.dev landing page routes through the
analytics redirect URL `https://analytics.veng.dev/q/bMiDbOK78` instead of
linking directly to GitHub. The redirect still takes users to GitHub but
routes through analytics so conversion rate can be measured.

The landing page is built with Astro; the GitHub-bound links live in
`site/src/pages/index.astro` (CTA section) and `site/src/components/Nav.astro`
(navigation bar). Both use the analytics redirect URL as their `href`.

## Success Criteria

- Every link on the landing page pointing to the GitHub repo uses
  `https://analytics.veng.dev/q/bMiDbOK78`
- No direct GitHub repo URLs remain in `site/src/pages/index.astro` or
  `site/src/components/Nav.astro`
- The page renders correctly and all links are clickable

## Relationship to Parent

Parent chunk `landing_page_veng_dev` established the landing page structure.
All page structure, design, and content from the parent remain valid. This chunk
scopes only the link `href` values — no layout, copy, or style changes.