---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/plugin/skills/workspace-validate-fix.md.jinja2
- skills/workspace-validate-fix/SKILL.md
- tests/test_workspace_validate_fix_skill.py
code_references:
- ref: src/templates/plugin/skills/workspace-validate-fix.md.jinja2
  implements: 'The pointer-coverage deletion guard, at both points where the rationalization
    arises: the "Never delete a reference" invariant forecloses peer-pointer coverage
    as deletion grounds, and the misrouted-bare callout "Does the pointer make the
    references redundant?" answers no and says what to do instead (leave resolving
    references alone, work broken ones through their fix class, escalate deletion).'
- ref: skills/workspace-validate-fix/SKILL.md
  implements: The committed render that reaches operators through the plugin; generated
    output via `ve plugin render`, not the edit surface
- ref: tests/test_workspace_validate_fix_skill.py#test_document_forecloses_pointer_coverage_as_deletion_grounds
  implements: Document-contract assertion that the skill keeps stating the pointer-coverage
    guard and the redundancy callout
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---

# Chunk Goal

## Minor Goal

The workspace-validate-fix skill (source of truth:
src/templates/plugin/skills/workspace-validate-fix.md.jinja2) forecloses the
peer-pointer deletion trap: pointer coverage is never grounds for reference
deletion. A cross-tree external.yaml pointer typically covers a chunk's public
surface, so treating "this ref is covered by the pointer" as license to delete
a reference silently drops intent for private helpers — the per-symbol
backreference is often the only record anywhere tying that code to its
governing intent (4 field rows in the Cloud Capital archaeology lost exactly
this way). The skill states the guard at both points where the rationalization
arises: the "Never delete a reference" invariant names peer-pointer coverage
as a non-license, and the `misrouted-bare` section — where a peer pointer is
created and references are left bare — answers "does the pointer make the
references redundant?" with no, and says what to do instead: leave resolving
references alone, work broken references through their fix class, and escalate
when deletion looks like the only remaining move. A document-contract test
(tests/test_workspace_validate_fix_skill.py) keeps the guard from being
silently dropped by future template edits.

## Success Criteria

- The workspace-validate-fix skill template's "Never delete a reference"
  invariant explicitly states that peer-pointer coverage of an artifact is
  never grounds for removing a reference, naming the private-helper intent
  loss that deletion causes.
- The skill's `misrouted-bare` guidance (where a peer pointer is created and
  references are left bare) carries a callout answering "does the pointer
  make the references redundant?" with: no — the pointer is the resolution
  mechanism for bare references, not a replacement for them.
- The guidance says what to do instead of deleting: leave resolving
  references alone, work broken references through their fix class, and
  escalate when deletion seems like the only remaining move.
- The committed render `skills/workspace-validate-fix/SKILL.md` matches a
  fresh render of the template (the drift test in
  tests/test_plugin_render.py passes).
- The full test suite and `ve validate` remain clean.