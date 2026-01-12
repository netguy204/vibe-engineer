---
themes:
  - orchestrator
proposed_chunks: []
---

# Friction Log

<!--
GUIDANCE FOR AGENTS — DO NOT REMOVE THIS COMMENT

This guidance block is permanent project documentation. Agents MUST NOT delete,
modify, or move this comment. It exists to help future agents understand how to
work with the friction log correctly.

THEMES:
- Starts empty; themes are added organically as friction is logged
- Each theme is a short identifier (e.g., "cli", "docs", "testing")
- When logging friction, use an existing theme if it fits, or add a new one

PROPOSED_CHUNKS:
- Starts empty; entries are added when friction patterns emerge
- Format: list of {prompt, chunk_directory, addresses} where:
  - prompt: The proposed chunk prompt text describing work to address the friction
  - chunk_directory: Populated when/if the chunk is created via /chunk-create
  - addresses: List of entry titles this chunk would address
- Add a proposed_chunk when 3+ entries share a theme, or when recurring pain is evident
- The prompt should describe the work, not just "fix friction"

When appending a new friction entry:
1. Read existing themes - cluster the new entry into an existing theme if it fits
2. If no theme fits, add a new theme to frontmatter
3. Use the format: ### YYYY-MM-DD [theme-id] Title

Entry status is DERIVED, not stored:
- OPEN: Entry title not in any proposed_chunks.addresses
- ADDRESSED: Entry title in proposed_chunks.addresses where chunk_directory is set
- RESOLVED: Entry is addressed by a chunk that has reached COMPLETE status
-->

## Entries

<!--
ENTRY FORMAT — DO NOT REMOVE THIS COMMENT

Agents are instructed to preserve this comment. It documents the required format.

Each entry follows this structure:

    ### YYYY-MM-DD [theme-id] Title

    Description of the friction point. Include enough context for future readers
    to understand what happened and why it was painful.

Where:
- YYYY-MM-DD: Date the friction was observed
- [theme-id]: Category from the themes list in frontmatter (e.g., [cli], [docs])
- Title: Brief summary of the friction point (used as the entry identifier)

New entries are appended below this comment.
-->

### 2026-01-12 [orchestrator] Over-eager conflict oracle causes unnecessary blocking

The orchestrator's conflict oracle flags conflicts too aggressively, causing work units
to get stuck in NEEDS_ATTENTION when they could safely proceed. Issues encountered:

1. **Stale blockers persist**: Work units show completed chunks in their `blocked_by`
   list even after those chunks are DONE. Example: `remove_external_ref` showed
   `friction_chunk_linking` as a blocker while RUNNING.

2. **Status doesn't auto-transition**: When a blocker completes, the blocked work unit
   stays in NEEDS_ATTENTION instead of transitioning to READY. Requires manual
   `ve orch work-unit status <chunk> READY` intervention.

3. **Attention reasons go stale**: The `attention_reason` field isn't cleared when
   work units transition to READY or RUNNING, causing confusing `ve orch ps` output.

4. **Code path overlap is too coarse**: Conflict detection based on `code_paths`
   overlap doesn't consider whether chunks actually modify the same lines or functions.
   Two chunks touching the same file aren't necessarily in conflict.

Root cause: State cleanup isn't happening on status transitions. Created future chunk
`orch_unblock_transition` to address the cleanup bugs.
