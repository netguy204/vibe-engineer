---
discovered_by: claude
discovered_at: 2026-04-26T01:44:00
severity: low
status: resolved
resolved_by: "audit batch 5f — present-tense rewrite of GOAL"
artifacts:
  - docs/chunks/landing_page_analytics_redirect/GOAL.md
---

## Claim

`docs/chunks/landing_page_analytics_redirect/GOAL.md` (pre-rewrite) instructed:

> Find every `<a>` tag and any other element in `site/index.html` that
> currently links to the GitHub repo and change the `href` to the analytics
> redirect URL.

…and listed `site/index.html` again under the success criteria
("No direct GitHub repo URLs remain in `site/index.html`").

## Reality

The landing page is built with Astro. `site/index.html` does not exist.
The GitHub-bound links live in:

- `site/src/pages/index.astro` (CTA section)
- `site/src/components/Nav.astro` (navigation bar)

The chunk's `code_paths` were already correct; the inconsistency was localized
to the body and success-criteria prose.

## Workaround

Rewrote the GOAL body and success criteria to reference the actual Astro source
files, matching `code_paths`.

## Fix paths

- (FIXED) Rewrite GOAL body and success criteria to point at the real Astro
  source files.
- Alternative: introduce a `site/index.html` shim — undesirable, would diverge
  from the Astro build pipeline.
