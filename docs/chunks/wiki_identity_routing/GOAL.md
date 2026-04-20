---
status: ACTIVE
ticket: null
parent_chunk: entity_wiki_maintenance_prompt
code_paths:
- src/templates/entity/wiki_schema.md.jinja2
- src/templates/entity/wiki/identity.md.jinja2
code_references:
  - ref: src/templates/entity/wiki_schema.md.jinja2
    implements: "Identity routing guidance — Decision Rubric, reframed identity.md description, updated Maintenance Triggers, Identity.md Health Check, See: convention, and Page Operations table"
  - ref: src/templates/entity/wiki/identity.md.jinja2
    implements: "Hard-Won Lessons comment updated to discourage per-session dumping and encourage principle-level entries with See: links"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- entity_attach_detach
- entity_creation_wiki_prompts
- entity_fork_merge
- entity_from_transcript
- entity_ingest_transcript
- entity_memory_migration
- entity_push_pull
- entity_repo_structure
- entity_shutdown_wiki
- entity_sop_file
- entity_startup_wiki
- entity_wiki_maintenance_prompt
- entity_wiki_schema
- entity_worktree_support
---

# Chunk Goal

## Minor Goal

Refine `wiki_schema.md.jinja2` to prevent identity.md bloat across entity
lifetimes. Field-tested by the `savings-instruments` entity over ~16 sessions:
identity.md drifted from a lean self-model into a ~30-entry catalog of mixed
principles and mechanics. Root cause is the current template's routing guidance,
which defaults findings to identity.md.

### Source material

The `savings-instruments` entity refined their own `wiki_schema.md` after
experiencing the bloat firsthand. Their refined schema is provided inline in
steward channel message at position 56. Use it as the canonical reference.

### Changes to `src/templates/entity/wiki_schema.md.jinja2`

1. **Reframe identity.md description** (line 37, 74-77). Change "the most
   important section" framing to: "who you are and what you value. Lean,
   curated, readable in one sitting. NOT a dumping ground for technical
   findings." Hard-Won Lessons targets ~8-15 principle-level entries with
   See: links to mechanics pages.

2. **Add concrete test** for identity.md routing. "Would this principle still
   apply if the codebase, technology, or project changed completely?" Yes =
   identity, No = domain/techniques. Include worked examples of each.

3. **Add Decision Rubric section**. Branching question sequence that routes
   findings to the correct directory BEFORE touching any file. identity.md
   is the *last* branch, not the first.

4. **Rewrite Maintenance Triggers** (lines 139-150). Remove the
   "discover something was wrong → identity.md" trigger. New triggers route
   mechanics-corrections to domain/, technique-corrections to techniques/,
   and only send updates to identity.md when the *principle itself* changed.

5. **Add Identity.md Health Check section**. Periodic audit: for each
   Hard-Won Lessons entry, apply the codebase-independent test. If it fails,
   move mechanics out. Target ~8-15 entries.

6. **Add "See:" convention**. Every identity.md Hard-Won Lessons entry ends
   with a link to the mechanics page(s). Principle on identity, mechanics in
   domain/techniques; neither duplicates the other.

7. **Add guardrail line**: "Adding to identity.md should be rare. If you find
   yourself adding multiple entries per session, you are most likely dumping
   mechanics there."

8. **Update Page Operations table** to include identity.md-specific operations
   (move mechanics out, run health check when > 15 entries).

9. **Domain and techniques sections** get explicit "absorbs mechanics/recipes"
   framing to make clear they are the default home for findings.

### Also audit `src/templates/entity/wiki/identity.md.jinja2`

Check for instructions that encourage dumping — e.g. the Hard-Won Lessons
section header's comment or default starter content that primes identity.md
as a generic lesson log. Align with the refined schema's guidance.

### Preserve

- All existing jinja2 variable substitutions in the template
- The "Why This Wiki Exists" compounding-artifact framing (added by
  entity_wiki_maintenance_prompt)
- The Operations section (Ingest/Query/Lint)
- The SOP.md entry in directory structure (added by entity_sop_file)
- Cross-reference conventions
- Page conventions (frontmatter, wikilinks, page size)

### Non-goals

- Retroactively migrating existing entities' identity.md files
- Changing directory structure or other established conventions

## Success Criteria

- wiki_schema.md.jinja2 includes the Decision Rubric routing findings away
  from identity.md by default
- identity.md description explicitly says "NOT a dumping ground"
- Maintenance Triggers no longer route corrections to identity.md by default
- Identity.md Health Check section exists with concrete audit procedure
- Hard-Won Lessons has a concrete test ("would this apply if the codebase
  changed?") with worked examples
- "See:" convention documented for linking principles to mechanics
- Guardrail line present about rare identity.md additions
- Existing jinja2 substitutions preserved
- Tests pass

## Relationship to Parent

Parent chunk `entity_wiki_maintenance_prompt` added compounding-artifact
framing and Operations (Ingest/Query/Lint) to the wiki schema template.
This chunk refines the *routing* guidance within that same template — the
rules for which directory a finding goes into. The compounding-artifact
framing and Operations sections are preserved unchanged.

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->