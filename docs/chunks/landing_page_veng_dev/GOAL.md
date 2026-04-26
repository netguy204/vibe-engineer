---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - site/astro.config.mjs
  - site/src/styles/global.css
  - site/src/layouts/BaseLayout.astro
  - site/src/layouts/DocsLayout.astro
  - site/src/components/Nav.astro
  - site/src/components/CodeBlock.astro
  - site/src/pages/index.astro
  - site/src/pages/404.astro
  - site/src/pages/docs/index.astro
  - site/src/data/hero-code.ts
  - site/public/CNAME
  - site/public/favicon.svg
  - site/public/og-image.svg
  - .github/workflows/deploy-site.yml
  - DESIGN.md
code_references:
  - ref: site/src/pages/index.astro
    implements: "Landing page with 6-section persuasion arc and CSS-only tabs"
  - ref: site/src/components/CodeBlock.astro
    implements: "Reusable code block with backreference filtering"
  - ref: site/src/data/hero-code.ts
    implements: "Single source of truth for hero Python code example"
  - ref: site/src/styles/global.css
    implements: "Design system tokens and CSS-only tab mechanics"
  - ref: site/src/layouts/BaseLayout.astro
    implements: "HTML head, OG tags, Umami analytics, accessibility landmarks"
  - ref: site/src/layouts/DocsLayout.astro
    implements: "Docs scaffold with sidebar (hidden from nav)"
  - ref: .github/workflows/deploy-site.yml
    implements: "GitHub Pages deploy pipeline"
  - ref: DESIGN.md
    implements: "Design system specification"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: ["cli_dotenv_walk_parents"]
---

# Chunk Goal

## Minor Goal

Build a static landing page for vibe-engineer at veng.dev. The page sells the workflow by showing its output — code with backreferences — before explaining how it gets there. The goal: a visitor spends 30 seconds on the page and thinks "this is how it should work."

The page structure follows a studied analysis of max.cloud's marketing strategy, adapted for VE's audience (engineers who already know what vibe coding is) and VE's CTA (install immediately, not "get in touch").

### Page Structure

**Section 1 — Hero: The Code**
A realistic e-commerce checkout file with backreference comments throughout. The backreferences link to decision records, chunk goals, and subsystem docs. One detail in the code looks like a bug (a hardcoded 3-second retry delay) but is correct — the backreference points to a decision record explaining a vendor rate-limiter constraint discovered in a production incident. This rewards careful readers and sets up Section 4. Below the code: *"An agent reading this code knows where it came from, why it exists, and what it's allowed to change."*

**Section 2 — The Day-2 Problem**
Three short paragraphs: vibe coding is magic on day 1; on day 2, the agent doesn't know why anything was built the way it was; the problem is that the codebase contains only the result, not the reasoning. Then the same checkout code from the hero, stripped of backreferences. The contrast makes the argument.

**Section 3 — How Does It Get There?**
Light introduction to chunks: small, documented units of change where you write what you're trying to do before the agent implements it. The documentation stays connected to the code it produces. A brief visual showing the chunk lifecycle: Goal → Plan → Implement → Complete. One paragraph on progressive discovery: "Recent research confirms what VE practitioners already know: agents don't benefit from being told everything upfront. They need to discover context progressively, at the point where it's relevant. That's what backreferences and chunk documentation create — a codebase that teaches the agent as it navigates."

**Section 4 — The Hardcoded Retry (payoff)**
Drive home the subtle detail from the hero. Show the decision record the backreference pointed to. The 3-second delay was the only correct answer — the vendor bans clients that retry faster. *"Code can look wrong and be exactly right. Without the reasoning, the next agent to touch it will 'fix' it."*

**Section 5 — Retrofit, Don't Rewrite**
One section addressing the legacy objection head-on. You don't need to have used VE from the start. You can retrofit it onto any existing project.

**Section 6 — CTA**
`pip install vibe-engineer` / `uv tool install vibe-engineer`. One command. Get started.

### Design Principles

- Problem-first framing, not feature-first
- Show, don't tell — the code sample does the arguing
- Lead with the output (backreferenced code), then reveal the workflow that creates it
- Use a hypothetical but relatable example (e-commerce), not VE's own codebase as the primary example
- Tone: technically confident, short sentences, specific claims, no marketing fluff

### Inspiration

Studied max.cloud's landing page strategy. Key techniques adopted:
- Problem-first framing (they open with MCP's pain points)
- Executable/concrete examples as the hero (they show CLI commands)
- "How is this possible?" architectural explanation
- Scenario-based proof points
- Engineer-to-engineer tone

## Success Criteria

- Static landing page exists and can be deployed to veng.dev
- Page contains all six sections described above
- The hero code example is realistic and contains backreferences that feel natural
- The "buggy" hardcoded retry detail is subtle enough to reward close reading but clear enough to drive home Section 4
- The stripped-code contrast in Section 2 is visually clear
- CTA includes working install commands
- Page loads fast (static, no heavy JS frameworks)
- Responsive on mobile

## Rejected Ideas

### Using VE's own codebase as the primary example

We could dogfood by showing VE's own code with backreferences.

Rejected because: when introducing VE to the team, this approach triggered "of course it works on itself" skepticism. People assumed it wouldn't work on legacy projects or that VE's codebase is trivially simple. A hypothetical e-commerce example signals "this works on real-world code" without that baggage. VE's own codebase may appear as a secondary credibility reinforcer.

### "Get in touch" CTA (like max.cloud)

Max.cloud gates behind a contact form, suggesting enterprise focus.

Rejected because: VE is an open-source CLI tool. The audience already knows what vibe coding is. Lower friction wins — let them install and try it immediately.