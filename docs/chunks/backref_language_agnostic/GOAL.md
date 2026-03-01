---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/source_files.py
- src/integrity.py
- src/backreferences.py
- tests/test_source_files.py
- tests/test_backreferences.py
code_references:
  - ref: src/source_files.py
    implements: "New module for language-agnostic source file enumeration with SOURCE_EXTENSIONS and FALLBACK_EXCLUDE_DIRS constants"
  - ref: src/source_files.py#enumerate_source_files
    implements: "Main entry point using git or fallback enumeration with extension filtering"
  - ref: src/source_files.py#_is_git_repository
    implements: "Git repository detection for strategy selection"
  - ref: src/source_files.py#_enumerate_git_files
    implements: "Git-based file enumeration using git ls-files --cached --others --exclude-standard"
  - ref: src/source_files.py#_enumerate_fallback_files
    implements: "Non-git fallback using recursive glob with exclusion set"
  - ref: src/source_files.py#_filter_by_extension
    implements: "Extension filtering for source files"
  - ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
    implements: "Replaced hardcoded src/**/*.py with enumerate_source_files() call"
  - ref: src/backreferences.py#count_backreferences
    implements: "Uses enumerate_source_files() and fixed filter bug to include subsystem/narrative-only files"
narrative: arch_review_cleanup
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- dead_code_removal
- narrative_compact_extract
- persist_retry_state
- repo_cache_dry
- reviewer_decisions_dedup
- worktree_merge_extract
- phase_aware_recovery
---

# Chunk Goal

## Minor Goal

Make backreference scanning work for any programming language, not just Python. Currently, both `src/integrity.py` `_validate_code_backreferences` (line 658-663) and `src/backreferences.py` `count_backreferences` (line 58-59) hardcode `src/**/*.py` as the only glob pattern for discovering source files with backreference comments. This means projects using JavaScript, TypeScript, Go, Rust, or any other language get zero backreference validation or counting.

The fix has three parts:

1. **Extract a shared source-file enumeration utility** that both modules call. In git repositories, use `git ls-files --cached --others --exclude-standard` to enumerate user source files, automatically respecting `.gitignore` to exclude dependency directories (node_modules, vendor, dist, .venv, etc.) without maintaining a hardcoded exclusion list. Filter the resulting file list by known source extensions (py, js, ts, jsx, tsx, rb, go, rs, java, kt, swift, c, cpp, h, cs, etc.). For non-git projects, fall back to a recursive glob with a minimal exclusion set (.git, __pycache__).

2. **Replace hardcoded globs** in `_validate_code_backreferences` and `count_backreferences` with calls to the shared utility.

3. **Fix the filter bug** in `src/backreferences.py` line 79: the condition `if chunk_refs:` silently excludes files that contain only `# Subsystem:` or `# Narrative:` backreferences but no `# Chunk:` references. These files should be included in the results since `BackreferenceInfo` tracks all three reference types.

## Success Criteria

- A shared source-file enumeration function exists (e.g., in a common utility module) that both `integrity.py` and `backreferences.py` call. No duplicated file-discovery logic.
- In a git repository, the enumeration uses `git ls-files --cached --others --exclude-standard` and filters by a configurable set of source extensions. Files ignored by `.gitignore` (node_modules, vendor, dist, .venv, etc.) are automatically excluded without any hardcoded directory exclusion list.
- In a non-git project directory, the enumeration falls back to a recursive glob with a minimal exclusion set (at least `.git` and `__pycache__`).
- `_validate_code_backreferences` in `src/integrity.py` no longer hardcodes `src/**/*.py`; it uses the shared utility to scan all language source files in the project.
- `count_backreferences` in `src/backreferences.py` no longer defaults to `["src/**/*.py"]`; it uses the shared utility when no explicit `source_patterns` argument is provided.
- Files containing only `# Subsystem:` or `# Narrative:` backreferences (but no `# Chunk:` refs) are included in `count_backreferences` results, fixing the filter bug at line 79.
- Existing tests continue to pass. New tests cover: (a) git-based enumeration returns files with supported extensions, (b) non-git fallback works, (c) the filter bug fix includes subsystem/narrative-only files in results.
