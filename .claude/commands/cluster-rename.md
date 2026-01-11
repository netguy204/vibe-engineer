---
description: Rename all chunks matching a prefix to use a new prefix.
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/cluster-rename.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


## Tips

- The ve command is an installed CLI tool, not a file in the repository. Do not
search for it - run it directly via Bash.

## Instructions

The operator has requested a cluster rename operation:

$ARGUMENTS

Parse the arguments to extract `<old_prefix>` and `<new_prefix>`. The format should be:
`/cluster-rename <old_prefix> <new_prefix>`

---

### Phase 1: Dry-Run Preview

1. Run the cluster rename command in dry-run mode (default):
   ```
   ve chunk cluster-rename <old_prefix> <new_prefix>
   ```

2. Review the output, which shows:
   - **Directories to be renamed**: Chunk directories that will be renamed
   - **Frontmatter references to update**: `created_after`, subsystem `chunks`, narrative/investigation `proposed_chunks`
   - **Code backreferences to update**: `# Chunk: docs/chunks/...` comments in source files
   - **Prose references for manual review**: Potential mentions in documentation that may need updating

3. If no chunks match the prefix or there are validation errors (collisions, dirty working tree), the command will fail with an error message. Address any issues before proceeding.

4. **Note the prose references** shown in the output—you will address these AFTER the automated rename completes.

---

### Phase 2: Execute the Rename

Execute the rename to apply all automatable changes:

1. Run with `--execute` flag:
   ```
   ve chunk cluster-rename <old_prefix> <new_prefix> --execute
   ```

2. The command will automatically:
   - Rename chunk directories
   - Update all frontmatter references (`created_after`, subsystem `chunks`, narrative/investigation `proposed_chunks`)
   - Update code backreferences (`# Chunk: docs/chunks/...` comments) in source files

3. Verify the automated changes:
   - Run `ve chunk list` to see the renamed chunks
   - Spot-check a few updated frontmatter references

---

### Phase 3: Fix Prose References

Now that the automated rename is complete, manually review and fix the prose references that were identified in Phase 1.

**Why this order matters**: The CLI handles structured references (frontmatter fields, code backreferences) automatically. Prose references require semantic judgment that only you can provide. By executing first, you avoid accidentally duplicating work the CLI would have done.

Prose references are mentions of chunk names in documentation that cannot be safely auto-updated because they may be:
- Part of explanatory text
- In code examples
- Historical references that should not change
- False positives (similar text that isn't actually a reference)

For each prose reference from the dry-run output:

1. **Read the context** around the reference to understand its purpose
2. **Decide if it should be updated**:
   - If it's a live reference to the chunk being renamed → update it
   - If it's a historical reference or example that should preserve the old name → leave it
   - If it's a false positive → ignore it
3. **Apply the fix** using targeted edits

Common patterns to update:
- `docs/chunks/<old_name>` → `docs/chunks/<new_name>` in prose text
- References in OVERVIEW.md files linking to chunks
- References in other chunk GOAL.md/PLAN.md prose sections

---

## Error Recovery

If something goes wrong during execution:

1. **Missed references**: Run `grep -r "<old_prefix>_" docs/ src/` to find any remaining references that weren't updated

2. **Build/test failures**: The rename should be purely cosmetic. If tests fail after rename, check for hardcoded chunk names in test fixtures