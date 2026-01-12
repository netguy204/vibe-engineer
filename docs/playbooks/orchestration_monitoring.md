# Orchestration Monitoring Playbook

This playbook describes how to monitor chunks executing in the parallel agent orchestrator and report status back to the operator.

## Quick Reference Commands

```bash
# Check daemon status and work unit counts
uv run ve orch status

# View the ready queue with priorities
uv run ve orch queue

# Check orchestrator configuration
uv run ve orch config

# List worktree directories
ls -la .ve/chunks/

# Check git branches for orchestrator work
git branch -a | grep orch
```

## Monitoring Workflow

### 1. Check Overall Status

```bash
uv run ve orch status
```

This shows:
- Daemon status (Running/Stopped)
- PID and uptime
- Work unit counts by status (READY, RUNNING, DONE, NEEDS_ATTENTION)

Example output:
```
Status: Running
PID: 45881
Uptime: 10m
Work Units:
  DONE: 2
  RUNNING: 1
```

### 2. Examine Worktree Directories

Each running chunk has an isolated worktree at `.ve/chunks/<chunk_name>/`:

```bash
ls -la .ve/chunks/
```

Structure:
```
.ve/chunks/<chunk_name>/
├── log/           # Agent transcripts
│   ├── plan.txt
│   ├── implement.txt
│   └── complete.txt
└── worktree/      # Isolated git worktree
```

### 3. Check Phase Progression

Agents progress through phases: **PLAN → IMPLEMENT → COMPLETE**

Determine current phase by checking which log files exist:

```bash
ls -la .ve/chunks/<chunk_name>/log/
```

| Files Present | Current Phase |
|---------------|---------------|
| `plan.txt` only | PLAN |
| `plan.txt` + `implement.txt` | IMPLEMENT |
| All three files | COMPLETE |

### 4. Monitor Agent Activity

#### Check log file sizes (indicates progress):
```bash
wc -l .ve/chunks/*/log/*.txt
```

#### View recent agent activity:
```bash
tail -30 .ve/chunks/<chunk_name>/log/<phase>.txt
```

#### Watch for specific events:
```bash
# Git operations
grep "git add\|git commit" .ve/chunks/<chunk_name>/log/complete.txt

# Tool calls
grep "ToolUseBlock" .ve/chunks/<chunk_name>/log/implement.txt | tail -10

# Errors
grep -i "error\|failed" .ve/chunks/<chunk_name>/log/*.txt
```

### 5. Verify Worktree Isolation

**Critical check**: Ensure agents work in their worktrees, not the main repo.

#### Check main repo is unchanged:
```bash
git status  # Should be clean on main branch
git branch --show-current  # Should be "main"
```

#### Check worktree has its own branch:
```bash
cd .ve/chunks/<chunk_name>/worktree
git branch --show-current  # Should be "orch/<chunk_name>"
git status --short  # Shows changes in worktree only
cd -
```

#### Compare status between main and worktree:
```bash
# Main repo chunk status (should stay FUTURE until merge)
grep "^status:" docs/chunks/<chunk_name>/GOAL.md

# Worktree chunk status (should be IMPLEMENTING)
grep "^status:" .ve/chunks/<chunk_name>/worktree/docs/chunks/<chunk_name>/GOAL.md
```

### 6. Monitor Completion and Merges

When a chunk completes, the orchestrator:
1. Commits changes in the worktree
2. Merges the branch to main
3. Removes the worktree

#### Check recent merges:
```bash
git log --oneline -10
```

Look for merge commits like: `Merge branch 'orch/<chunk_name>'`

#### Verify merge included all changes:
```bash
git show <commit_hash> --stat
```

**Important**: Verify the commit includes chunk documentation (GOAL.md, PLAN.md), not just code files.

## Common Issues and Diagnostics

### Issue: Agent Using Wrong Paths

**Symptom**: Log shows errors like "File does not exist" for paths with wrong usernames.

**Example**:
```
Read input: {'file_path': '/Users/jsmith/dev/ve/docs/chunks/...'}
ToolResultBlock: '<tool_use_error>File does not exist.</tool_use_error>'
```

**Diagnosis**: Agents sometimes hallucinate absolute paths from training data. They typically recover by using relative paths after receiving errors.

**Action**: Monitor that the agent recovers and starts using correct paths. The worktree CWD is shown in the init message.

### Issue: Documentation Not Committed

**Symptom**: After merge, chunk GOAL.md still shows `status: FUTURE` and PLAN.md is empty template.

**Diagnosis**: Check the commit contents:
```bash
git show <commit_hash> --stat
```

If only code files (not `docs/chunks/`) are listed, the agent excluded documentation.

**Root Cause**: The `chunk-commit.md` skill had ambiguous guidance about "ephemeral files" that agents misinterpreted to exclude chunk documentation.

**Fix**: The skill has been updated to explicitly require chunk documentation in commits.

### Issue: Worktree Not Cleaned Up

**Symptom**: `.ve/chunks/<chunk>/` directory exists but worktree is gone.

**Diagnosis**:
```bash
git worktree list
ls -la .ve/chunks/<chunk>/
```

If only `log/` remains, the worktree was removed but logs preserved for debugging.

**Action**: Logs can be examined for post-mortem analysis. The directory can be manually cleaned if no longer needed.

## Reporting Status to Operator

When reporting orchestrator status, include:

### Summary Table
```
| Chunk | Phase | Status | Notes |
|-------|-------|--------|-------|
| chunk_a | COMPLETE | DONE | Merged to main |
| chunk_b | IMPLEMENT | RUNNING | Writing tests |
| chunk_c | PLAN | READY | Waiting for slot |
```

### Key Metrics
- Total runtime (from `ve orch status` uptime)
- Chunks completed vs remaining
- Any chunks needing attention

### Isolation Verification
- Confirm main repo is clean
- Confirm each worktree has its own branch
- Confirm status changes are worktree-only until merge

### Issues Observed
- Path hallucination (recovered? still failing?)
- Incomplete commits (documentation missing?)
- Phase failures (needs attention queue?)

### Cost Summary (if available from logs)
```bash
grep "total_cost_usd" .ve/chunks/*/log/*.txt
```

## Example Monitoring Session

```bash
# 1. Initial status check
uv run ve orch status

# 2. Watch progress over time
watch -n 30 'uv run ve orch status; echo "---"; ls .ve/chunks/*/log/ 2>/dev/null'

# 3. Check specific chunk progress
tail -f .ve/chunks/my_chunk/log/implement.txt

# 4. After completion, verify merges
git log --oneline -5
for chunk in chunk_a chunk_b; do
  echo "=== $chunk ==="
  grep "^status:" docs/chunks/$chunk/GOAL.md
done

# 5. Report summary
uv run ve orch status
```

## Related Documentation

- `docs/chunks/orch_scheduling/GOAL.md` - Orchestrator scheduling design
- `docs/investigations/parallel_agent_orchestration/` - Original investigation
- `.claude/commands/chunk-commit.md` - Commit skill (updated to require documentation)
