<!-- Chunk: docs/chunks/progressive_disclosure_refactor - Extracted artifact documentation -->
<!-- Chunk: docs/chunks/intent_principles - Cross-reference to CHUNKS.md added -->
# VE Artifact Types Reference

> Before working with chunks, read [docs/trunk/CHUNKS.md](CHUNKS.md) — the canonical statement of what chunks are for and how their status is interpreted.

Beyond chunks (the core unit of work), VE supports several artifact types for different scenarios.

## Narratives {#narratives}

Narratives are multi-chunk initiatives that capture a high-level ambition decomposed into implementation steps. Each narrative directory (`docs/narratives/<name>/`) contains an OVERVIEW.md with:

- **Advances Trunk Goal** - How this narrative advances the project's goals
- **Proposed Chunks** - List of chunk prompts and their corresponding chunk directories

**When to use narratives:**
- When you have a clear multi-step goal that can be decomposed upfront
- When the initiative is too large for a single chunk
- When you want to track progress across related chunks

**Frontmatter pattern:**

Chunks may reference their parent narrative:
```yaml
narrative: my_initiative
```

When you see this, read `docs/narratives/my_initiative/OVERVIEW.md` to understand the larger initiative.

## Investigations {#investigations}

Investigations are exploratory documents for understanding something before committing to action. Each investigation (`docs/investigations/<name>/`) contains an OVERVIEW.md with:

- **Trigger** - What prompted the investigation
- **Success Criteria** - What "done" looks like
- **Testable Hypotheses** - Beliefs to verify or falsify
- **Proposed Chunks** - Work items that emerge from findings

**Investigation status values:** `ONGOING`, `SOLVED`, `NOTED`, `DEFERRED`

**When to use investigations:**
- When you need to understand before acting
- When diagnosing unclear issues
- When exploring unfamiliar code
- When validating hypotheses

**Frontmatter pattern:**

Chunks may reference the investigation they emerged from:
```yaml
investigation: memory_leak
```

**Choosing between artifacts:**

| Scenario | Use |
|----------|-----|
| Clear intent to capture (see [CHUNKS.md](CHUNKS.md) principle 2) | Chunk |
| Need to understand first | Investigation |
| Clear multi-step goal | Narrative |
| Pain point to remember | Friction Log |

## Subsystems {#subsystems}

Subsystems document emergent architectural patterns discovered in the codebase. Each subsystem (`docs/subsystems/<name>/`) contains an OVERVIEW.md describing:

- **Intent** - What the subsystem accomplishes
- **Scope** - What's in and out of scope
- **Invariants** - Rules that must always hold
- **Code References** - Symbolic references to implementations with compliance levels

**Subsystem status values:** `DISCOVERING`, `DOCUMENTED`, `REFACTORING`, `STABLE`, `DEPRECATED`

**When to check subsystems:**
- Before implementing patterns that might already exist
- When you see `# Subsystem:` backreferences in code
- When touching areas that span multiple files with shared patterns

**Status affects your behavior:**

| Status | Behavior |
|--------|----------|
| `DISCOVERING` / `DOCUMENTED` | Pattern documented but may have inconsistencies. Do NOT expand scope to fix inconsistencies unless asked. |
| `REFACTORING` | Active consolidation. You MAY expand scope for consistency. |
| `STABLE` | Authoritative. Follow its patterns for new code. |
| `DEPRECATED` | Avoid using; may suggest alternatives. |

## Friction Log {#friction-log}

The friction log (`docs/trunk/FRICTION.md`) is an accumulative ledger for capturing pain points encountered during project use:

- **Indefinite lifespan**: A friction log is like a journal—you don't "complete" it
- **Contains many entries**: Each entry is a distinct friction point
- **No artifact-level status**: The log is always active; only entries have lifecycle

**Entry format:**
```markdown
### FXXX: YYYY-MM-DD [theme-id] Title

Description of the friction point and context.
```

**Entry lifecycle (derived, not stored):**
- **OPEN**: Entry ID not in any `proposed_chunks.addresses`
- **ADDRESSED**: Entry ID appears in a proposed chunk that has been created
- **RESOLVED**: Entry is addressed by a chunk that has reached ACTIVE status

When friction accumulates (3+ entries in a theme), add a proposed chunk to the friction log frontmatter.

Use `/friction-log` to quickly capture a friction point.

## VE Hooks {#hooks}

A VE hook is a project's own requirements for one lifecycle command, written to
`docs/hooks/<command-name>.md`. Every plugin command loads its hook into the
context block at the top of the command, so the content arrives precisely when
the phase it governs is running.

```
docs/hooks/chunk-complete.md    # loaded by /chunk-complete
docs/hooks/chunk-create.md      # loaded by /chunk-create
docs/hooks/narrative-create.md  # loaded by /narrative-create
```

**Format**: Markdown. Optional YAML frontmatter (no keys are meaningful today);
the body is the instruction, passed to the agent verbatim.

```markdown
Did this chunk change anything in the public-facing documentation?
If it did, update it before reporting the chunk complete.
```

**Naming**: the filename must exactly match a command name — `chunk-complete.md`,
not `chunk-completed.md` or `complete.md`. A filename matching no command is
well-formed and will silently never fire, so `ve hooks list` and `ve validate`
both flag it as a warning.

**Hooks are advisory.** They are prompt content, not enforced checks: an agent
is instructed to satisfy them and to surface conflicts with the command's own
instructions, but nothing verifies compliance. Use them for judgement-shaped
requirements ("check whether X needs updating"), not for guarantees. See DEC-016.

**Not to be confused with Claude Code plugin hooks** (`hooks/hooks.json`,
`hooks/session_start.sh`), which are a harness-level mechanism firing on session
events like `SessionStart`. The two are unrelated.

Use `ve hooks list` to see the hooks a project defines and `ve hooks show
<command-name>` to preview what a command will receive.

## Deletion Grants {#deletion-grants}

The deletion-grant ledger (`docs/trunk/DELETIONS.md`) records operator-authorized reference deletions. Deleting a backreference or `code_references` entry is normally out of vocabulary for validation fix loops — a reference is somebody's record of governing intent. When code was deliberately deleted and the operator explicitly authorizes removing the reference to it, the grant is recorded **before** the reference is removed:

```bash
ve exists <name>                 # evidence of absence: does this path/symbol exist anywhere visible?
ve deletion record <reference> --location <file:line> --by <operator> --reason "<why>" --evidence "<summary>"
```

The ledger is created by `ve deletion record` on first use (never by hand), so the authorization lands in the same diff as the deletion and a reviewer can see the grant. `ve deletion list` shows recorded grants.

## Proposed Chunks

The `proposed_chunks` frontmatter field is a cross-cutting pattern used in narratives, investigations, and friction logs to track work that has been proposed but not yet created:

```yaml
proposed_chunks:
  - prompt: "Add caching to user lookups"
    chunk_directory: null  # Set when chunk is created
```

Use `ve chunk list-proposed` to see all proposed chunks across the project.

## Code Backreferences

Source code may contain comments linking back to documentation:

```python
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/auth_refactor - Authentication system redesign
```

**Valid backreference types:**

| Type | Purpose | Lifespan |
|------|---------|----------|
| `# Subsystem:` | Architectural pattern | Enduring |
| `# Chunk:` | Implementation work | Until HISTORICAL |

When you see backreferences, read the referenced artifact to understand the code's context and constraints.

References are maintained under the rename mandate (see CLAUDE.md, "File Moves and Renames"): any file move or rename must update every reference that names the old path — chunk `code_paths` and `ref:` fields included — validated with `uvx --from vibe-engineer ve validate`.

**Do NOT add `# Narrative:` backreferences.** Narratives decompose into chunks; reference the implementing chunk instead.

**Chunk backreferences in multi-project tasks:**

Always use the local path within the current repository (e.g., `docs/chunks/chunk_name`), not cross-repository paths. Each participating project has `external.yaml` pointers for chunks that live in the external artifacts repo.

<!-- Chunk: docs/chunks/claudemd_external_prompt - External Artifacts section with redirect to EXTERNAL.md -->
<!-- Chunk: docs/chunks/progressive_disclosure_external - Simplified external artifacts section -->
<!-- Chunk: docs/chunks/federation_peer_refs - Peer pointers and the point-vs-promote rule -->
## External Artifacts {#external-artifacts}

External artifacts are pointers: an artifact directory containing `external.yaml` instead of GOAL.md or OVERVIEW.md, recording where the real document lives. A pointer either names another repository (`repo: org/repo`, resolved by fetching a tracked branch) or another VE tree in the same working copy (`tree: <member>`, resolved through the workspace manifest — no fetch, no branch). Either kind may carry a `why:` line saying what this tree depends on in the target, which turns the pointer into a legible interest edge.

Ownership stays with the tree whose code enforces an intent; other trees express interest with pointers at their own level. **Point when readers multiply; promote when writers change** — moving an artifact to the root tree is an ownership transfer, not a way to make it visible.

For comprehensive documentation on external artifacts, see [EXTERNAL.md](EXTERNAL.md).
