

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is surgical: add one new Jinja2 template file and one new test.

`_init_trunk` in `src/project.py` already calls `render_to_directory("trunk", ...)`,
which renders every `.jinja2` file found in `src/templates/trunk/`. Adding
`src/templates/trunk/CHUNKS.md.jinja2` is therefore sufficient to make `ve init`
produce `docs/trunk/CHUNKS.md` on every fresh project — no changes to `project.py`
are needed.

The template content is the static prose from `docs/trunk/CHUNKS.md` (the four
chunk principles). CHUNKS.md contains no Jinja2 delimiters (`{{ }}` or `{% %}`),
so no `{% raw %}...{% endraw %}` wrapper is required.

The existing `overwrite=False` semantics of `render_to_directory` mean re-running
`ve init` on a project that already has `docs/trunk/CHUNKS.md` skips the file —
preserving any user edits. This behaviour is already tested for other trunk docs and
does not need a new test.

## Sequence

### Step 1: Write the failing test

Add a test to `tests/test_init.py` that:
- Invokes `ve init` in a fresh temp directory.
- Asserts that `docs/trunk/CHUNKS.md` exists.
- Asserts that the file contains the four principles by checking for a key phrase
  from each (e.g., `"Code owns implementation"`, `"Chunks exist only for
  intent-bearing work"`, `"present tense"`, `"Status answers a single question"`).

Run the test suite to confirm the new test fails (red phase).

```
uv run pytest tests/test_init.py -k chunks -v
```

### Step 2: Create `src/templates/trunk/CHUNKS.md.jinja2`

Copy the content of `docs/trunk/CHUNKS.md` verbatim into the new template file.
No Jinja2 variable substitutions are needed — the four principles are static prose.
Add a backreference comment at the top (inside an HTML comment so it does not appear
in rendered output):

```
# Chunk: docs/chunks/init_chunks_md_template - Adds CHUNKS.md to ve init trunk set
```

Location: `src/templates/trunk/CHUNKS.md.jinja2`

### Step 3: Verify the test passes

Run the full test suite:

```
uv run pytest tests/
```

The new test should now be green. All previously passing tests must still pass —
in particular `test_init_skips_existing_files` (or equivalent) should continue to
demonstrate that `overwrite=False` is preserved.

### Step 4: Smoke-test `ve init` in a temp directory

```bash
tmp=$(mktemp -d)
uv run ve init --project-dir "$tmp"
cat "$tmp/docs/trunk/CHUNKS.md"
rm -rf "$tmp"
```

Confirm the file renders with the four principles intact.

### Step 5: Update `code_paths` in GOAL.md

Update the `code_paths` field in `docs/chunks/init_chunks_md_template/GOAL.md` to
list both files touched by this chunk:

```yaml
code_paths:
- src/templates/trunk/CHUNKS.md.jinja2
- tests/test_init.py
```

## Risks and Open Questions

- **Jinja2 delimiter collision**: If a future edit to `docs/trunk/CHUNKS.md` adds
  text that looks like a Jinja2 expression, the template will break at render time.
  The current content has no such text; if it ever does, wrap the affected section in
  `{% raw %}...{% endraw %}`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->