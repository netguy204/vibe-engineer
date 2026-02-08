# Implementation Plan

## Approach

Split the four oversized orchestrator test files along functional boundaries, following the pattern already established by `test_orchestrator_review_routing.py` and `test_orchestrator_review_parsing.py` which were extracted as part of `scheduler_decompose_methods`.

**Strategy:**
1. Analyze each file's class structure to identify coherent functional groupings
2. Extract shared fixtures to `tests/conftest.py` (per TESTING_PHILOSOPHY.md)
3. Create new focused test files named to reflect functionality
4. Move test classes to their appropriate new files
5. Verify all tests pass after each file split

**File Naming Convention:**
- Use `test_orchestrator_{component}_{area}.py` for splits from the main orchestrator tests
- Keep names descriptive of the functional area being tested

**Target File Sizes:**
- Each new file should be under ~1000 lines
- Prefer more files over fewer to maintain clear functional boundaries

## Sequence

### Step 1: Extract shared orchestrator test fixtures to conftest.py

Move fixtures from `test_orchestrator_scheduler.py` that are used across scheduler tests to `tests/conftest.py`:
- `state_store` fixture (creates StateStore for testing)
- `mock_worktree_manager` fixture (creates mock WorktreeManager)
- `mock_agent_runner` fixture (creates mock AgentRunner)
- `config` fixture (creates OrchestratorConfig)
- `scheduler` fixture (creates Scheduler instance)

Location: `tests/conftest.py`

### Step 2: Split test_orchestrator_scheduler.py (5046 lines → 5-6 files)

**Current structure analysis:**
- Lines 90-312: TestSchedulerProperties, TestSchedulerDispatch, TestPhaseAdvancement (~220 lines) - Core dispatch mechanics
- Lines 314-648: TestMechanicalCommit, TestAgentResultHandling, TestVerboseSuccessNotMisinterpreted (~330 lines) - Agent result handling
- Lines 649-885: TestCrashRecovery, TestRetainWorktree, TestCreateScheduler, TestSchedulerLifecycle (~240 lines) - Lifecycle/recovery
- Lines 886-1189: TestActiveStatusVerification, TestAttentionReason (~300 lines) - Status verification
- Lines 1191-1609: TestActivateChunkInWorktree, TestRestoreDisplacedChunk, TestChunkActivationInWorkUnit (~420 lines) - Chunk activation
- Lines 1610-2009: TestDeferredWorktreeCreation, TestBlockedWorkDeferredWorktree, TestDeferredWorktreeCreationIntegration (~400 lines) - Deferred worktree
- Lines 2011-2693: TestPendingAnswerInjection, TestConflictChecking, TestExplicitDepsOracleBypass (~680 lines) - Injection and conflicts
- Lines 2695-3404: TestQuestionForwardingFlow, TestAutomaticUnblock, TestNeedsAttentionUnblock, TestAttentionReasonCleanup (~710 lines) - Unblock flows
- Lines 3406-3554: TestWebSocketBroadcasts (~150 lines) - Already has test_orchestrator_websocket potential
- Lines 3555-3982: TestReviewPhase, TestReviewDecisionParsing, TestReviewFeedbackFile (~430 lines) - Review phase (partially covered by test_orchestrator_review_routing.py)
- Lines 3983-4531: TestReviewDecisionTool, TestManualDoneUnblock (~550 lines) - Review tools and manual unblock
- Lines 4533-4845: TestIsRetryableApiError, TestApiRetryScheduling (~310 lines) - Retry logic
- Lines 4846-5046: TestRebasePhase (~200 lines) - Rebase phase

**Split plan:**

| New File | Classes | ~Lines |
|----------|---------|--------|
| `test_orchestrator_scheduler_dispatch.py` | TestSchedulerProperties, TestSchedulerDispatch, TestPhaseAdvancement, TestCreateScheduler, TestSchedulerLifecycle | ~350 |
| `test_orchestrator_scheduler_results.py` | TestMechanicalCommit, TestAgentResultHandling, TestVerboseSuccessNotMisinterpreted, TestCrashRecovery, TestRetainWorktree | ~400 |
| `test_orchestrator_scheduler_activation.py` | TestActiveStatusVerification, TestVerifyChunkActiveStatus, TestActivateChunkInWorktree, TestRestoreDisplacedChunk, TestChunkActivationInWorkUnit | ~700 |
| `test_orchestrator_scheduler_worktree.py` | TestDeferredWorktreeCreation, TestBlockedWorkDeferredWorktree, TestDeferredWorktreeCreationIntegration | ~400 |
| `test_orchestrator_scheduler_injection.py` | TestPendingAnswerInjection, TestConflictChecking, TestExplicitDepsOracleBypass | ~680 |
| `test_orchestrator_scheduler_unblock.py` | TestQuestionForwardingFlow, TestAutomaticUnblock, TestNeedsAttentionUnblock, TestAttentionReasonCleanup, TestAttentionReason | ~800 |
| `test_orchestrator_scheduler_review.py` | TestReviewPhase, TestReviewDecisionParsing, TestReviewFeedbackFile, TestReviewDecisionTool, TestManualDoneUnblock | ~980 |
| `test_orchestrator_scheduler.py` (keep) | TestWebSocketBroadcasts, TestIsRetryableApiError, TestApiRetryScheduling, TestRebasePhase | ~660 |

Location: `tests/`

### Step 3: Split test_orchestrator_cli.py (1930 lines → 3 files)

**Current structure analysis:**
- Lines 26-145: TestOrchClientContextManager, TestOrchStart, TestOrchStop, TestOrchStatus (~120 lines) - Daemon lifecycle
- Lines 147-355: TestOrchPs, TestWorkUnitCreate, TestWorkUnitStatus, TestWorkUnitDelete (~210 lines) - Work unit management
- Lines 355-534: TestOrchInject, TestOrchQueue, TestOrchPrioritize (~180 lines) - Queue operations
- Lines 535-868: TestOrchConfig, TestWorkUnitShow, TestOrchUrl, TestOrchPsAttentionReason (~330 lines) - Config and status display
- Lines 869-1757: TestOrchInjectBatch (~890 lines) - Batch injection (large class)
- Lines 1758-1930: TestOrchTail (~170 lines) - Log tailing

**Split plan:**

| New File | Classes | ~Lines |
|----------|---------|--------|
| `test_orchestrator_cli_lifecycle.py` | TestOrchClientContextManager, TestOrchStart, TestOrchStop, TestOrchStatus, TestOrchUrl | ~200 |
| `test_orchestrator_cli_workunit.py` | TestOrchPs, TestWorkUnitCreate, TestWorkUnitStatus, TestWorkUnitDelete, TestWorkUnitShow, TestOrchPsAttentionReason | ~540 |
| `test_orchestrator_cli_queue.py` | TestOrchInject, TestOrchQueue, TestOrchPrioritize, TestOrchConfig | ~330 |
| `test_orchestrator_cli_inject_batch.py` | TestOrchInjectBatch | ~890 |
| `test_orchestrator_cli.py` (keep) | TestOrchTail | ~170 |

Location: `tests/`

### Step 4: Split test_orchestrator_agent.py (1899 lines → 3 files)

**Current structure analysis:**
- Lines 27-127: MockClaudeSDKClient helper class (~100 lines) - Test infrastructure
- Lines 128-309: TestPhaseSkillFiles, TestLoadSkillContent, TestErrorDetectionRemoval (~180 lines) - Skill loading
- Lines 310-493: TestAgentRunner, TestAgentRunnerPhaseExecution, TestSettingSourcesConfiguration (~180 lines) - Agent runner
- Lines 494-658: TestLogCallback, TestQuestionInterceptHook (~160 lines) - Callbacks and hooks
- Lines 660-805: TestRunPhaseWithQuestionCallback (~145 lines) - Question flow
- Lines 806-1048: TestSandboxViolationDetection, TestMergeHooks, TestSandboxEnforcementHook, TestAgentRunnerSandboxIntegration (~240 lines) - Sandbox
- Lines 1049-1210: (continues sandbox integration) (~160 lines)
- Lines 1211-1565: TestReviewDecisionHook, TestRunPhaseWithReviewDecisionCallback (~350 lines) - Review decision hooks
- Lines 1566-1899: TestMCPServerConfiguration, TestAskUserQuestionMessageStreamCapture (~330 lines) - MCP and message capture

**Split plan:**

| New File | Classes | ~Lines |
|----------|---------|--------|
| `test_orchestrator_agent_skills.py` | MockClaudeSDKClient (helper), TestPhaseSkillFiles, TestLoadSkillContent, TestErrorDetectionRemoval | ~280 |
| `test_orchestrator_agent_runner.py` | TestAgentRunner, TestAgentRunnerPhaseExecution, TestSettingSourcesConfiguration | ~180 |
| `test_orchestrator_agent_hooks.py` | TestLogCallback, TestQuestionInterceptHook, TestRunPhaseWithQuestionCallback, TestMergeHooks | ~305 |
| `test_orchestrator_agent_sandbox.py` | TestSandboxViolationDetection, TestSandboxEnforcementHook, TestAgentRunnerSandboxIntegration | ~400 |
| `test_orchestrator_agent.py` (keep) | TestReviewDecisionHook, TestRunPhaseWithReviewDecisionCallback, TestMCPServerConfiguration, TestAskUserQuestionMessageStreamCapture | ~680 |

Location: `tests/`

### Step 5: Split test_orchestrator_worktree.py (1685 lines → 3 files)

**Current structure analysis:**
- Lines 43-200: TestWorktreeManager (~160 lines) - Basic worktree operations
- Lines 202-265: TestWorktreeCleanup, TestBaseBranch (~60 lines) - Cleanup and branching
- Lines 267-461: TestMergeToBase, TestCommitChanges (~200 lines) - Merge and commit
- Lines 464-559: TestMultiRepoWorktreeCreation (~95 lines) - Multi-repo creation
- Lines 561-720: TestMultiRepoWorktreeRemoval, TestMultiRepoMerge (~160 lines) - Multi-repo operations
- Lines 720-955: TestTaskContextSymlinks, TestBaseBranchPersistence (~235 lines) - Task context
- Lines 956-1162: TestCheckoutFreeMerge (~206 lines) - Checkout-free merge
- Lines 1163-1300: TestWorktreeLocking, TestTaskContextDetection (~140 lines) - Locking and detection
- Lines 1301-1556: TestMultiRepoBaseBranchPersistence, TestMultiRepoCheckoutFreeMerge, TestMultiRepoWorktreeLocking (~260 lines) - Multi-repo advanced
- Lines 1557-1685: TestFinalizeWorkUnit (~130 lines) - Finalization

**Split plan:**

| New File | Classes | ~Lines |
|----------|---------|--------|
| `test_orchestrator_worktree_basic.py` | TestWorktreeManager, TestWorktreeCleanup, TestBaseBranch, TestMergeToBase, TestCommitChanges | ~420 |
| `test_orchestrator_worktree_multirepo.py` | TestMultiRepoWorktreeCreation, TestMultiRepoWorktreeRemoval, TestMultiRepoMerge, TestMultiRepoBaseBranchPersistence, TestMultiRepoCheckoutFreeMerge, TestMultiRepoWorktreeLocking | ~515 |
| `test_orchestrator_worktree.py` (keep) | TestTaskContextSymlinks, TestBaseBranchPersistence, TestCheckoutFreeMerge, TestWorktreeLocking, TestTaskContextDetection, TestFinalizeWorkUnit | ~750 |

Location: `tests/`

### Step 6: Verify all tests pass

Run the full test suite to confirm:
1. All tests are discoverable by pytest
2. No test duplication (each test exists in exactly one file)
3. All tests pass with the same results as before the split
4. No import errors or missing fixtures

Command: `uv run pytest tests/test_orchestrator_*.py -v`

### Step 7: Update code_paths in GOAL.md

Add all new test files to the chunk's `code_paths` frontmatter for traceability.

## Dependencies

- **scheduler_decompose_methods** (ACTIVE): Tests should be split against the new code structure where `_handle_review_result` is in `review_routing.py` and there's already a `test_orchestrator_review_routing.py`
- **artifact_pattern_consolidation** (ACTIVE): No direct test file impact, but ensures artifact-related tests are against consolidated patterns

Both chunks are ACTIVE, meaning the code changes are complete and tests can be split against the current structure.

## Risks and Open Questions

- **Fixture dependencies**: Some test classes may depend on fixtures defined inline above them. Need to trace fixture usage carefully when extracting to conftest.py.
- **Import ordering**: Moving test classes between files may surface hidden import order dependencies. Monitor for import errors.
- **Test isolation**: Some tests may have implicit dependencies on test execution order. Splitting files will change execution order - need to ensure all tests are properly isolated.
- **Line count estimates**: The split boundaries are estimated from grep output. Actual line counts may vary once helper functions and imports are accounted for.
