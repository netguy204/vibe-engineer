# Plan

## Context

The `progressive_disclosure_refactor` chunk (from the `claudemd_progressive_disclosure` investigation) successfully reduced CLAUDE.md token usage by 77% by:
1. Extracting detailed artifact documentation to `docs/trunk/ARTIFACTS.md`
2. Extracting orchestrator documentation to `docs/trunk/ORCHESTRATOR.md`
3. Adding signpost sections to CLAUDE.md.jinja2 that point to these files

Additionally, the `progressive_disclosure_external` chunk added `docs/trunk/EXTERNAL.md` for multi-repo workflows.

**The problem**: These documents were created directly in vibe-engineer's `docs/trunk/` directory but corresponding templates were never added to `src/templates/trunk/`. When agents run `ve init` in user projects, these three files are not created, leaving broken signposts in CLAUDE.md.

The existing template system in `src/templates/trunk/` includes:
- `GOAL.md.jinja2`
- `SPEC.md.jinja2`
- `DECISIONS.md.jinja2`
- `FRICTION.md.jinja2`
- `TESTING_PHILOSOPHY.md.jinja2`

The `Project._init_trunk()` method in `src/project.py` uses `render_to_directory("trunk", ...)` which automatically renders all `.jinja2` files in the trunk template directory.

## Approach

Create three new Jinja2 templates by converting the existing `docs/trunk/` files to templates. Since these documents are reference documentation without dynamic content, the templates will be simple static markdown wrapped in the Jinja2 template structure.

## Steps

### Step 1: Create ORCHESTRATOR.md.jinja2

Create `src/templates/trunk/ORCHESTRATOR.md.jinja2` with the content from `docs/trunk/ORCHESTRATOR.md`.

**Implementation**:
- Copy the content from `docs/trunk/ORCHESTRATOR.md`
- The file is already static markdown with no user-specific variables
- No Jinja2 templating needed beyond the file structure

### Step 2: Create ARTIFACTS.md.jinja2

Create `src/templates/trunk/ARTIFACTS.md.jinja2` with the content from `docs/trunk/ARTIFACTS.md`.

**Implementation**:
- Copy the content from `docs/trunk/ARTIFACTS.md`
- The file references artifact types and their usage patterns
- No dynamic content needed

### Step 3: Create EXTERNAL.md.jinja2

Create `src/templates/trunk/EXTERNAL.md.jinja2` with the content from `docs/trunk/EXTERNAL.md`.

**Implementation**:
- Copy the content from `docs/trunk/EXTERNAL.md`
- Documents external artifact workflows
- No dynamic content needed

### Step 4: Verify Template Rendering

Run `uv run ve init` in a test project to verify:
1. All three files are created in `docs/trunk/`
2. Content matches expectations
3. No rendering errors occur

**Verification command**:
```bash
# Create a temp directory and test init
cd $(mktemp -d)
uv run ve init
ls -la docs/trunk/
```

### Step 5: Run Existing Tests

Ensure existing tests pass:
```bash
uv run pytest tests/
```

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Templates have Jinja2 syntax that needs escaping | Low | Low | Review content for `{{`, `}}`, `{%`, `%}` characters |
| Existing projects get duplicate content on re-init | Low | Low | `render_to_directory` with `overwrite=False` skips existing files |

## Success Metrics

- [x] `src/templates/trunk/ORCHESTRATOR.md.jinja2` exists
- [ ] `src/templates/trunk/ARTIFACTS.md.jinja2` exists
- [ ] `src/templates/trunk/EXTERNAL.md.jinja2` exists
- [ ] `uv run ve init` creates all three files in a fresh project
- [ ] Rendered content matches source documents
- [ ] All existing tests pass
