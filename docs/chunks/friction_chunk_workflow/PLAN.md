# Plan: Integrate Friction Tracking into Chunk Lifecycle

## Overview

This chunk integrates friction entry tracking into the `/chunk-create` and `/chunk-complete` skill templates, completing the bidirectional friction-to-resolution lifecycle:

```
Experience friction → /friction-log → Pattern accumulation → /chunk-create (with friction) → /chunk-complete → Friction resolved
```

The foundation is already in place:
- `friction_template_and_cli` implemented `FRICTION.md`, entry parsing, and CLI commands
- `friction_chunk_linking` added `friction_entries` to chunk GOAL.md frontmatter and validation

This chunk connects those pieces through the skill workflows.

## Dependencies

- **friction_template_and_cli** (ACTIVE): Provides `Friction` class and entry management
- **friction_chunk_linking** (ACTIVE): Provides `friction_entries` frontmatter schema and validation

## Implementation Steps

### Step 1: Enhance `/chunk-create` Template

**File:** `src/templates/commands/chunk-create.md.jinja2`

Add a new step between step 5 (refine GOAL.md) and step 6 (check for investigation origin) that:

1. Prompts the operator: "Does this chunk address any friction entries from `docs/trunk/FRICTION.md`?"
2. If yes, read `docs/trunk/FRICTION.md` and show OPEN entries
3. Let operator select which entries this chunk addresses (with scope: full/partial)
4. Add selected entries to the chunk's `friction_entries` frontmatter

**Template changes:**
- Add new step 6 for friction entry selection
- Renumber subsequent steps (current step 6 becomes step 7)
- Include guidance on reading FRICTION.md and presenting options

### Step 2: Implement `/chunk-create` Friction Update Logic

**File:** `src/templates/commands/chunk-create.md.jinja2`

When friction entries are specified in step 6:

1. Add `friction_entries` to the chunk's GOAL.md frontmatter
2. Update FRICTION.md frontmatter to mark entries as ADDRESSED:
   - Add or update a `proposed_chunks` entry linking the friction entry IDs to this chunk
   - The `addresses` field contains the entry IDs
   - The `chunk_directory` is set to the chunk being created

**Note:** The status derivation logic already exists in `Friction.get_entry_status()`:
- OPEN → ADDRESSED when entry ID is in `proposed_chunks.addresses` with `chunk_directory` set

### Step 3: Add Helper CLI Command for Listing OPEN Friction

**File:** `src/ve.py`

Add a new CLI command `ve friction list-open` (or enhance existing `ve friction list --open`) that:
- Returns machine-parseable output of OPEN friction entries
- Format: `F001 [theme-id] Title` per line
- This helps agents quickly query which entries are available to address

**Assessment:** The existing `ve friction list --open` already provides this. No new command needed, but verify output format is agent-friendly.

### Step 4: Enhance `/chunk-complete` Template

**File:** `src/templates/commands/chunk-complete.md.jinja2`

Add a new step (after current step 11, before optional task context steps) that:

1. Check if the chunk being completed has `friction_entries` in its frontmatter
2. If yes, for each friction entry referenced:
   a. Display the entry ID and title
   b. Prompt: "Mark friction entry {ID} as RESOLVED?"
3. For entries confirmed as resolved, verify the chunk has reached ACTIVE status
4. Report friction resolution status to operator

**Note on "RESOLVED" status:** The status is derived, not stored. An entry is RESOLVED when:
- It's in `proposed_chunks.addresses`
- The linked chunk has reached ACTIVE status

Since `/chunk-complete` transitions the chunk to ACTIVE (step 11), the friction entries will automatically be computed as RESOLVED by the existing derivation logic. The prompt in this step is informational/confirmatory rather than requiring file updates.

### Step 5: Handle Partial vs Full Scope

Both templates need to handle the `scope` field:

**In `/chunk-create`:**
- When adding friction entries, prompt for scope: "Does this chunk fully or partially address this entry?"
- Store as `{entry_id: "F001", scope: "full"}` or `{entry_id: "F001", scope: "partial"}`

**In `/chunk-complete`:**
- For `scope: full` entries: These are fully resolved when chunk is ACTIVE
- For `scope: partial` entries: Inform operator that this entry may need additional chunks to fully resolve

### Step 6: Update FRICTION.md proposed_chunks on Chunk Create

**File:** `src/templates/commands/chunk-create.md.jinja2`

When friction entries are being addressed, the template should instruct the agent to:

1. Read current FRICTION.md frontmatter
2. Check if a `proposed_chunks` entry already exists for these friction entries
3. If not, add a new `proposed_chunks` entry:
   ```yaml
   proposed_chunks:
     - prompt: "<derived from chunk goal>"
       chunk_directory: "<chunk being created>"
       addresses: ["F001", "F003"]
   ```
4. If an existing entry covers some of these IDs, update it with the chunk_directory

**Implementation approach:** The agent will edit FRICTION.md directly (no CLI command needed for this low-frequency operation).

### Step 7: Add Integration Tests

**File:** `tests/test_friction_workflow.py` (new file)

Test scenarios:

1. **chunk-create with friction entries**: Verify that:
   - Chunk frontmatter contains `friction_entries`
   - FRICTION.md `proposed_chunks` is updated correctly
   - Entry status transitions from OPEN to ADDRESSED

2. **chunk-complete with friction entries**: Verify that:
   - Entries referenced in completed chunk compute as RESOLVED
   - Partial scope entries are handled correctly

3. **Edge cases**:
   - Chunk addresses entries from multiple themes
   - Chunk partially addresses some entries, fully addresses others
   - Multiple chunks address the same entry (partial scope)

## Code Paths

- `src/templates/commands/chunk-create.md.jinja2` - Add friction entry selection step
- `src/templates/commands/chunk-complete.md.jinja2` - Add friction resolution verification step
- `tests/test_friction_workflow.py` - Integration tests for friction workflow

## Risks and Mitigations

1. **Risk:** Agent may incorrectly identify friction entries
   - **Mitigation:** Template explicitly shows OPEN entries with IDs and titles for operator confirmation

2. **Risk:** FRICTION.md edits may corrupt frontmatter
   - **Mitigation:** Template provides clear YAML format example; validation exists in `ve chunk validate`

3. **Risk:** Partial scope complexity confuses operators
   - **Mitigation:** Clear explanation in prompts; most entries will use `full` scope

## Success Verification

After implementation:

1. Create a test friction entry with `/friction-log`
2. Create a chunk with `/chunk-create` that addresses the entry
3. Verify chunk has `friction_entries` in frontmatter
4. Verify FRICTION.md has updated `proposed_chunks`
5. Run `ve friction list --open` and verify entry shows as ADDRESSED
6. Complete the chunk with `/chunk-complete`
7. Verify entry status is RESOLVED
