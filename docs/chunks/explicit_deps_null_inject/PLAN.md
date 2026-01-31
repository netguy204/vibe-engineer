# Implementation Plan

## Approach

The core insight is that YAML distinguishes between `null`, omitted fields, and empty lists, but Pydantic's default behavior collapses them. We need to:

1. **Preserve the null vs empty distinction in the model layer**: Change `ChunkFrontmatter.depends_on` from `list[str] = []` to `list[str] | None = None`. This lets us distinguish between:
   - `depends_on: null` or omitted → `None` (unknown deps)
   - `depends_on: []` → empty list `[]` (explicitly no deps)
   - `depends_on: ["chunk_a"]` → populated list (explicit deps)

2. **Update the injection logic**: Modify `read_chunk_dependencies` and the injection path to check whether `depends_on` is `None` vs an empty list. Set `explicit_deps=True` when `depends_on` is a list (even if empty).

3. **Write tests first**: Following TDD per docs/trunk/TESTING_PHILOSOPHY.md, write failing tests that verify the null vs empty distinction before implementing the fix.

This approach minimizes code changes—the semantic distinction already exists in YAML; we just need to stop collapsing it.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (status: DOCUMENTED): This chunk IMPLEMENTS part of the orchestrator's dependency management logic. We're modifying how `explicit_deps` is determined at injection time.

## Sequence

### Step 1: Write failing tests for null vs empty distinction

Create tests that verify the semantic distinction between `depends_on: null`/omitted and `depends_on: []`. Following TDD, these tests will fail initially.

**Tests to add** (in `tests/test_orchestrator_cli.py`):

1. `test_inject_empty_depends_on_sets_explicit_deps_true` - A chunk with `depends_on: []` should have `explicit_deps=True` when injected
2. `test_inject_null_depends_on_sets_explicit_deps_false` - A chunk with `depends_on: null` should have `explicit_deps=False`
3. `test_inject_omitted_depends_on_sets_explicit_deps_false` - A chunk with no `depends_on` field should have `explicit_deps=False`

Location: `tests/test_orchestrator_cli.py`

### Step 2: Update ChunkFrontmatter model

Change the `depends_on` field from `list[str] = []` to `list[str] | None = None`.

This preserves the null vs empty distinction from YAML parsing:
- `depends_on: null` → `None`
- `depends_on:` (empty) → `None`
- `depends_on: []` → `[]`
- `depends_on: ["x"]` → `["x"]`

Location: `src/models.py#ChunkFrontmatter`

### Step 3: Update read_chunk_dependencies function

Modify `read_chunk_dependencies` in `src/ve.py` to return `None` values when `depends_on` is `None` in the frontmatter (rather than converting to `[]`).

The function signature changes to:
```python
def read_chunk_dependencies(project_dir, chunk_names) -> dict[str, list[str] | None]:
```

This lets callers distinguish unknown deps (`None`) from explicit no-deps (`[]`).

Location: `src/ve.py#read_chunk_dependencies`

### Step 4: Update orch_inject command logic

Modify the injection loop in `orch_inject` to set `explicit_deps=True` when:
- `depends_on` is an empty list `[]` (explicit no deps), OR
- `depends_on` is a non-empty list (explicit deps)

And set `explicit_deps=False` when:
- `depends_on` is `None` (unknown deps, consult oracle)

The key change is from:
```python
if chunk_deps:
    body["blocked_by"] = chunk_deps
    body["explicit_deps"] = True
```

To:
```python
deps = dependencies.get(chunk)
if deps is not None:
    # deps is a list (empty or non-empty) - explicit declaration
    body["explicit_deps"] = True
    if deps:
        body["blocked_by"] = deps
# else: deps is None - unknown, oracle will be consulted
```

Location: `src/ve.py#orch_inject`

### Step 5: Verify tests pass

Run the tests from Step 1 to verify they now pass with the implementation changes.

```bash
uv run pytest tests/test_orchestrator_cli.py -k "depends_on" -v
```

### Step 6: Update existing test expectations

Review existing tests that create chunks with `depends_on: []` and ensure they expect `explicit_deps=True`. The test `test_inject_explicit_deps_flag_set` currently expects `explicit_deps=False` for chunks with `depends_on: []`—this needs updating.

Location: `tests/test_orchestrator_cli.py#TestOrchInjectBatch`


## Risks and Open Questions

1. **Backward compatibility**: Existing chunks with `depends_on: []` currently get `explicit_deps=False`. After this change, they'll get `explicit_deps=True`. This is the intended behavior change, but existing tests may need updating.

2. **Template default**: The chunk GOAL.md template currently has `depends_on: []`. Should this stay as-is (meaning new chunks explicitly declare no deps by default) or change to omitted/null (meaning new chunks are unknown)? The template currently matches the desired "explicit no deps" semantic, so no change needed.

3. **Pydantic default handling**: Verify that Pydantic's YAML parsing actually distinguishes `null` from `[]`. The `yaml.safe_load` call should handle this correctly, but needs verification in tests.

## Deviations

<!-- Populate during implementation -->