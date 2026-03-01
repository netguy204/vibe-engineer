<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation extracts source file enumeration into a shared utility module (`src/source_files.py`) that both `integrity.py` and `backreferences.py` use. The utility leverages git when available to automatically respect `.gitignore`, eliminating the need to maintain a hardcoded exclusion list for dependency directories.

Key design decisions:
- Use `git ls-files --cached --others --exclude-standard` in git repositories to enumerate files while respecting `.gitignore`
- Filter files by a configurable set of source extensions (py, js, ts, go, rs, etc.)
- Fall back to recursive glob with a minimal exclusion set for non-git projects (per DEC-002: git not assumed)
- Fix the filter bug in `count_backreferences` that silently excluded files with only subsystem or narrative backreferences

Per TESTING_PHILOSOPHY.md, tests are written for the semantic behaviors:
- Git-based enumeration respects `.gitignore`
- Non-git fallback excludes common dependency directories
- Multiple programming languages are supported
- The filter bug fix includes subsystem/narrative-only files

## Sequence

### Step 1: Create the source_files.py utility module

Create a new module `src/source_files.py` with:
- `SOURCE_EXTENSIONS` constant: Set of known source file extensions (py, js, ts, jsx, tsx, rb, go, rs, java, kt, swift, c, cpp, h, cs, etc.)
- `FALLBACK_EXCLUDE_DIRS` constant: Minimal set of directories to exclude in non-git mode (.git, __pycache__, node_modules, .venv, venv, vendor, dist, build, .tox, .pytest_cache)
- `_is_git_repository()`: Check if directory is inside a git repo
- `_enumerate_git_files()`: Use `git ls-files --cached --others --exclude-standard`
- `_enumerate_fallback_files()`: Recursive glob with exclusion set
- `_filter_by_extension()`: Filter paths by extension set
- `enumerate_source_files()`: Main entry point that selects strategy and filters

Location: src/source_files.py

### Step 2: Update integrity.py to use the shared utility

Replace the hardcoded `src/**/*.py` glob in `_validate_code_backreferences` with a call to `enumerate_source_files()`. Remove any hardcoded directory exclusions - let git handle that via `.gitignore`.

Location: src/integrity.py

### Step 3: Update backreferences.py to use the shared utility

Update `count_backreferences` to use `enumerate_source_files()` when no explicit `source_patterns` argument is provided. The explicit patterns argument is retained for backward compatibility.

Location: src/backreferences.py

### Step 4: Fix the filter bug in count_backreferences

Change the filter condition from `if chunk_refs:` to `if chunk_refs or narrative_refs or subsystem_refs:` so that files containing only `# Subsystem:` or `# Narrative:` backreferences are included in results.

Location: src/backreferences.py

### Step 5: Add tests for source_files.py

Create `tests/test_source_files.py` with tests covering:
- Git-based enumeration returns files with supported extensions
- Respects `.gitignore` (node_modules, etc. excluded)
- Returns files from multiple programming languages
- Excludes non-source files (.txt, .md, .json)
- Includes untracked but not-ignored files
- Custom extensions parameter works
- Non-git fallback discovers source files
- Non-git fallback excludes __pycache__, node_modules, .venv
- Empty directory returns empty list
- Nested directories are traversed
- Returns absolute paths

Location: tests/test_source_files.py

### Step 6: Add tests for the filter bug fix

Create tests in `tests/test_backreferences.py` covering:
- Files with only `# Subsystem:` refs are included
- Files with only `# Narrative:` refs are included
- Files with subsystem + narrative (but no chunk) refs are included
- Files with only chunk refs still work (regression test)
- Files with no refs are excluded

Location: tests/test_backreferences.py

### Step 7: Add tests for language-agnostic scanning in backreferences

Add tests verifying that `count_backreferences` finds refs in:
- JavaScript files (.js)
- TypeScript files (.ts)
- Go files (.go)
- And that explicit `source_patterns` argument still works for backward compatibility

Location: tests/test_backreferences.py

## Dependencies

None. This chunk modifies existing modules and adds a new utility module.

## Risks and Open Questions

- **Symlink resolution**: Need to ensure paths are resolved consistently when comparing file paths (e.g., /var vs /private/var on macOS). Addressed by calling `.resolve()` on the project directory.
- **Git not installed**: The `_is_git_repository()` function handles the `FileNotFoundError` case when git is not installed, falling back to non-git enumeration.
- **Large repositories**: For very large repos, `git ls-files` output could be substantial. This is acceptable since git handles this efficiently and the alternative (recursive glob) would be worse.

## Deviations

None - implementation followed the plan as designed.
