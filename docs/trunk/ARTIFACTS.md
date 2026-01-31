# VE Artifact Types Reference

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
| Know what needs to be done | Chunk |
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
| `# Chunk:` | Implementation work | Until SUPERSEDED/HISTORICAL |

When you see backreferences, read the referenced artifact to understand the code's context and constraints.

**Do NOT add `# Narrative:` backreferences.** Narratives decompose into chunks; reference the implementing chunk instead.

**Chunk backreferences in multi-project tasks:**

Always use the local path within the current repository (e.g., `docs/chunks/chunk_name`), not cross-repository paths. Each participating project has `external.yaml` pointers for chunks that live in the external artifacts repo.

## External Artifacts {#external-artifacts}

External artifacts enable multi-repository workflows by providing pointers to artifacts in other repositories. When an artifact directory contains `external.yaml` instead of GOAL.md or OVERVIEW.md, it's pointing to content in another repo.

For comprehensive documentation on external artifacts, see [EXTERNAL.md](EXTERNAL.md).
