---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/config.py
- src/cli/__init__.py
- tests/test_config.py
code_references:
- ref: src/cli/config.py#VeConfig
  implements: "Typed dataclass holding the fully-resolved operator config (absolute entities_dir + normalized git_base)"
- ref: src/cli/config.py#ConfigError
  implements: "Exception type for missing-file, malformed-file, and field-validation failures with messages that name the offending field and the config file path"
- ref: src/cli/config.py#load_config
  implements: "Canonical loader: parses ~/.ve-config.toml, applies tilde expansion, strips trailing slash from git_base, validates required-field/wrong-type cases, and raises ConfigError with actionable messages"
- ref: src/cli/config.py#get_entities_dir
  implements: "Convenience accessor returning the resolved absolute entities_dir Path (consumed by canonical-clone helper and worktree attach in downstream chunks)"
- ref: src/cli/config.py#get_git_base
  implements: "Convenience accessor returning the normalized git_base URL string (consumed by canonical-clone helper in the next chunk)"
- ref: src/cli/config.py#config
  implements: "Top-level `ve config` Click command group registered with the main CLI"
- ref: src/cli/config.py#show
  implements: "`ve config show` subcommand that prints the resolved config in a stable key=value format with the source file path as a header"
- ref: src/cli/__init__.py
  implements: "Registers the `ve config` command group with the main CLI assembly"
- ref: tests/test_config.py
  implements: "Coverage for valid load, default entities_dir, missing file, malformed TOML, missing field, wrong field type, trailing-slash normalization, tilde expansion, accessor helpers, and `ve config show` success + missing-file paths"
narrative: entity_worktrees
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- plugin_hook_cli_bootstrap
---

# Chunk Goal

## Minor Goal

`~/.ve-config.toml` is the operator-level configuration file the `ve` CLI
reads to discover where entity clones live and where to fetch them from.
The file holds exactly two fields for now:

- `entities_dir` — filesystem path (default `~/Entities`, tilde-expanded
  at load time).
- `git_base` — URL prefix, no trailing slash. Combined with an entity
  name N, the clone URL becomes `{git_base}/{N}.git`.

A configuration module loads and validates the file, returns a typed,
fully-resolved config object, and is the single source of truth every
other entity-related command consults. Missing-file and malformed-file
cases surface clear, actionable errors that tell the user exactly which
field is wrong and where the file is read from. A `ve config show`
subcommand prints the resolved config so users can debug their setup and
so the 1.0 demo path has something concrete to display.

This chunk lays the foundation that the canonical-clone helper, the
worktree-based `attach`/`detach`, and `ve entity claude` auto-attach all
build on. Keeping it minimal is deliberate — `entities_dir` and `git_base`
are the only fields with an immediate consumer in this narrative; future
config additions can land as their own chunks when they have concrete
callers.

## Success Criteria

- `~/.ve-config.toml` with valid `entities_dir` and `git_base` fields
  loads into a typed config object via the new config module.
- `entities_dir` paths beginning with `~` are expanded at load time;
  downstream consumers receive an absolute path.
- `git_base` is normalized at load time (trailing slash stripped if
  present, so consumers can always concatenate `/<name>.git` safely).
- A missing `~/.ve-config.toml` produces a clear error pointing at the
  expected path and naming the missing file — not a stack trace.
- Malformed TOML, missing required fields, or wrong field types produce
  errors that name the offending field and the file path.
- `ve config show` prints the resolved config (with `~` already expanded
  in `entities_dir`) in a stable, human-readable format. The same command
  works as a demo aid and a debugging tool.
- Tests cover: valid load, default `entities_dir`, missing file, malformed
  TOML, missing field, wrong field type, trailing-slash normalization,
  tilde expansion.

## Notes for Planning

- This is `proposed_chunks[0]` of the `entity_worktrees` narrative —
  read `docs/narratives/entity_worktrees/OVERVIEW.md` for the full 1.0
  decomposition and the org-distribution story this enables.
- Resist adding config fields here without a concrete consumer in the
  narrative; future chunks can extend the schema as they need it.