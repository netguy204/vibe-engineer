---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- src/entity_merge.py
code_references:
  - ref: src/entity_repo.py#_has_tracked_uncommitted_changes
    implements: "Uncommitted-changes gate that ignores untracked entity artifacts (transcripts, decay logs, snapshot dirs)"
  - ref: src/entity_repo.py#merge_entity
    implements: "Merge with optional SOURCE (falls back to configured origin) and updated uncommitted gate"
  - ref: src/entity_repo.py#pull_entity
    implements: "Pull that auto-merges diverged histories instead of raising MergeNeededError"
  - ref: src/entity_merge.py#_RESOLVER_MODEL
    implements: "Centralized model constant for Anthropic SDK fallback (replaces retired claude-3-5-haiku-latest)"
  - ref: src/entity_merge.py#_build_resolver_prompt
    implements: "Extracted prompt builder shared by agent SDK and Anthropic SDK paths"
  - ref: src/entity_merge.py#_resolve_with_agent_sdk
    implements: "Async helper that runs the conflict resolver via Claude Code agent SDK (no API key required)"
  - ref: src/entity_merge.py#resolve_wiki_conflict
    implements: "Wiki conflict resolver that tries agent SDK first, falls back to Anthropic SDK with clear error"
  - ref: src/cli/entity.py#pull
    implements: "pull CLI command with --yes flag, auto-merge result handling, and conflict resolution flow"
  - ref: src/cli/entity.py#merge
    implements: "merge CLI command with optional SOURCE argument resolving from configured remote"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- chunk_goal_stative_voice
- init_chunks_md_template
---

# Chunk Goal

## Minor Goal

`ve entity pull` performs fetch-and-merge in a single command, mirroring
`git pull` semantics. When local and remote histories diverge, `pull`
runs the same merge that `ve entity merge` performs today instead of
referring the operator to a second command. `ve entity merge` accepts
its `SOURCE` argument as optional and, when omitted, resolves it from the
entity's already-recorded remote — so an operator who just ran `pull`
does not have to re-type the URL when escalating to `merge`.

The "uncommitted changes" gate distinguishes intentionally-untracked
files (session transcripts, decay logs, snapshot directories — files the
entity repo never pushes under any circumstances) from genuine
in-progress edits to tracked files. Intentionally-untracked artifacts
do not block sync; uncommitted edits to tracked files still do, and the
error names what's blocking and how to clear it.

The wiki-conflict resolver in `src/entity_merge.resolve_wiki_conflict`
runs through the Claude Code agent SDK on the operator's Claude Max
subscription, so synchronization works for any operator with a working
`claude` CLI without exporting `ANTHROPIC_API_KEY`. The resolver targets
a current, supported Claude model, with the model identifier centralized
so future migrations touch one constant. If the agent-SDK path is
genuinely unavailable in the operator's environment, the resolver falls
back to the Anthropic SDK and emits an error that names the missing key
— not a 404 from a retired model.

Net architectural state: an operator who has been working on an entity in
parallel with a colleague pulls and ends up merged in one command, with
no transcript shuffling, no environment-variable rituals, and no model
ghosts.

## Success Criteria

- `ve entity pull <name>` performs fetch + merge in one step. Divergent
  histories trigger the merge automatically; no "use ve entity merge to
  resolve" error path exists.
- `ve entity merge <name>` treats SOURCE as optional and falls back to
  the remote already configured for the entity. Explicit SOURCE remains
  supported and overrides the configured remote.
- The "uncommitted changes" gate ignores intentionally-untracked entity
  artifacts (transcripts, decay logs, snapshot directories — anything
  the entity repo's gitignore-equivalent excludes from push). Genuine
  uncommitted edits to tracked files still block, with an actionable
  error message.
- `resolve_wiki_conflict` invokes the Claude Code agent SDK as its
  primary path. A merge succeeds end-to-end on a fresh checkout where
  only the `claude` CLI is authenticated and `ANTHROPIC_API_KEY` is
  unset.
- The retired `claude-3-5-haiku-latest` identifier is absent. A current
  model identifier is defined as a single centralized constant.
- Falling back to the Anthropic SDK (when agent SDK is unavailable)
  produces a clear "set ANTHROPIC_API_KEY" message rather than an HTTP
  404 against a retired model.
- Tests cover: pull-on-diverged auto-merges; merge-without-source falls
  back to configured remote; untracked transcripts do not block;
  resolver path selection (agent SDK vs anthropic SDK).

## Out of Scope

- Re-architecting the entity repo's storage model or remote protocol.
- Adding new entity-sync primitives (push/clone/etc.) beyond the
  pull/merge polish above.
- Changing the wiki-conflict resolution strategy itself (prompt content,
  output schema, how synthesized text is applied). This chunk changes
  only how the resolver is *invoked* and which model it targets.
- Generic Anthropic-SDK-to-agent-SDK migration of any other call site
  in the codebase. The migration covers only the resolver path that
  this friction story exercises.