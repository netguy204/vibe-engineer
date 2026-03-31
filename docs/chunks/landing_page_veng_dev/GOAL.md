---
status: IMPLEMENTING
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
  - site/public/og-image.png
  - .github/workflows/deploy-site.yml
  - DESIGN.md
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: ["cli_dotenv_walk_parents"]
---

<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
║                                                                              ║
║  AGENT INSTRUCTIONS: When editing this file, preserve this entire comment    ║
║  block. Only modify the frontmatter YAML and the content sections below      ║
║  (Minor Goal, Success Criteria, Relationship to Parent). Use targeted edits  ║
║  that replace specific sections rather than rewriting the entire file.       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This comment describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- FUTURE: This chunk is queued for future work and not yet being implemented
- IMPLEMENTING: This chunk is in the process of being implemented.
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only

FUTURE CHUNK APPROVAL REQUIREMENT:
ALL FUTURE chunks require operator approval before committing or injecting.
After refining this GOAL.md, you MUST present it to the operator and wait for
explicit approval. Do NOT commit or inject until the operator approves.
This applies whether triggered by "in the background", "create a future chunk",
or any other mechanism that creates a FUTURE chunk.

COMMIT BOTH FILES: When committing a FUTURE chunk after approval, add the entire
chunk directory (both GOAL.md and PLAN.md) to the commit, not just GOAL.md. The
`ve chunk create` command creates both files, and leaving PLAN.md untracked will
cause merge conflicts when the orchestrator creates a worktree for the PLAN phase.

PARENT_CHUNK:
- null for new work
- chunk directory name (e.g., "006-segment-compaction") for corrections or modifications

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Populated after implementation, before PR
- Uses symbolic references to identify code locations

- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Example:
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
    - ref: src/segment/writer.rs#SegmentWriter::fsync
      implements: "Durability guarantees"
    - ref: src/utils.py#validate_input
      implements: "Input validation logic"


NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name.
- When setting this field during /chunk-create, also update the narrative's OVERVIEW.md
  frontmatter to add this chunk to its `chunks` array with the prompt and chunk_directory.
- If this is the final chunk of a narrative, the narrative status should be set to COMPLETED
  when this chunk is completed.

INVESTIGATION:
- If this chunk was derived from an investigation's proposed_chunks, reference the investigation
  directory name (e.g., "memory_leak" for docs/investigations/memory_leak/).
- This provides traceability from implementation work back to exploratory findings.
- When implementing, read the referenced investigation's OVERVIEW.md for context on findings,
  hypotheses tested, and decisions made during exploration.
- Validated by `ve chunk validate` to ensure referenced investigations exist.


SUBSYSTEMS:
- Optional list of subsystem references that this chunk relates to
- Format: subsystem_id is the subsystem directory name, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "validation"
      relationship: implements
    - subsystem_id: "frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section.

FRICTION_ENTRIES:
- Optional list of friction entries that this chunk addresses
- Provides "why did we do this work?" traceability from implementation back to accumulated pain points
- Format: entry_id is the friction entry ID (e.g., "F001"), scope is "full" or "partial"
  - "full": This chunk fully resolves the friction entry
  - "partial": This chunk partially addresses the friction entry
- When to populate: During /chunk-create if this chunk addresses known friction from FRICTION.md
- Example:
  friction_entries:
    - entry_id: F001
      scope: full
    - entry_id: F003
      scope: partial
- Validated by `ve chunk validate` to ensure referenced friction entries exist in FRICTION.md
- When a chunk addresses friction entries and is completed, those entries are considered RESOLVED

BUG_TYPE:
- Optional field for bug fix chunks that guides agent behavior at completion
- Values: semantic | implementation | null (for non-bug chunks)
  - "semantic": The bug revealed new understanding of intended behavior
    - Code backreferences REQUIRED (the fix adds to code understanding)
    - On completion, search for other chunks that may need updating
    - Status → ACTIVE (the chunk asserts ongoing understanding)
  - "implementation": The bug corrected known-wrong code
    - Code backreferences MAY BE SKIPPED (they don't add semantic value)
    - Focus purely on the fix
    - Status → HISTORICAL (point-in-time correction, not an ongoing anchor)
- Leave null for feature chunks and other non-bug work

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/foo/migrate.py)
- These artifacts help future archaeologists understand what the chunk did
- Unlike code in src/, chunk artifacts are not expected to be maintained long-term
- Examples: data migration scripts, one-time fixups, analysis tools used during implementation

CREATED_AFTER:
- Auto-populated by `ve chunk create` - DO NOT MODIFY manually
- Lists the "tips" of the chunk DAG at creation time (chunks with no dependents yet)
- Tips must be ACTIVE chunks (shipped work that has been merged)
- Example: created_after: ["auth_refactor", "api_cleanup"]

IMPORTANT - created_after is NOT implementation dependencies:
- created_after tracks CAUSAL ORDERING (what work existed when this chunk was created)
- It does NOT mean "chunks that must be implemented before this one can work"
- FUTURE chunks can NEVER be tips (they haven't shipped yet)

COMMON MISTAKE: Setting created_after to reference FUTURE chunks because they
represent design dependencies. This is WRONG. If chunk B conceptually depends on
chunk A's implementation, but A is still FUTURE, B's created_after should still
reference the current ACTIVE tips, not A.

WHERE TO TRACK IMPLEMENTATION DEPENDENCIES:
- Investigation proposed_chunks ordering (earlier = implement first)
- Narrative chunk sequencing in OVERVIEW.md
- Design documents describing the intended build order
- The `created_after` field will naturally reflect this once chunks ship

DEPENDS_ON:
- Declares explicit implementation dependencies that affect orchestrator scheduling
- Format: list of chunk directory name strings, or null
- Default: [] (empty list - explicitly no dependencies)

VALUE SEMANTICS (how the orchestrator interprets this field):

| Value             | Meaning                              | Oracle behavior   |
|-------------------|--------------------------------------|-------------------|
| `null` or omitted | "I don't know my dependencies"       | Consult oracle    |
| `[]` (empty list) | "I explicitly have no dependencies"  | Bypass oracle     |
| `["chunk_a"]`     | "I depend on these specific chunks"  | Bypass oracle     |

CRITICAL: The default `[]` means "I have analyzed this chunk and it has no dependencies."
This is an explicit assertion, not a placeholder. If you haven't analyzed dependencies yet,
change the value to `null` (or remove the field entirely) to trigger oracle consultation.

WHEN TO USE EACH VALUE:
- Use `[]` when you have analyzed the chunk and determined it has no implementation dependencies
  on other chunks in the same batch. This tells the orchestrator to skip conflict detection.
- Use `null` when you haven't analyzed dependencies yet and want the orchestrator's conflict
  oracle to determine if this chunk conflicts with others.
- Use `["chunk_a", "chunk_b"]` when you know specific chunks must complete before this one.

WHY THIS MATTERS:
The orchestrator's conflict oracle adds latency and cost to detect potential conflicts.
When you declare `[]`, you're asserting independence and enabling the orchestrator to
schedule immediately. When you declare `null`, you're requesting conflict analysis.

PURPOSE AND BEHAVIOR:
- When a list is provided (empty or not), the orchestrator uses it directly for scheduling
- When null, the orchestrator consults its conflict oracle to detect dependencies heuristically
- Dependencies express order within a single injection batch (intra-batch scheduling)
- The chunks listed in depends_on will be scheduled to complete before this chunk starts

CONTRAST WITH created_after:
- `created_after` tracks CAUSAL ORDERING (what work existed when this chunk was created)
- `depends_on` tracks IMPLEMENTATION DEPENDENCIES (what must complete before this chunk runs)
- `created_after` is auto-populated at creation time and should NOT be modified manually
- `depends_on` is agent-populated based on design requirements and may be edited

WHEN TO DECLARE EXPLICIT DEPENDENCIES:
- When you know chunk B requires chunk A's implementation to exist before B can work
- When the conflict oracle would otherwise miss a subtle dependency
- When you want to enforce a specific execution order within a batch injection
- When a narrative or investigation explicitly defines chunk sequencing

EXAMPLE:
  # Chunk has no dependencies (explicit assertion - bypasses oracle)
  depends_on: []

  # Chunk dependencies unknown (triggers oracle consultation)
  depends_on: null

  # Chunk B depends on chunk A completing first
  depends_on: ["auth_api"]

  # Chunk C depends on both A and B completing first
  depends_on: ["auth_api", "auth_client"]

VALIDATION:
- `null` is valid and triggers oracle consultation
- `[]` is valid and means "explicitly no dependencies" (bypasses oracle)
- Referenced chunks should exist in docs/chunks/ (warning if not found)
- Circular dependencies will be detected at injection time
- Dependencies on ACTIVE chunks are allowed (they've already completed)
-->

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