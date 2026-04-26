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

CLI commands follow a single exit-code convention: exit 0 means the command succeeded (including the "succeeded but found nothing" case), and exit 1 means the command failed. Every list command — `ve chunk list`, `ve investigation list`, `ve narrative list`, `ve subsystem list`, `ve friction list`, `ve chunk list-proposed`, and `ve migration list` — exits 0 when its result set is empty, so scripts and automation can distinguish "no results" from "error" by exit code alone.

Validation failures, missing files, daemon-down conditions, and malformed-frontmatter errors all exit 1. The convention is documented in `docs/trunk/SPEC.md` so the contract is reviewable rather than implicit in each command's source.

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


