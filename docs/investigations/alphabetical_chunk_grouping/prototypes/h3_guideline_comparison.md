# H3: Prescriptive vs Characteristic Guidelines

## Prescriptive Guidelines (Expected to fail)

These tell you WHAT prefix to use:

### Example 1: Category-based
```
- Use `cli_` for commands
- Use `model_` for data models
- Use `migration_` for data migrations
- Use `docs_` for documentation updates
- Use `fix_` for bug fixes
- Use `feature_` for new features
```

**Why this fails:**
- "What category is a command that migrates data?" → ambiguous
- Creates superclusters (all commands lumped together)
- Creates "other" buckets for things that don't fit
- Strips semantic meaning (two unrelated fixes both become `fix_*`)

### Example 2: Artifact-type-based
```
- Use `chunk_` for chunk-related work
- Use `subsystem_` for subsystem work
- Use `narrative_` for narrative work
- Use `investigation_` for investigation work
```

**Why this fails:**
- This is what current organic naming naturally does
- Creates superclusters (`chunk_*` = 7, `subsystem_*` = 6)
- Semantically unrelated work groups together
- "chunk_validate" and "chunk_create_task_aware" have nothing in common except artifact type

---

## Characteristic Guidelines (Might work)

These tell you HOW to choose a prefix, not what prefix to use:

### Draft 1: The "Initiative Noun" Rule

```
Name chunks by the INITIATIVE they belong to, not the artifact or action.

Ask: "What multi-chunk effort does this advance?"

Good prefixes: ordering, taskdir, template, crossref
Bad prefixes: chunk, fix, update, cli, add, implement

The prefix should be a NOUN that names the initiative, not:
- The artifact type being modified (chunk, subsystem)
- The action being taken (fix, add, update, implement)
- The technical category (cli, model, migration)
```

**Test against existing chunks:**

| Current Name | Initiative | Better Name |
|--------------|------------|-------------|
| `chunk_create_task_aware` | Task directory | `taskdir_chunk_create` |
| `remove_sequence_prefix` | Causal ordering | `ordering_remove_sequence_prefix` |
| `canonical_template_module` | Template system | `template_canonical_module` |
| `fix_ticket_frontmatter_null` | Frontmatter | `frontmatter_fix_null_ticket` |

### Draft 2: The "Specificity" Rule

```
Choose the MOST SPECIFIC noun that:
1. Could apply to 2-8 other chunks (not a singleton)
2. Couldn't apply to 10+ chunks (not a supercluster)
3. Names the domain concept, not the technical operation

Ask: "What would a new team member search for to find related work?"
```

**Example application:**

For `chunk_create_task_aware`:
- "chunk" → too broad (7+ chunks)
- "create" → too generic (action verb)
- "task" → just right (6 related chunks exist)
- "task_aware" → too specific (only 3 chunks have this exact pattern)

Suggested: `task_create_chunk` or `taskdir_chunk_create`

### Draft 3: The "First Chunk Seeds the Cluster" Rule

```
When creating the FIRST chunk in a potential cluster:
- Choose a noun that describes the problem domain
- Avoid generic terms (api, data, util, misc, core)
- Prefer compound nouns that narrow scope (taskdir vs task, crossref vs ref)

When creating SUBSEQUENT chunks:
- Check semantic similarity to existing chunks
- If similar chunks share a prefix, adopt that prefix
- If no cluster exists, you're seeding a new one—choose carefully
```

---

## Analysis

**Prescriptive guidelines** fail because:
1. Categories are ambiguous at boundaries
2. They force false groupings
3. They create "other" buckets
4. They strip semantic information

**Characteristic guidelines** might work because:
1. They're testable ("could this apply to 2-8 other chunks?")
2. They preserve semantic meaning
3. They adapt to the domain naturally
4. They don't require maintaining a category list

**Key insight:** The guideline should be a QUESTION to ask, not a RULE to follow.

- Bad: "Commands should be prefixed with cli_"
- Good: "What initiative does this chunk advance? Use that noun."
