---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
created_after: ["orch_attention_queue", "orch_conflict_oracle", "orch_agent_skills", "orch_question_forward"]
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
- If this is the final chunk of a narrative, the narrative status should be set to completed
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
- Format: subsystem_id is {NNNN}-{short_name}, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "0001-validation"
      relationship: implements
    - subsystem_id: "0002-frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section.

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/0042-foo/migrate.py)
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
-->

# Chunk Goal

## Minor Goal

Prevent orchestrator agents from escaping their worktree sandbox and modifying
the host repository directly. This addresses a critical bug discovered during
investigation of the `artifact_copy_backref` work unit, where an agent ran
`cd /path/to/host && git commit` and committed unrelated changes directly to
main instead of to the worktree branch. The implementation was lost because
the worktree had no commits to merge.

The fix implements defense-in-depth with three layers:

### 1. Hook-based Command Filtering (Primary Enforcement)

Register a Claude Code hook when launching agents that intercepts Bash tool
calls and blocks commands that would escape the worktree:

- Block commands containing `cd <host_repo_path>` (absolute path to host)
- Block commands containing the host repo path in git operations
- Block any `cd` to an absolute path outside the worktree

**Critical**: Paths must be dynamically derived at runtime:
- `host_repo_path`: The directory where `ve orch start` was launched (available
  from orchestrator state or `os.getcwd()` at startup)
- `worktree_path`: The actual worktree path for the current chunk (e.g.,
  `.ve/chunks/<chunk>/worktree`)

Do NOT hard-code paths like `/Users/btaylor/Projects/vibe-engineer`.

### 2. Git Environment Restriction

When launching agents, set environment variables that restrict git operations
to the worktree only:

```python
env = os.environ.copy()
env["GIT_DIR"] = str(worktree_path / ".git")
env["GIT_WORK_TREE"] = str(worktree_path)
```

This causes git commands to operate on the worktree even if the agent somehow
changes directory to the host repo.

### 3. Prompt Hardening (Guidance Layer)

Add explicit sandbox rules to the CWD reminder already prepended to phase
prompts (in `src/orchestrator/agent.py`):

```markdown
## SANDBOX RULES (CRITICAL)

You are operating in an isolated git worktree. You MUST:
- NEVER use `cd` with absolute paths outside this directory
- NEVER run git commands targeting the host repository
- ALWAYS use relative paths from the current worktree
- ONLY commit to the current branch in this worktree

Violations will be blocked and logged.
```

## Success Criteria

- **Hook registration**: `AgentRunner` registers a sandbox enforcement hook
  when creating `ClaudeAgentOptions` that intercepts Bash commands
- **Dynamic path detection**: Hook uses `self.host_repo_path` (captured at
  orchestrator startup) and `worktree_path` (passed per-agent) - no hard-coded
  paths in the codebase
- **Blocking behavior**: Hook returns `SyncHookJSONOutput(decision="block", ...)`
  for commands matching:
  - `cd {host_repo_path}` or `cd '{host_repo_path}'` or `cd "{host_repo_path}"`
  - Any git command containing `{host_repo_path}`
  - `cd /absolute/path` where path is outside `{worktree_path}`
- **Git environment**: Agent subprocess environment includes `GIT_DIR` and
  `GIT_WORK_TREE` pointing to the worktree
- **Prompt hardening**: Phase prompts include sandbox rules warning agents
  about isolation requirements
- **Test coverage**:
  - Unit test verifying hook blocks `cd /host/repo/path`
  - Unit test verifying hook blocks `git -C /host/repo/path commit`
  - Unit test verifying hook allows normal commands within worktree
  - Unit test verifying `GIT_DIR` environment is set correctly
- **No regressions**: All existing orchestrator tests pass

