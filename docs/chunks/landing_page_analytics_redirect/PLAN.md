

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Simple find-and-replace of all GitHub repository URLs in the Astro site source
files. The landing page is built with Astro SSG (created by parent chunk
`landing_page_veng_dev`). Two source files contain direct links to
`https://github.com/netguy204/vibe-engineer`:

1. **`site/src/pages/index.astro`** — line 139, the "GitHub" link in the CTA section
2. **`site/src/components/Nav.astro`** — line 8, the "GitHub" link in the nav bar

Both `href` values will be changed to the analytics redirect URL
`https://analytics.veng.dev/q/bMiDbOK78`. Link text ("GitHub") and
`target="_blank" rel="noopener"` attributes remain unchanged.

**Note on code_paths:** The GOAL.md lists `site/index.html` as the code path,
but the site uses Astro. The actual source files are `site/src/pages/index.astro`
and `site/src/components/Nav.astro`. The GOAL.md code_paths will be updated to
reflect the real files.

No tests are needed for this change — it is a static content edit with no logic.
Verification is visual: confirm both links point to the redirect URL and no
direct GitHub URLs remain in the site source.

<!-- No subsystem considerations — this is a static content edit with no
     architectural implications. -->

## Sequence

### Step 1: Update code_paths in GOAL.md

Change the `code_paths` frontmatter in
`docs/chunks/landing_page_analytics_redirect/GOAL.md` from `site/index.html` to
the actual Astro source files:
- `site/src/pages/index.astro`
- `site/src/components/Nav.astro`

### Step 2: Replace GitHub URL in Nav.astro

In `site/src/components/Nav.astro`, change the `href` on line 8 from
`https://github.com/netguy204/vibe-engineer` to
`https://analytics.veng.dev/q/bMiDbOK78`.

Location: `site/src/components/Nav.astro`

### Step 3: Replace GitHub URL in index.astro

In `site/src/pages/index.astro`, change the `href` on line 139 from
`https://github.com/netguy204/vibe-engineer` to
`https://analytics.veng.dev/q/bMiDbOK78`.

Location: `site/src/pages/index.astro`

### Step 4: Verify no remaining direct GitHub URLs

Search all files under `site/` for any remaining occurrences of
`github.com/netguy204/vibe-engineer` to confirm complete replacement.
The deploy workflow (`.github/workflows/deploy-site.yml`) is not a landing page
link and should be left unchanged if it references the repo.

## Dependencies

- Parent chunk `landing_page_veng_dev` must be merged (it is — commit `54e0b36`
  is on `main`)
- The analytics redirect URL `https://analytics.veng.dev/q/bMiDbOK78` must be
  configured and working (assumed to be set up externally)

## Risks and Open Questions

- The GOAL.md references `site/index.html` but the site uses Astro SSG; the
  actual source files are `.astro` components. This is a documentation mismatch
  from the GOAL, not a code risk. Step 1 corrects the code_paths.
- If the analytics redirect URL is not yet live, clicking the link will fail.
  This is an external dependency outside this chunk's scope.

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