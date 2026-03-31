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

Replace all direct GitHub repository links on the veng.dev landing page with
the analytics redirect URL `https://analytics.veng.dev/q/bMiDbOK78`. The
redirect still takes users to GitHub but routes through analytics so we can
measure conversion rate.

Find every `<a>` tag and any other element in `site/index.html` that currently
links to the GitHub repo and change the `href` to the analytics redirect URL.

## Success Criteria

- Every link on the landing page that previously pointed to the GitHub repo
  now points to `https://analytics.veng.dev/q/bMiDbOK78`
- No direct GitHub repo URLs remain in `site/index.html`
- The page renders correctly and all links are clickable

## Relationship to Parent

Parent chunk `landing_page_veng_dev` created the landing page at `site/index.html`.
All page structure, design, and content from the parent remain valid. This chunk
only modifies link `href` values — no layout, copy, or style changes.