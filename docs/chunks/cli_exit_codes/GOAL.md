---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/cli/chunk.py
  - src/cli/investigation.py
  - src/cli/narrative.py
  - src/cli/subsystem.py
  - src/cli/migration.py
  - docs/trunk/SPEC.md
  - tests/test_chunk_list.py
  - tests/test_investigation_list.py
  - tests/test_narrative_list.py
  - tests/test_subsystem_list.py
code_references:
  - ref: src/cli/chunk.py#list_chunks
    implements: "Exit code 0 for empty chunk list results"
  - ref: src/cli/investigation.py#list_investigations
    implements: "Exit code 0 for empty investigation list results"
  - ref: src/cli/narrative.py#list_narratives
    implements: "Exit code 0 for empty narrative list results"
  - ref: src/cli/subsystem.py#list_subsystems
    implements: "Exit code 0 for empty subsystem list results"
  - ref: src/cli/migration.py#list_migrations
    implements: "Explicit exit code 0 for empty migration list results"
  - ref: docs/trunk/SPEC.md
    implements: "Exit code convention documentation"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Standardize exit codes across all CLI commands to follow a consistent convention: exit code 0 for success (including "no results found"), exit code 1 for actual errors. Currently, CLI commands inconsistently treat "no results found" scenarios: some exit with 0 (treating it as success), others exit with 1 (treating it as an error), and some don't use SystemExit at all.

This inconsistency breaks scripting and automation use cases where users need to distinguish between "the command succeeded but found nothing" (exit 0) and "the command failed due to an error" (exit 1).

**Current inconsistencies identified:**

Exit 1 for "no results found" (incorrect - should be 0):
- `ve chunk list` with no chunks (src/cli/chunk.py:445)
- `ve investigation list` with no investigations (src/cli/investigation.py:143)
- `ve narrative list` with no narratives (src/cli/narrative.py:130)
- `ve subsystem list` with no subsystems (src/cli/subsystem.py:58)

Exit 0 for "no results found" (correct):
- `ve chunk list-proposed` with no proposed chunks (src/cli/chunk.py:759)
- `ve friction list` with no entries (src/cli/friction.py:307)

No SystemExit at all (ambiguous):
- `ve migration list` with no migrations (src/cli/migration.py:102) - just returns, implicitly 0

## Success Criteria

1. **All CLI list commands exit with code 0 when no results are found:**
   - `ve chunk list` exits 0 (currently exits 1)
   - `ve investigation list` exits 0 (currently exits 1)
   - `ve narrative list` exits 0 (currently exits 1)
   - `ve subsystem list` exits 0 (currently exits 1)
   - `ve friction list` exits 0 (already correct)
   - `ve chunk list-proposed` exits 0 (already correct)
   - `ve migration list` exits 0 (currently implicit, make explicit)

2. **All CLI commands exit with code 1 for actual errors:**
   - Validation errors (invalid arguments, missing required inputs)
   - File system errors (missing files, permission denied)
   - API errors (daemon not running, network failures)
   - Data errors (malformed frontmatter, invalid references)

3. **Exit code convention is documented:**
   - Add a section to docs/trunk/SPEC.md or appropriate location documenting the exit code convention
   - Document that exit 0 means "command succeeded" (including "succeeded but found nothing")
   - Document that exit 1 means "command failed due to an error"

4. **Tests verify the exit code behavior:**
   - Existing CLI tests are updated to assert correct exit codes
   - Tests cover both "no results found" (exit 0) and "actual error" (exit 1) cases


