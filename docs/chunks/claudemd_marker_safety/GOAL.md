---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/templates/claude/AGENTS.md.jinja2
- tests/test_project.py
- tests/test_template_system.py
- tests/fixtures/agents_md_single_tree.md
code_references:
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: 'Self-documenting VE:MANAGED markers (annotated START/END lines) and
    seeded safe regions outside them: a ''this region is yours'' comment above START
    and a ''project-specific content goes here'' line below END'
- ref: src/project.py#parse_markers
  implements: Recognition of both the bare and the annotated marker forms, so every
    existing AGENTS.md keeps parsing
- ref: src/project.py#_managed_block_lines
  implements: Comparable line inventory of a managed block (non-blank, non-marker
    lines) used for discard detection
- ref: src/project.py#Project::_init_agents_md
  implements: The discard warning through InitResult.warnings when regeneration drops
    in-block lines the incoming render does not carry
- ref: tests/test_project.py#TestAnnotatedMarkerParsing
  implements: Bare/annotated/mixed marker parsing, prose-mention exclusion, and malformed-marker
    cases
- ref: tests/test_project.py#TestManagedBlockSafety
  implements: Seeded safe regions on fresh write, self-documenting marker lines, discard
    warning, marker-upgrade and no-op silence, unchanged outside-marker preservation
- ref: tests/test_template_system.py#TestVeConfigInTemplates::test_agents_md_template_has_managed_markers
  implements: Marker presence assertions match the annotated prefix rather than the
    bare form
narrative: init_trust
investigation: null
subsystems: []
friction_entries: []
depends_on:
- template_workspace_awareness
- claudemd_symlink_notice
created_after:
- crossref_absence_evidence
- crossref_artifact_id_cap
- crossref_defect_line_anchor
- crossref_generator_verify
- crossref_glob_refs
- crossref_pointer_guard
- crossref_reexport_absence
- crossref_refactor_move
- crossref_unchecked_anchors
- crossref_workspace_parity
- federation_member_refs
---
# Chunk Goal

## Minor Goal

The VE:MANAGED block is safe to live next to. The AGENTS.md/CLAUDE.md
templates render self-documenting markers: the START and END lines state on
themselves that everything between them is regenerated and destroyed by
`ve init` and that project content belongs above START or below END —
wording adapted from a field-tested warning written after a production
incident in which operator security directives authored inside the block
were silently erased by regeneration while user-authored *files* got
"Preserved ..." notices (that asymmetry was the bug). A fresh render seeds a
safe region outside the markers — a "this region is yours" comment above
START and a "project-specific content goes here" line below END — so a new
AGENTS.md never begins at START and ends at END with nowhere correct to
write. `parse_markers` in src/project.py recognizes both the bare and the
annotated marker forms, so every existing AGENTS.md keeps parsing and
upgrades to the annotated markers on its next regeneration. When
regeneration replaces a managed block containing non-blank, non-marker
lines the incoming render does not carry, `ve init` reports the discard
through `InitResult.warnings`, naming AGENTS.md and pointing at the
preserved regions for recovery — dropping in-block content is never silent.
Above-START/below-END preservation in `Project._init_agents_md` is designed
behavior, unchanged, and is stated on the markers themselves and in the
discard warning.

## Success Criteria

- The rendered VE:MANAGED:START/END lines are annotated in place: each
  marker states that content between the markers is regenerated and
  destroyed by `ve init` and that project content belongs above START or
  below END (wording adapted from the archived field-tested warning).
- A fresh `ve init` write of AGENTS.md seeds a safe region outside the
  markers: a comment block above START and a short "project-specific
  content goes here" line below END, so a new file never begins at START
  and ends at END.
- `parse_markers` in src/project.py recognizes both the bare form
  (`<!-- VE:MANAGED:START -->`) and the annotated form; every existing
  AGENTS.md keeps parsing, and prose that merely mentions the marker tokens
  is never counted as a marker.
- Regenerating a managed block that contains non-blank, non-marker lines
  absent from the incoming render appends a warning to `InitResult.warnings`
  naming AGENTS.md; a no-op regeneration and a bare-to-annotated marker
  upgrade emit no warning.
- Above-START/below-END preservation in `Project._init_agents_md` is
  unchanged, and is now stated on the markers themselves and in the
  discard warning.
- The single-tree golden fixtures are deliberately regenerated and the
  renders stay pinned byte-for-byte; `uv run pytest tests/` and
  `uv run ve validate` pass clean.