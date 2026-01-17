# Phase 6: Infrastructure Annotation

## Infrastructure Patterns

### CLI Framework (Click)
- **Used by subsystems**: All (workflow_artifacts, template_system, orchestrator, cross_repo_operations, cluster_analysis, friction_log)
- **Documented in chunks**: None specifically (every feature adds commands)
- **Consistency**: CONSISTENT - All commands use Click decorators, follow `ve {type} {action}` pattern
- **Complexity**: LOW
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: Standard Click usage, no domain-specific complexity, consistent patterns

### Git Operations
- **Used by subsystems**: cross_repo_operations, orchestrator (indirectly)
- **Documented in chunks**: git_local_utilities, ve_sync_command (partial)
- **Consistency**: CONSISTENT
- **Complexity**: MEDIUM
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: Standard git operations (SHA resolution, remote fetching), no domain-specific invariants that need tracking. repo_cache.py is utility code.

### Validation Utilities
- **Used by subsystems**: workflow_artifacts, cross_repo_operations
- **Documented in chunks**: implement_chunk_start (created validation.py)
- **Consistency**: CONSISTENT
- **Complexity**: LOW
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: Simple identifier validation, shared utility. No complex business rules, just format checking.

### Error Handling
- **Used by subsystems**: All
- **Documented in chunks**: None specifically
- **Consistency**: CONSISTENT - Click exceptions for CLI errors, custom exceptions per module
- **Complexity**: LOW
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: Standard Python exception patterns, no centralized error type system

### YAML/Markdown Parsing
- **Used by subsystems**: workflow_artifacts, friction_log
- **Documented in chunks**: Various (frontmatter parsing in each artifact type)
- **Consistency**: CONSISTENT - PyYAML + frontmatter extraction pattern
- **Complexity**: LOW
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: Standard parsing with Pydantic validation, no complex parsing rules

### Pydantic Model Validation
- **Used by subsystems**: workflow_artifacts, cross_repo_operations, friction_log
- **Documented in chunks**: chunk_frontmatter_model, subsystem_schemas_and_model, etc.
- **Consistency**: CONSISTENT - All models in src/models.py
- **Complexity**: MEDIUM
- **Recommendation**: SUPPORTING_PATTERN (absorbed into domain subsystems)
- **Rationale**: Pydantic is the validation framework, but the models themselves are domain-specific and belong in their subsystems

### Project Initialization
- **Used by subsystems**: template_system (uses), workflow_artifacts (creates dirs)
- **Documented in chunks**: project_init_command, init_creates_chunks_dir
- **Consistency**: CONSISTENT
- **Complexity**: LOW
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: One-time setup, uses template_system for rendering. No ongoing invariants.

### Symbol Parsing
- **Used by subsystems**: workflow_artifacts (for validation)
- **Documented in chunks**: symbolic_code_refs, task_qualified_refs
- **Consistency**: CONSISTENT - All in src/symbols.py
- **Complexity**: MEDIUM
- **Recommendation**: SUPPORTING_PATTERN
- **Rationale**: AST-based symbol extraction is technical infrastructure. The *format* of references is a domain concern (workflow_artifacts), but the *parsing* is infrastructure.

---

## Infrastructure Chunk Disposition

| Chunk | Pattern | Recommendation | Rationale |
|-------|---------|----------------|-----------|
| git_local_utilities | Git Operations | SUPPORTING_PATTERN | Generic git utilities |
| implement_chunk_start (validation parts) | Validation | SUPPORTING_PATTERN | Created validation.py |
| spec_docs_update | Documentation | SUPPORTING_PATTERN | No code, just docs |
| remove_trivial_tests | Testing | SUPPORTING_PATTERN | Test cleanup, not domain |
| agent_discovery_command | CLI | SUPPORTING_PATTERN | Documentation only |

---

## Supporting Patterns Summary
(For inclusion in repo documentation)

| Pattern | Purpose | Status | Location |
|---------|---------|--------|----------|
| CLI Framework | Click-based command dispatching | Consistent | src/ve.py |
| Git Operations | SHA resolution, remote ops, repo cache | Consistent | src/git_utils.py, src/repo_cache.py |
| Validation Utilities | Identifier format validation | Consistent | src/validation.py |
| Symbol Parsing | AST-based code symbol extraction | Consistent | src/symbols.py |
| YAML/Frontmatter Parsing | PyYAML + Pydantic validation | Consistent | Various (models.py for schemas) |
| Error Handling | Click exceptions + custom per module | Consistent | Per-module |
| Project Initialization | Template-based setup | Consistent | src/project.py |

---

## Subsystem vs Supporting Pattern Decision Summary

| Pattern | Promoted to Subsystem? | Rationale |
|---------|------------------------|-----------|
| template_system | YES (existing) | Complex business rules, has deviations to track, affects multiple consumers |
| Git Operations | NO | Simple utility, no domain invariants |
| CLI Framework | NO | Standard Click usage, no invariants |
| Validation | NO | Simple format checking |
| Symbol Parsing | NO | Technical utility for validation |
| Project Init | NO | One-time setup, uses template_system |
| Error Handling | NO | Standard Python patterns |

---

## Files Without Subsystem Assignment

These files are pure infrastructure and do not belong to any domain subsystem:

| File | Purpose | Pattern |
|------|---------|---------|
| src/validation.py | Identifier validation | Validation Utilities |
| src/git_utils.py | Git SHA and remote operations | Git Operations |
| src/repo_cache.py | Repository caching for external resolve | Git Operations |
| src/symbols.py | AST symbol extraction | Symbol Parsing |
| src/constants.py | Template directory path constant | Template System (infrastructure) |

These files will have backreferences removed (infrastructure has no backref) or kept minimal.
