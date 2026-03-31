


<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build an Astro SSG project in `site/` with zero client-side JavaScript. The landing page is a single `index.astro` with six content sections. Design tokens come from `DESIGN.md` and are implemented as CSS custom properties. The code example content (Python checkout function with backreferences) is defined once as a data structure and rendered twice by the CodeBlock component (with and without backreferences).

Deploy via GitHub Actions to GitHub Pages with custom domain `veng.dev`.

Reference: CEO plan at `~/.gstack/projects/netguy204-vibe-engineer/ceo-plans/2026-03-30-landing-page.md` contains the full spec including design review and eng review additions.

## Sequence

### Step 1: Scaffold the Astro project

Initialize the Astro project in `site/`:

```bash
cd site && npm create astro@latest . -- --template minimal --no-install
```

Create these files:
- `site/package.json` — Astro with no extras
- `site/astro.config.mjs` — `output: 'static'`, `site: 'https://veng.dev'`
- `site/.nvmrc` — pin Node version (20)
- `site/public/CNAME` — contains `veng.dev`
- `site/public/favicon.svg` — "ve" monogram in amber on transparent

Update repo root `.gitignore`:
```
site/node_modules/
site/dist/
site/.astro/
```

Location: `site/`

### Step 2: Implement the design system as CSS

Create `site/src/styles/global.css` with all CSS custom properties from DESIGN.md:
- Dark mode tokens on `:root` (dark-first)
- Light mode tokens on `@media (prefers-color-scheme: light)` override
- Typography scale (Geist from Google Fonts CDN)
- Spacing scale
- Component styles: `.code-block`, `.decision-card`, `.lifecycle`, `.badge`
- Responsive breakpoints at 640px and 768px

Location: `site/src/styles/global.css`

### Step 3: Create the base layout

Create `site/src/layouts/BaseLayout.astro`:
- HTML5 doctype with `lang="en"`
- `<head>`: charset, viewport, title, meta description, canonical URL
- OG tags: `og:title`, `og:description`, `og:image`, `og:url`, `twitter:card`
- Google Fonts preconnect + Geist/Geist Mono stylesheet link
- Global CSS import
- Umami analytics snippet (conditional: only render if `import.meta.env.PUBLIC_UMAMI_URL` is set)
- Semantic landmarks: `<nav>`, `<main>`, `<footer>`
- Skip-to-content link (visually hidden, visible on `:focus`)

Location: `site/src/layouts/BaseLayout.astro`

### Step 4: Create the Nav component

Create `site/src/components/Nav.astro`:
- Logo: "ve" in Geist Mono, links to `/`
- Links: GitHub (external)
- No docs link yet (hidden until content exists per eng review)
- Responsive: at < 640px, font drops to 12px, gap tightens to 16px

Location: `site/src/components/Nav.astro`

### Step 5: Create the CodeBlock component

Create `site/src/components/CodeBlock.astro`:
- Props: `code: string`, `showBackreferences: boolean`, `dimmed: boolean`
- Renders pre-formatted code with Shiki syntax highlighting (Astro built-in)
- When `showBackreferences` is false, strips lines matching `# Chunk:`, `# Decision:`, `# Subsystem:` patterns
- When `dimmed` is true, applies `opacity: 0.6` to the entire block
- `tabindex="0"` for keyboard scrollability
- Horizontal scroll on overflow, no wrapping

**Important: the Python code example is defined once** as a constant in a shared data file (`site/src/data/hero-code.ts` or inline in the component). Both Section 1 and Section 2 render from the same source. This prevents the DRY violation of duplicating the code example.

Location: `site/src/components/CodeBlock.astro`

### Step 6: Write the hero code example

Write the Python checkout function (~30-40 lines) with these backreference comments:
- `# Subsystem: docs/subsystems/payment_pipeline`
- `# Chunk: docs/chunks/checkout_retry`
- `# Decision: docs/trunk/DECISIONS.md#stripe-retry-policy` (next to `time.sleep(3)`)

The code must:
- Feel realistic (real imports, real types, real error handling)
- Include the hardcoded `time.sleep(3)` that looks like a bug
- Have the backreference comment explaining the sleep as the amber-highlighted line

Location: `site/src/data/hero-code.ts` (or similar)

### Step 7: Build the landing page (index.astro)

Create `site/src/pages/index.astro` with six sections:

**Section 1 — Hero:**
- Tagline: "Your codebase doesn't remember *why*." (48px Geist, "why" in amber)
- CodeBlock component with `showBackreferences=true`
- Caption: italic, muted, "An agent reading this code..."

**Section 2 — Day-2 Problem:**
- H2: "Day 2"
- Three paragraphs (magic on day 1, broken on day 2, problem is missing reasoning)
- "Without context:" subheading
- CodeBlock component with `showBackreferences=false`, `dimmed=true`

**Section 3 — How Does It Get There:**
- H2: "How does it get there?"
- Two paragraphs about chunks and progressive discovery
- Lifecycle visual: Goal → Plan → Implement → Complete (flexbox, Geist Mono)

**Section 4 — Hardcoded Retry Payoff:**
- H2: "The hardcoded retry"
- Paragraph referencing `time.sleep(3)`
- Decision record card (olive background, amber left border):
  - Label: "DECISION RECORD" in Geist Mono uppercase
  - Content: Stripe retry policy explanation
  - Date: 2024-11-15
- Blockquote: "Code can look wrong and be exactly right..."

**Section 5 — Retrofit:**
- H2: "Retrofit, don't rewrite"
- One paragraph about `ve init` on existing projects

**Section 6 — CTA:**
- `<details>` element: `uv tool install vibe-engineer` visible by default
- Summary: "Other install methods" expands to show `pip install vibe-engineer`
- GitHub link, open source badge

Location: `site/src/pages/index.astro`

### Step 8: Create the 404 page

Create `site/src/pages/404.astro`:
- Uses BaseLayout
- "Page not found" in Geist 32px
- Muted body text
- Link back to landing page

Location: `site/src/pages/404.astro`

### Step 9: Create the docs scaffold (hidden)

Create the docs infrastructure without exposing it in navigation:

- `site/src/layouts/DocsLayout.astro` — extends BaseLayout, adds left sidebar
- `site/src/pages/docs/index.astro` — Getting Started stub
- `site/src/pages/docs/concepts.astro` — Concepts stub

The DocsLayout sidebar collapses to a top dropdown on mobile (< 768px). These pages exist and work but are not linked from the Nav component until real content is written.

Location: `site/src/layouts/DocsLayout.astro`, `site/src/pages/docs/`

### Step 10: Create the social card image

Create a simple OG image (1200x630 PNG):
- Dark background (`#0a0a0b`)
- "ve" in Geist Mono, large, centered
- Amber accent element
- Save as `site/public/og-image.png`

This can be a placeholder generated with any image tool or SVG-to-PNG conversion. Refine later.

Location: `site/public/og-image.png`

### Step 11: Set up GitHub Actions deploy workflow

Create `.github/workflows/deploy-site.yml` at the repo root:

```yaml
name: Deploy site to GitHub Pages
on:
  push:
    branches: [main]
    paths: ['site/**', 'DESIGN.md']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: site/.nvmrc
      - uses: actions/cache@v4
        with:
          path: site/node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('site/package-lock.json') }}
      - run: cd site && npm install && npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site/dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

Add Lighthouse CI as a separate job or step (run against the built output).

Location: `.github/workflows/deploy-site.yml`

### Step 12: Verify build and test locally

Run the following locally to verify everything works:
```bash
cd site && npm install && npm run build && npm run preview
```

Check:
- All 6 sections render correctly
- Code blocks have syntax highlighting
- Backreferences display in amber
- Stripped code block is dimmed
- Decision card has olive background + amber border
- Responsive layout works at 320px, 768px, 1024px
- `prefers-color-scheme: light` shows light theme
- 404 page works
- OG tags present in HTML source

## Dependencies

- Node.js 20+ (for Astro build)
- Astro (latest stable)
- Domain `veng.dev` DNS configured to point to GitHub Pages
- GitHub Pages enabled on the repository

## Risks and Open Questions

- **DNS configuration:** veng.dev must be configured with A records pointing to GitHub Pages IPs (185.199.108-111.153) or a CNAME to the GitHub Pages URL. This is a manual step outside the codebase.
- **Umami instance:** The analytics snippet requires a running Umami instance. If not available at launch, the page renders fine without it (graceful degradation). The instance URL is an env var, not hardcoded.
- **Geist font availability:** Geist is available on Google Fonts. If Google Fonts CDN is down, the page falls back to system fonts via `font-display: swap`. Acceptable degradation.
- **Shiki backreference highlighting:** The amber color for backreference comments comes from a CSS override targeting comment tokens that contain `Chunk:`, `Decision:`, or `Subsystem:`. This may need a custom Shiki transformer rather than pure CSS. Test during Step 5.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
