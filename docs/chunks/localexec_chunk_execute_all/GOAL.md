---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: ["commands/chunk-execute-all.md", "agents/chunk-executor.md", "docs/trunk/DECISIONS.md", "README.md"]
code_references:
  - ref: commands/chunk-execute-all.md
    implements: "Wave-based session-local execution command: target selection, pre-flight baseline, DAG/waves, worktree-isolated parallel execution, per-wave merge-back, failure handling, finalization"
  - ref: agents/chunk-executor.md
    implements: "Worktree-mode protocol (self-activation, ff to main tip, commit-on-branch, no merging) and extended report contract"

narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["agentskills_migration", "plugin_core_commands", "plugin_init_slimdown", "plugin_legacy_migration", "plugin_orch_commands", "plugin_runtime_context", "plugin_scaffold", "plugin_session_hooks", "plugin_subagents"]
---

# Chunk Goal

## Minor Goal

The plugin exposes `/chunk-execute-all`, which drives a set of chunks — all
FUTURE chunks, one narrative's chunks, or an explicitly named list — through
the full lifecycle inside the operator's interactive session using parallel
sub-agents. Chunks are grouped into topological waves from their `depends_on`
frontmatter; a wave with one chunk runs a chunk-executor agent directly in the
main working tree, while a wave with several runs one chunk-executor agent per
chunk in isolated git worktrees that are merged back, verified, and cleaned up
before the next wave launches. Failures and review escalations block all
transitive dependents. This session-local execution path is the preferred
alternative to `ve orch` background execution (DEC-012): interactive-session
sub-agents bill under the operator's Claude subscription, while the Agent
SDK-based orchestrator bills at standard API token rates.

## Context

- Operator motivation (2026-06-09): Anthropic's billing change requires Agent
  SDK consumers — which includes the ve orchestrator — to pay standard token
  rates, while sub-agents spawned inside an interactive Claude Code session
  are covered by a Max plan. The operator also judged the observed execution
  pattern preferable to the orchestrator's. Orchestrator deprecation is
  contemplated but is NOT this chunk's scope; this chunk only establishes the
  preferred alternative and records the direction (DEC-012).
- The reference implementation of the pattern is the execution of
  docs/narratives/claude_plugin_port (8 chunks, 5 waves, 6 worktree-isolated
  agents, conflict-free merges). The load-bearing mechanics to encode:
  pre-flight baseline capture (pre-existing test-failure set; unrelated
  dirty/untracked paths that agents must never stage), worktree isolation for
  parallel chunks (one IMPLEMENTING chunk per worktree), fast-forwarding each
  worktree branch to the main tip before starting, per-wave merge-back +
  worktree/branch cleanup + focused test verification, and propagation of
  each wave's reported handoffs/warnings into the next wave's agent prompts.
- Composes with existing plugin pieces: `commands/narrative-execute.md` is
  narrative-scoped, launches wave agents in the SAME working tree, and
  predates the worktree pattern — it stays as-is for now;
  `agents/chunk-executor.md` is the single-chunk lifecycle agent and gains a
  worktree mode (self-activation inside the worktree when the chunk is still
  FUTURE, commit on the branch, never merge, report branch + worktree path +
  handoffs).
- Test invariants that govern the new files:
  `tests/test_plugin_commands.py#TestCommandInvariants` is parameterized over
  every commands/*.md (frontmatter name+description, no Jinja2, no
  AUTO-GENERATED header); `tests/test_plugin_agents.py#TestChunkExecutorPromotion`
  requires agents/chunk-executor.md to keep the `/chunk-plan` →
  `/chunk-implement` → `/chunk-review` → `/chunk-complete` lifecycle text, the
  "3 times maximum" retry cap, and the SUCCESS/FAILURE report contract.
- The command follows the canonical preamble from
  docs/chunks/plugin_runtime_context/PORTING_GUIDE.md.

## Success Criteria

- `commands/chunk-execute-all.md` exists with the canonical preamble and
  frontmatter; it covers: target selection (no args → all FUTURE chunks;
  narrative name; explicit chunk list), pre-flight (chunk dirs committed,
  baseline test failures recorded, unrelated dirty paths listed as
  forbidden), wave computation from `depends_on` (null → analyze GOALs and
  serialize conservatively; cycles → stop), operator confirmation of the
  plan, solo-wave execution in the main tree, parallel-wave execution via
  worktree-isolated chunk-executor agents launched in a single message,
  per-wave merge-back/cleanup/verification, handoff propagation, failure
  handling that blocks transitive dependents and consults the operator, and
  finalization (narrative status COMPLETED only when all its chunks are
  ACTIVE; summary report).
- `agents/chunk-executor.md` documents the worktree mode without breaking
  TestChunkExecutorPromotion.
- DEC-012 in docs/trunk/DECISIONS.md records the session-local-execution
  preference, the billing rationale, and orchestrator deprecation as
  contemplated future work.
- README's plugin command table lists `/chunk-execute-all`.
- Plugin test suites pass (TestCommandInvariants picks up the new command
  automatically).

## Rejected Ideas

### Deprecate or remove the orchestrator in this chunk

Rejected because: the orchestrator is a large surface (daemon, scheduler,
merge machinery, conflict oracle, trunk docs) and removal deserves its own
narrative once `/chunk-execute-all` has proven itself on real batches.
DEC-012 records the direction so the intent is not lost.

### Extend narrative-execute instead of adding a new command

Rejected because: the operator wants execution over arbitrary chunk sets
(especially "all FUTURE chunks"), not only narratives, and narrative-execute's
same-tree parallelism is unsafe to extend without the worktree machinery this
command introduces. The two can converge later, with narrative-execute
delegating its wave execution to this command's mechanics.
