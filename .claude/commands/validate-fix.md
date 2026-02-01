---
description: Iteratively fix validation errors until clean
---


<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Overview

This command runs an iterative fix loop that:
1. Runs `ve validate --verbose` to detect errors
2. Classifies each error as auto-fixable or unfixable
3. Applies fixes for auto-fixable issues
4. Repeats until clean or only unfixable issues remain
5. Reports what was fixed and what needs human attention

**Important constraints:**
- Does NOT perform git operations (no auto-commits) per DEC-005
- Max 10 iterations to prevent infinite loops
- Stops if no progress is made (same errors remain unfixed)

## Error Classification

### Auto-Fixable Errors (apply fixes directly)

| Error Type | Link Type | Fix |
|------------|-----------|-----|
| Malformed `chunk_directory` | `narrative→chunk`, `investigation→chunk`, `friction→chunk` | Strip `docs/chunks/` prefix |
| Missing bidirectional link | `chunk↔narrative`, `chunk↔investigation` | Add chunk to parent's `proposed_chunks` |
| Missing code backref in file | `chunk→code` (when chunk has `code_references`) | Add `# Chunk:` comment to file |
| Missing `code_references` entry | `code↔chunk` (code has backref, chunk doesn't list file) | Add entry to chunk's `code_references` |

### Unfixable Errors (report for human review)

| Error Type | Link Type | Reason |
|------------|-----------|--------|
| Reference to non-existent artifact | `chunk→narrative`, `chunk→investigation`, `chunk→subsystem`, `chunk→friction`, `chunk→chunk` | Artifact may be deleted or typo; requires human judgment |
| Code backref to non-existent chunk | `code→chunk` | Chunk may be deleted; requires human to update code |
| Code backref to non-existent subsystem | `code→subsystem` | Subsystem may be deleted; requires human to update code |
| Non-existent chunk in `proposed_chunks` | `narrative→chunk`, `investigation→chunk` | Chunk reference is stale; requires human judgment |

## Instructions


### Initial Run

Run validation to capture current state:

```bash
ve validate --verbose
```

Parse the output to extract:
- **Errors**: Lines containing `ERROR:` - these block success
- **Warnings**: Lines containing `WARNING:` - bidirectional consistency issues

### Iteration Loop

For each iteration (max 10):

1. **Analyze each error** and classify it:

   **Malformed path errors** (auto-fixable):
   - Message: `Malformed chunk_directory '...' - should not include 'docs/chunks/' prefix`
   - Fix: Edit the source file's frontmatter to remove the prefix

   **Missing proposed_chunks entry** (auto-fixable):
   - Source: `docs/chunks/{chunk}/GOAL.md`
   - Message: `Chunk references {narrative/investigation} '...' but {narrative/investigation}'s proposed_chunks does not list this chunk`
   - Link type: `chunk↔narrative` or `chunk↔investigation`
   - Fix: Add an entry to the parent artifact's `proposed_chunks` array

   **Missing code backref in file** (auto-fixable when chunk has code_references):
   - This is detected by reading the chunk's `code_references` and checking if each referenced file contains a `# Chunk:` comment pointing back
   - Fix: Add `# Chunk: docs/chunks/{chunk_name} - {description}` to the file

   **Missing chunk→code reference** (auto-fixable):
   - Source: `{file}:{line}`
   - Message: `Code backreference to chunk '...' but chunk's code_references does not include this file`
   - Link type: `code↔chunk`
   - Fix: Add entry to chunk's `code_references` array

   **Non-existent references** (unfixable):
   - Message: `... does not exist`
   - Track these to report at the end

2. **Apply auto-fixable fixes**:

   **Fix: Malformed path**
   ```yaml
   # Before in OVERVIEW.md frontmatter
   proposed_chunks:
     - prompt: "..."
       chunk_directory: docs/chunks/my_chunk

   # After
   proposed_chunks:
     - prompt: "..."
       chunk_directory: my_chunk
   ```

   **Fix: Missing proposed_chunks entry**
   ```yaml
   # Add to narrative/investigation's OVERVIEW.md proposed_chunks:
   proposed_chunks:
     # ... existing entries ...
     - prompt: "<infer from chunk's Minor Goal>"
       chunk_directory: {chunk_name}
   ```

   **Fix: Missing code backref**
   ```python
   # Add at module level or before the referenced symbol
   # Chunk: docs/chunks/{chunk_name} - {brief description from Minor Goal}
   ```

   **Fix: Missing code_references entry**
   ```yaml
   # Add to chunk's GOAL.md code_references:
   code_references:
     # ... existing entries ...
     - ref: {file_path}#{symbol_if_known}
       implements: "{describe what this code implements}"
   ```

3. **Track progress**:
   - Count fixes applied this iteration
   - If zero fixes applied but errors remain → terminate (unfixable only)

4. **Re-validate**:
   ```bash
   ve validate --verbose
   ```

5. **Loop check**:
   - If no errors → success, exit loop
   - If iteration >= 10 → terminate with remaining errors
   - If fixes were applied → continue to next iteration
   - If no fixes applied → terminate with remaining errors

### Termination

Report results:

```
## Validation Fix Results

### Fixes Applied
- Fixed malformed chunk_directory in docs/narratives/foo/OVERVIEW.md: docs/chunks/bar → bar
- Added chunk integrity_validate_fix_command to docs/investigations/referential_integrity/OVERVIEW.md proposed_chunks
- Added code backref to src/integrity.py for chunk integrity_validate

### Remaining Issues (require human review)
- ERROR: docs/chunks/foo/GOAL.md → docs/narratives/deleted_narrative: Narrative 'deleted_narrative' does not exist
- ERROR: src/old_code.py:42 → docs/chunks/removed_chunk: Chunk 'removed_chunk' does not exist

### Summary
- Iterations: 3
- Fixes applied: 5
- Remaining errors: 2 (require human intervention)
```

### Edge Cases

**Warnings only**: If validation shows only warnings (bidirectional issues) and no errors:
- Warnings are informational about bidirectional consistency
- You may optionally fix warnings using the same pattern (add missing links)
- Success is achieved when there are zero errors, regardless of warnings

**Circular or conflicting fixes**: If the same error reappears after being "fixed":
- Track error signatures across iterations
- If an error persists after attempting a fix, mark it as unfixable
- Report it with context about what was attempted

**Multiple fixes per file**: When applying multiple edits to the same file:
- Read the file once
- Apply all edits
- Write the file once
- This prevents intermediate states from causing parse errors
