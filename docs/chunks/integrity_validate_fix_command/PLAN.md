<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a `/validate-fix` slash command that provides an iterative fix loop for referential integrity issues. The command will:

1. Run `ve validate` to detect errors
2. Analyze each error to determine if it's auto-fixable
3. Apply fixes for auto-fixable issues
4. Repeat until clean or only unfixable issues remain
5. Report results to the operator

**Auto-fixable error types:**
- **Malformed paths**: Normalize `docs/chunks/foo` → `foo`, `docs/investigations/bar` → `bar`, etc.
- **Missing code backreferences**: Add `# Chunk:` or `# Subsystem:` comments to referenced files when chunk's code_references lists a file but the file lacks the backref
- **Missing proposed_chunks entries**: Add chunk to parent artifact's proposed_chunks when chunk references a narrative/investigation but parent doesn't list the chunk

**Unfixable issues (require human review):**
- Deleted artifacts (chunk, narrative, investigation, subsystem, friction entry doesn't exist)
- Ambiguous references where the fix direction is unclear
- Code references to files that don't exist

**Key design decisions:**
- Per DEC-005, the command will not perform git operations (no auto-commits)
- Max iteration limit (default: 10) to prevent infinite loops
- Clear separation between errors (must be fixed) and warnings (bidirectional consistency)
- This is a slash command template (Jinja2), not a CLI command—the agent executes the fix logic

## Subsystem Considerations

No existing subsystems are directly relevant to this work. This chunk implements a slash command template following the established command pattern in `src/templates/commands/`.

## Sequence

### Step 1: Create the slash command template

Create `src/templates/commands/validate-fix.md.jinja2` following the established pattern:
- YAML frontmatter with `description: "Iteratively fix validation errors until clean"`
- Include the auto-generated header partial
- Include common-tips partial

Location: `src/templates/commands/validate-fix.md.jinja2`

### Step 2: Define error classification in the template

Document which errors are auto-fixable vs unfixable in the command instructions:

**Auto-fixable (agent can fix directly):**
1. Malformed paths in proposed_chunks (e.g., `docs/chunks/foo` → `foo`)
2. Missing bidirectional links:
   - Chunk→narrative exists but narrative→chunk missing: Add to narrative's proposed_chunks
   - Chunk→investigation exists but investigation→chunk missing: Add to investigation's proposed_chunks
   - Code→chunk backref exists but chunk→code missing: Add code_reference to chunk's GOAL.md
3. Missing code backreferences:
   - Chunk→code reference exists but code file lacks `# Chunk:` comment: Add the backref comment

**Unfixable (report for human review):**
1. References to non-existent artifacts (deleted chunks, narratives, investigations, subsystems, friction entries)
2. Code backreferences to files that don't exist
3. Ambiguous cases where multiple fixes are possible

Location: `src/templates/commands/validate-fix.md.jinja2`

### Step 3: Write the iterative fix loop instructions

The command instructs the agent to:

1. **Initial run**: Execute `ve validate --verbose` and capture output
2. **Analyze errors**: For each error, classify as auto-fixable or unfixable
3. **Apply fixes**: For auto-fixable errors, apply the appropriate fix:
   - Malformed paths: Edit the frontmatter field to remove prefix
   - Missing proposed_chunks entry: Edit parent artifact's OVERVIEW.md to add entry
   - Missing code backref: Add `# Chunk: docs/chunks/<name> - <description>` comment
   - Missing chunk→code reference: Add entry to chunk's code_references
4. **Track fixes**: Record what was fixed
5. **Re-validate**: Run `ve validate` again
6. **Loop check**: If errors remain and iteration < max (10), go to step 2
7. **Report**: Summarize fixes applied and any remaining unfixable issues

Location: `src/templates/commands/validate-fix.md.jinja2`

### Step 4: Add detailed fix instructions for each error type

Provide specific edit instructions for each auto-fixable error type:

**Malformed path fix:**
```yaml
# Before
chunk_directory: docs/chunks/my_chunk
# After
chunk_directory: my_chunk
```

**Missing proposed_chunks entry fix (narrative):**
```yaml
# Add to proposed_chunks array in narrative's OVERVIEW.md
- prompt: "<infer from chunk's Minor Goal>"
  chunk_directory: <chunk_name>
```

**Missing code backref fix:**
```python
# Add at module level or before relevant class/function
# Chunk: docs/chunks/<chunk_name> - <brief description>
```

**Missing chunk→code reference fix:**
```yaml
# Add to code_references array in chunk's GOAL.md
- ref: <file_path>#<symbol>
  implements: "<what the code implements>"
```

Location: `src/templates/commands/validate-fix.md.jinja2`

### Step 5: Add max iteration and termination logic

Include safeguards:
- Max iteration count (default 10)
- If no fixes were applied in an iteration but errors remain → report and stop
- If only warnings remain (bidirectional issues in non-strict mode) → success

Location: `src/templates/commands/validate-fix.md.jinja2`

### Step 6: Update CLAUDE.md template to document the new command

Add `/validate-fix` to the Available Commands section in the CLAUDE.md template.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 7: Write tests for the command template rendering

Add tests to verify the command template renders correctly and the fix loop
logic is accurately described.

Test cases:
- Template renders without Jinja2 errors
- Command appears in available commands after `ve init`
- Instructions include all auto-fixable error types
- Max iteration limit is documented

Location: `tests/test_templates.py` or new `tests/test_validate_fix.py`

### Step 8: Verify command registration

Run `ve init` and verify the command appears in `.claude/commands/validate-fix.md`.
Test that the rendered command can be read and parsed correctly.

## Dependencies

This chunk depends on the following completed chunks (all now ACTIVE):
- `integrity_validate` - Provides the `ve validate` CLI command
- `integrity_code_backrefs` - Validates code backreferences with line numbers
- `integrity_proposed_chunks` - Validates proposed_chunks references
- `integrity_bidirectional` - Provides bidirectional consistency warnings

All dependencies are met—these chunks are ACTIVE and their implementations are available in `src/integrity.py` and `src/ve.py`.

## Risks and Open Questions

1. **Code backref placement**: When adding a `# Chunk:` backref to a file, where exactly should it go?
   - Decision: Add at module level (near top of file, after docstring if present) unless the chunk's code_reference specifies a particular symbol, in which case add before that symbol.

2. **Infinite loop with unfixable errors**: If the same unfixable error appears repeatedly, the loop should not continue forever.
   - Mitigation: Track which errors were seen in previous iterations; if no progress (no new fixes applied), terminate even if errors remain.

3. **Concurrent edits**: If the agent applies multiple fixes to the same file, later parses may fail.
   - Mitigation: Apply all fixes to a file before moving to the next file; re-read after writing.

4. **Testing slash commands**: Slash commands are instructions for agents, not executable code.
   - Approach: Test template rendering, not execution. The command's correctness is verified by manually running it or through integration tests in a test project.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->