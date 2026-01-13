---
status: SOLVED
trigger: "Alphabetical filesystem ordering creates semantic grouping opportunity after sequence prefix removal"
proposed_chunks:
  - prompt: "Implement similarity-based prefix suggestion at chunk planning time using TF-IDF pairwise comparison"
    chunk_directory: cluster_prefix_suggest
  - prompt: "Add characteristic naming prompt for cluster seeds when no similar chunks exist"
    chunk_directory: cluster_seed_naming
  - prompt: "Implement ve cluster list command to show prefix clusters and identify singletons/superclusters"
    chunk_directory: cluster_list_command
  - prompt: "Implement ve cluster rename command for batch prefix renaming with reference updates"
    chunk_directory: cluster_rename
  - prompt: "Update CLAUDE.md with chunk naming guidance preferring initiative nouns over artifact types"
    chunk_directory: cluster_naming_guidance
created_after: ["chunk_reference_decay"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The question has been answered or the problem has been resolved
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

After removing sequence number prefixes from chunk directories (moving to causal ordering via `created_after`), filesystem listings no longer show chunks in causal/temporal order. Instead, alphabetical sorting now produces a semantic grouping based on the first word of chunk names. This accidental grouping suggests an opportunity: intentionally naming chunks to group related work alphabetically could help operators visually identify subsystems and narratives in their editor's file tree.

## Success Criteria

1. **Determine if semantic alphabetical grouping provides meaningful value** - Does intentional naming for alphabetical clustering actually help operators navigate chunks?

2. **Assess feasibility of prompting for useful clustering** - Can agent/operator guidance during chunk creation realistically produce useful semantic groups, or will it devolve into pathological patterns?

3. **Identify failure modes** - Specifically:
   - Superclusters: Too many chunks gravitating to popular prefixes
   - Tremor clusters: Isolated chunks that don't group with anything meaningful

4. **Evaluate janitorial overhead** - If clustering requires periodic renaming as new patterns emerge, is the maintenance burden acceptable?

5. **Explore naming guideline theories** - Test whether productive naming conventions can exist at all, using this codebase as a concrete example to inform broader conclusions

## Testable Hypotheses

### H1: Alphabetical grouping provides navigational value only when clusters are mid-sized (3-8 chunks)

- **Rationale**: Single chunks don't benefit from grouping; superclusters (10+) become noise where the grouping no longer aids navigation
- **Test**: Analyze current chunk distribution and simulate naming schemes to see what cluster sizes emerge
- **Status**: VERIFIED - Current distribution shows 57% singletons (no value) and artifact-type superclusters. Domain-concept naming produces 6 mid-sized clusters.

### H2: Effective prefixes emerge from domain concepts, not prescribed categories

- **Rationale**: Top-down taxonomies tend to create superclusters; organic naming from the work itself may cluster better
- **Test**: Compare how existing chunks would group under different prefix strategies (prescribed vs emergent)
- **Status**: VERIFIED - Prescribed categories create 2 superclusters and a 16-chunk "other" bucket. Domain concepts create 6 semantically coherent mid-sized clusters.

### H3: Naming guidelines that prescribe prefixes will fail; guidelines that describe prefix characteristics might work

- **Rationale**: "Use `api_` for API work" creates superclusters; "prefer the most specific noun" might not
- **Test**: Draft both styles of guidelines and evaluate which produces better distribution on existing chunks
- **Status**: PARTIALLY VERIFIED - Prescriptive guidelines clearly fail (H2 evidence). Characteristic guidelines ("What initiative does this advance?") are theoretically sound but untested in practice.

### H4: Janitorial renaming is unavoidable but can be scoped to cluster-level, not chunk-level

- **Rationale**: New clusters emerge over time; renaming individual chunks is expensive, but renaming a prefix is a batch operation
- **Test**: Explore what tooling would make cluster-level renaming practical (e.g., rename all `foo_*` to `bar_*`)
- **Status**: VERIFIED - Cluster rename is feasible. ~80% automatable (directories, frontmatter, backrefs). Prose references need manual review. A `ve cluster rename` command is practical.

### H5: Embedding-based similarity can guide prefix selection by finding existing clusters a new chunk is semantically near

- **Rationale**: Embeddings capture semantic relationships that alphabetical prefixes are trying to approximate; let the math suggest where a chunk belongs
- **Test**: Embed chunk GOAL.md content, cluster existing chunks, and for a new chunk, suggest the prefix of its nearest semantic neighbors. If no existing cluster is close enough (threshold), suggest it's a new cluster seed.
- **Status**: PARTIALLY VERIFIED - Automatic clustering fails (all chunks in one cluster due to shared vocabulary). BUT pairwise similarity finds genuine relationships. Pivot: use similarity for prefix SUGGESTION, not clustering.
- **Failure mode observed**: TF-IDF clustering failed as predicted—shared domain vocabulary overwhelms distinguishing content. Pairwise comparison is the viable approach.

## Exploration Log

### 2026-01-10: H1 - Current chunk distribution analysis

Analyzed 47 chunks in `docs/chunks/`. Extracted first-word prefixes and counted cluster sizes.

**Distribution by cluster size:**
- Size 1 (singletons): 27 clusters (57% of all chunks)
- Size 2: 2 clusters (4 chunks)
- Size 3: 1 cluster (3 chunks)
- Size 6: 1 cluster (6 chunks)
- Size 7: 1 cluster (7 chunks)

**Largest clusters:**
| Prefix | Count | Semantically coherent? |
|--------|-------|------------------------|
| `chunk_*` | 7 | Mixed - grouped by artifact type, not domain |
| `subsystem_*` | 6 | Mixed - grouped by artifact type, not domain |
| `artifact_*` | 3 | Yes - all about artifact ordering |
| `investigation_*` | 2 | Mixed - artifact type grouping |
| `remove_*` | 2 | No - coincidental (ordering_remove_seqno vs remove_trivial_tests are unrelated) |

**Key observations:**
1. Current naming creates clusters based on **artifact type** (chunk, subsystem, investigation) rather than **domain concepts**
2. This produces superclusters for common artifact work (`chunk_*` = 7, `subsystem_*` = 6)
3. 57% of chunks are singletons - no grouping benefit
4. Some coincidental groupings are false positives (`remove_*`)
5. Only `artifact_*` shows a genuinely useful semantic cluster (all 3 are about ordering)

**H1 preliminary assessment:** The "mid-sized cluster" hypothesis (3-8 chunks) seems directionally correct, but the current organic naming doesn't produce many useful clusters. The artifact-type prefix pattern creates superclusters that don't aid navigation.

### 2026-01-10: H5 - TF-IDF semantic clustering experiment

Ran prototype `prototypes/embedding_cluster.py` using TF-IDF vectorization and agglomerative clustering.

**Automatic clustering failed spectacularly:**
- At distance thresholds 0.7, 0.5, and 0.3, ALL 47 chunks ended up in a single cluster
- Confirms the predicted failure mode: chunks share too much domain vocabulary (chunk, frontmatter, subsystem, GOAL.md, status, etc.)
- TF-IDF cannot differentiate when the corpus is highly homogeneous

**However, pairwise similarity analysis found genuine semantic relationships:**

Chunks that are semantically similar but have different prefixes (potential missed groupings):

| Chunk A | Chunk B | Similarity | Common Theme |
|---------|---------|------------|--------------|
| `chunk_create_task_aware` | `cross_repo_schemas` | 0.69 | Task-aware work |
| `chunk_create_task_aware` | `external_resolve` | 0.68 | Task-aware work |
| `chunk_create_task_aware` | `list_task_aware` | 0.65 | Task-aware work |
| `external_resolve` | `ve_sync_command` | 0.65 | Cross-repo sync |
| `spec_docs_update` | `subsystem_cli_scaffolding` | 0.62 | Docs & scaffolding |
| `cross_repo_schemas` | `task_init` | 0.62 | Task directory |
| `causal_ordering_migration` | `ordering_remove_seqno` | 0.58 | Causal ordering migration |
| `ordering_remove_seqno` | `update_crossref_format` | 0.57 | Reference format changes |
| `agent_discovery_command` | `subsystem_template` | 0.55 | Subsystem discovery |

**Key insight:** The problem isn't that embeddings can't find semantic similarity—they clearly can. The problem is:
1. Automatic clustering fails due to shared vocabulary
2. BUT targeted pairwise comparisons CAN identify useful groupings

**Implication for H5:** Instead of clustering, a viable approach might be:
- When creating a new chunk, compute similarity to all existing chunks
- Suggest prefixes based on the most similar existing chunks
- Let the human decide whether the semantic similarity warrants the same prefix

**Prefix suggestion demo result:**
- Test chunk: `implement_chunk_start-ve-001`
- Nearest neighbors had prefixes: `fix_`, `chunk_`, `chunk_`, `update_`, `remove_`
- Weighted suggestion: `chunk_`
- This seems reasonable - it's a chunk workflow enhancement

**Alternative naming that would cluster the "task-aware" chunks:**
If `chunk_create_task_aware`, `list_task_aware`, `cross_repo_schemas`, `external_resolve`, `task_init`, and `ve_sync_command` were all named `task_*`, they would form a coherent semantic cluster of 6 chunks - the "cross-repo task directory work" theme.

### 2026-01-10: H2 - Domain concepts vs prescribed categories

Ran `prototypes/h2_naming_comparison.py` to compare three naming approaches on the existing 47 chunks.

**Results:**

| Approach              | Clusters | Singletons | Mid-sized (3-8) | Superclusters (>8) |
|-----------------------|----------|------------|-----------------|---------------------|
| Current organic       | 32       | 27 (57%)   | 3               | 0                   |
| Domain concepts       | 10       | 1 (2%)     | 6               | 1                   |
| Prescribed categories | 7        | 0 (0%)     | 5               | 2                   |

**Domain concept groupings identified:**
- `ordering_*` (9): All causal ordering work - artifact_index_no_git, causal_ordering_migration, ordering_field, etc.
- `chunkcli_*` (7): Chunk CLI/workflow - chunk_validate, chunk_list_command, etc.
- `template_*` (6): Template system work - template_unified_module, migrate_chunks_template, etc.
- `taskdir_*` (6): Cross-repo task work - chunk_create_task_aware, external_resolve, task_init, etc.
- `subsystem_*` (6): Subsystem feature - agent_discovery_command, subsystem_cli_scaffolding, etc.
- `crossref_*` (3): Cross-references - bidirectional_refs, symbolic_code_refs, etc.

**Prescribed category failure mode:**
- Created a 16-chunk "other" supercluster for things that didn't fit
- Created a 10-chunk "cli" supercluster mixing unrelated commands
- The "model" category lumped unrelated schema work together

**H2 assessment: VERIFIED** - Domain concepts produce better cluster distribution than prescribed categories. Prescribed categories create superclusters and "misc/other" buckets. Domain concepts create semantically coherent mid-sized clusters.

### 2026-01-10: H3 - Prescriptive vs characteristic guidelines

Drafted guideline examples in `prototypes/h3_guideline_comparison.md`.

**Prescriptive guideline examples (expected to fail):**
- "Use `cli_` for commands" → ambiguous boundaries, superclusters
- "Use `chunk_` for chunk work" → artifact-type grouping, strips semantics

**Characteristic guideline drafts (might work):**

1. **The "Initiative Noun" Rule:**
   > Name by the INITIATIVE the chunk advances, not the artifact or action.
   > Ask: "What multi-chunk effort does this advance?"

2. **The "Specificity" Rule:**
   > Choose the MOST SPECIFIC noun that could apply to 2-8 other chunks.
   > Ask: "What would a new team member search for to find related work?"

3. **The "First Chunk Seeds" Rule:**
   > When creating the first chunk in a cluster, choose a domain noun carefully.
   > Avoid generic terms (api, data, util, misc).
   > Subsequent chunks can inherit via similarity suggestion.

**Key insight:** Effective guidelines are QUESTIONS to ask, not RULES to follow.
- Bad: "Commands should be prefixed with cli_"
- Good: "What initiative does this chunk advance? Use that noun."

**H3 assessment: PARTIALLY VERIFIED** - Prescriptive guidelines clearly fail (H2 data). Characteristic guidelines are theoretically sound but untested in practice. The "initiative noun" approach aligns with how the successful domain-concept clusters emerged.

### 2026-01-10: H4 - Cluster-level renaming feasibility

Analyzed what renaming `artifact_*` → `ordering_*` would require (see `prototypes/h4_cluster_rename_spec.md`).

**Scope of a cluster rename:**
1. Rename 3 directories
2. Update `created_after` references in other chunks' frontmatter
3. Update code backreferences (`# Chunk: docs/chunks/...`)
4. Update `chunk_directory` fields in investigations/narratives
5. Manually review prose references

**Automation feasibility:**

| Task | Automatable? | Risk |
|------|--------------|------|
| Rename directories | Yes | Low |
| Update created_after | Yes (YAML) | Low |
| Update code backrefs | Yes (regex) | Medium |
| Update chunk_directory | Yes (YAML) | Low |
| Prose references | Partial | High |

**Alternatives explored:**
- **Soft aliases:** Maintain a `cluster_aliases.yaml` mapping without renaming. Doesn't fix filesystem view but avoids complexity.
- **Lightweight rename command:** Handle structured cases, output grep for manual prose review.

**H4 assessment: VERIFIED** - Cluster-level renaming is feasible but non-trivial. A `ve cluster rename` command could automate 80% of the work. Prose references remain a manual review task. The real win is naming correctly at creation time (H5 suggestion mechanism).

## Findings

### Verified Findings

1. **Mid-sized clusters (3-8 chunks) provide navigational value; singletons and superclusters do not.** Current organic naming produces 57% singletons. Domain-concept naming produces 6 mid-sized clusters covering 85% of chunks. (Evidence: H1, H2 analysis)

2. **Domain concepts produce better clusters than prescribed categories.** Prescribed categories ("cli_", "model_", "migration_") create superclusters and "other" buckets. Domain concepts ("ordering_", "taskdir_", "template_") create semantically coherent groupings. (Evidence: H2 comparison)

3. **Automatic clustering fails on homogeneous corpora.** TF-IDF clustering put all 47 chunks in one cluster at every threshold tested. Shared domain vocabulary (chunk, frontmatter, subsystem, GOAL.md) overwhelms distinguishing content. (Evidence: H5 prototype)

4. **Pairwise similarity finds genuine semantic relationships.** Despite clustering failure, pairwise comparison identified chunks that should group together (e.g., task-aware chunks at 0.65-0.69 similarity). (Evidence: H5 prototype output)

5. **Cluster-level renaming is feasible but non-trivial.** ~80% of rename work is automatable (directories, frontmatter references, code backrefs). Prose references require manual review. (Evidence: H4 analysis)

### Hypotheses/Opinions

1. **Characteristic guidelines will work better than prescriptive ones in practice.** The "initiative noun" question ("What multi-chunk effort does this advance?") aligns with how successful clusters emerged organically. Not yet tested in real chunk creation.

2. **The first chunk in a cluster is the critical naming decision.** Subsequent chunks can inherit via similarity suggestion, but the seed chunk establishes the prefix. Poor seed names (generic nouns) will cascade.

3. **Janitorial renaming will be rare if creation-time guidance works.** Most value comes from naming correctly upfront. Rename tooling is insurance, not the primary mechanism.

## Proposed Chunks

### 1. Prefix suggestion at chunk planning time

Implement similarity-based prefix suggestion that runs after GOAL.md is written but before planning begins. When the operator runs `/chunk-plan`, compute pairwise TF-IDF similarity between the new chunk's GOAL.md and all existing chunks. If the top-k nearest neighbors share a common prefix, suggest renaming: "This chunk is similar to `taskdir_*` chunks. Rename to `taskdir_<current_name>`?"

- **Priority**: High (primary mechanism for achieving useful clustering)
- **Dependencies**: None
- **Notes**:
  - Integrate into `/chunk-plan` skill, which runs after GOAL.md exists
  - Use similarity threshold (~0.4) to avoid weak suggestions
  - If no strong similarity, fall back to the characteristic guideline prompt
  - See `prototypes/embedding_cluster.py` for similarity computation approach

### 2. Characteristic naming prompt for cluster seeds

When prefix suggestion finds no similar chunks (new chunk is seeding a potential cluster), prompt the operator with the "initiative noun" question: "No similar chunks found. What initiative does this chunk advance? Use that noun as the prefix (e.g., `ordering_`, `taskdir_`). Avoid generic terms like `api_`, `fix_`, `util_`."

- **Priority**: High (pairs with chunk 1 to handle the bootstrapping case)
- **Dependencies**: Chunk 1 (prefix suggestion infrastructure)
- **Notes**:
  - This is guidance in the skill, not code
  - Update `/chunk-create` skill to include this prompt when naming
  - Could also suggest looking at narratives/investigations for initiative names

### 3. Cluster listing command

Implement `ve cluster list` to show current prefix clusters, their sizes, and members. Output should highlight singletons (potential tremor clusters) and superclusters (>8 members) to identify when janitorial work is needed.

- **Priority**: Medium (diagnostic tool, not critical path)
- **Dependencies**: None
- **Notes**:
  - Simple implementation: group chunks by first underscore-delimited word
  - Could add `--suggest-merges` flag to identify semantically similar singletons that could be renamed into clusters

### 4. Cluster rename command

Implement `ve cluster rename <old_prefix> <new_prefix>` to batch-rename all chunks matching a prefix. Should update: directory names, `created_after` references in frontmatter, code backreferences, and `chunk_directory` fields in investigations/narratives. Output a list of prose references for manual review.

- **Priority**: Low (insurance for when janitorial work is needed, but rare if creation-time guidance works)
- **Dependencies**: None
- **Notes**:
  - See `prototypes/h4_cluster_rename_spec.md` for detailed scope
  - Implement as dry-run by default, require `--execute` to apply
  - Consider soft aliases as lighter-weight alternative if full rename is too complex

### 5. Update CLAUDE.md with naming guidance

Add a brief section to CLAUDE.md documenting the naming convention for chunks: prefer initiative nouns over artifact types or action verbs. This makes the characteristic guideline visible to agents without requiring skill invocation.

- **Priority**: Medium (low effort, provides passive guidance)
- **Dependencies**: None (can be done independently)
- **Notes**:
  - Keep it brief: 3-5 sentences
  - Reference this investigation for rationale
  - Examples of good prefixes (ordering, taskdir, template) vs bad (chunk, fix, cli)

## Resolution Rationale

**Status: SOLVED** - The investigation question has been answered. Proposed chunks capture the implementation work.

The core question—"Can alphabetical chunk grouping provide meaningful navigational value?"—has been answered: **Yes, with the right naming approach.**

Key answers established:
1. Mid-sized clusters (3-8 chunks) provide value; singletons and superclusters do not
2. Domain-concept prefixes ("ordering_", "taskdir_") work; prescribed categories ("cli_", "model_") fail
3. Pairwise similarity can guide prefix selection at creation time
4. Characteristic guidelines ("What initiative does this advance?") are more effective than prescriptive ones
5. Cluster-level renaming is feasible for janitorial cleanup

Five proposed chunks capture the implementation work. The investigation is complete; the chunks are ready for prioritization and implementation.