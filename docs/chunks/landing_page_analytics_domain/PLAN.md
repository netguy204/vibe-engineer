

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The analytics script tag lives in `site/src/layouts/BaseLayout.astro` (lines
16–49). It currently uses environment variables with a fallback to the old Umami
host (`https://umami-bold-frog-5356.fly.dev`). Now that we own the
`analytics.veng.dev` subdomain, we should hardcode the new domain directly and
remove the environment-variable indirection — there's no longer a reason to
configure the analytics URL per-environment since all deployments should use our
domain.

The change is purely mechanical: replace the env-var-based URL construction with
a static `https://analytics.veng.dev/script.js` src and confirm the website ID
matches the target value.

No tests are needed for this change — it's a static HTML attribute swap in a
layout template. Verification is visual (inspect the rendered `<head>` tag).

Code paths in GOAL.md already reference `site/src/layouts/Layout.astro`; we
should update that to the correct file `site/src/layouts/BaseLayout.astro`.

## Subsystem Considerations

No subsystems are relevant to this change.

## Sequence

### Step 1: Remove environment-variable indirection for analytics URL

In `site/src/layouts/BaseLayout.astro`, replace the env-var-based URL
construction (lines 16–17):

```astro
const umamiUrl = import.meta.env.PUBLIC_UMAMI_URL || 'https://umami-bold-frog-5356.fly.dev';
const umamiSiteId = import.meta.env.PUBLIC_UMAMI_SITE_ID || '45c5153f-764f-4e64-8ae3-21a8db285393';
```

Remove both `const` declarations entirely. They are no longer needed since the
URL is now a known constant.

### Step 2: Replace the script tag with a static version

Replace the conditional script block (lines 47–49):

```astro
{umamiUrl && umamiSiteId && (
  <script defer src={`${umamiUrl}/script.js`} data-website-id={umamiSiteId}></script>
)}
```

With a simple static script tag:

```html
<script defer src="https://analytics.veng.dev/script.js" data-website-id="45c5153f-764f-4e64-8ae3-21a8db285393"></script>
```

The conditional wrapper is no longer needed since there are no variable inputs
that could be missing.

### Step 3: Verify no other references to old analytics host

Search the entire `site/` directory for `umami-bold-frog-5356.fly.dev` and any
other references to the old host. Confirm zero matches remain. Also search for
`PUBLIC_UMAMI_URL` and `PUBLIC_UMAMI_SITE_ID` env-var references (e.g., in
`.env` files, `astro.config.*`, or other templates) and remove any that exist.

### Step 4: Update GOAL.md code_paths

Update the chunk GOAL.md frontmatter `code_paths` to reference the correct file
`site/src/layouts/BaseLayout.astro` instead of `site/src/layouts/Layout.astro`.

## Dependencies

- The `analytics.veng.dev` DNS record must be configured and pointing to the
  Umami instance. This is an infrastructure prerequisite outside this chunk's
  scope (assumed already done since the sibling chunk
  `landing_page_analytics_redirect` is ACTIVE and already uses this domain for
  redirect URLs).

## Risks and Open Questions

- **DNS/TLS readiness**: If `analytics.veng.dev` is not yet serving the Umami
  script, the analytics tag will silently fail (the `defer` attribute and
  browser behavior mean this won't block page load). Low risk — the redirect
  sibling chunk already uses this domain.
- **Removing env-var flexibility**: Hardcoding the URL means local/staging
  environments can't override the analytics endpoint. This is acceptable because
  analytics in dev is either irrelevant or actively undesirable (pollutes
  production data).

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