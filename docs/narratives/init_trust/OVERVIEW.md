---
status: ACTIVE
advances_trunk_goal: 'Required Properties: ''Following the workflow must maintain
  the health of documents over time and should not grow more difficult over time''
  — and the multi-tree corollary from ''Maintaining the referential integrity of documents
  is an agent problem'': the instructions ve init regenerates must teach the working
  arrangement of the repository they land in, and regeneration must never silently
  destroy operator-authored content.'
proposed_chunks:
- prompt: 'Make the managed AGENTS.md/CLAUDE.md template workspace-aware. When .ve-workspace.yaml
    is present (see src/project.py workspace detection and src/workspace.py), the
    rendered managed block must: (a) show the member-qualified backreference form
    (member::docs/...) that the Nearest Enclosing Tree section alludes to but never
    demonstrates; (b) document peer pointers — ve external point, tree: (intra-workspace)
    vs repo: (cross-repository) — and the field-proven rule ''1 reader in a tree qualifies
    in place; 2+ readers get one pointer and stay bare'' (preserve that rule in spirit
    verbatim; it came out of the workspace-validate-fix skill and stopped a 28-tree
    deployment from oscillating between qualify-everything and point-at-everything);
    (c) fix ACTIVELY WRONG advice: the File Moves and Renames mandate says ''uvx --from
    vibe-engineer ve validate'', which at a 28-tree workspace root reports ~723 phantom
    structural errors and then instructs fixing them all — with a manifest present
    the mandate must prescribe ''ve workspace validate'' (via uvx) instead; (d) document
    code_references (with #Symbol::method anchors and implements: prose) as preferred
    over legacy code_paths, since 0.4.0 validates both; (e) point at ve deletion record
    / docs/trunk/DELETIONS.md for gone-target references so ''delete the reference''
    stops being the obvious move. Raw material: a field-written section covering all
    five, archived at /private/tmp/claude-501/-Users-btaylor-Projects-vibe-engineer/cd285902-cffd-44ec-a8d8-f49e76069245/scratchpad/cc_federation_section.md
    — take the shape, genericize the prose (28-tree counts, CI job names, and package
    examples are theirs). Render context work: the template needs to know whether
    the project sits in a workspace; thread that through TemplateContext/render_template
    in src/template_system.py and Project._init_agents_md in src/project.py. Single-tree
    projects must render byte-identically to today.'
  depends_on: []
  chunk_directory: template_workspace_awareness
- prompt: 'Make ve init announce the AGENTS.md/CLAUDE.md arrangement it creates. Project._init_agents_md
    (src/project.py) converts a tracked regular CLAUDE.md into a symlink to a new
    AGENTS.md with no mention in output — operators see a surprise ''T'' typechange
    in git status (field report: ''an operator who commits without looking lands a
    file-type change they did not ask for''). Emit one line naming what happened (created
    AGENTS.md, converted CLAUDE.md to a symlink, or updated the managed block in place)
    through the existing InitResult reporting in src/cli/init_cmd.py. Output-only
    chunk: no behavior change to the arrangement itself.'
  depends_on: []
  chunk_directory: claudemd_symlink_notice
- prompt: 'Make the VE:MANAGED block safe to live next to. Field incident: two operator
    security directives authored inside the managed region of a production AGENTS.md
    were silently deleted by ve init regeneration — no warning, no diff, while user-authored
    FILES do get ''Preserved ...'' notices (the asymmetry is the bug). Three coordinated
    fixes, ranked by the field reporter: (1) self-documenting markers — the template''s
    VE:MANAGED:START/END lines say what they mean: content between them is regenerated
    and destroyed by ve init; put project content above START or below END (adapt
    the archived field-tested warning wording in /private/tmp/claude-501/-Users-btaylor-Projects-vibe-engineer/cd285902-cffd-44ec-a8d8-f49e76069245/scratchpad/cc_federation_section.md;
    keep parse_markers in src/project.py recognizing both bare and annotated marker
    forms so existing files keep parsing); (2) seed a safe region on first write —
    a fresh AGENTS.md must not begin at START and end at END with nowhere correct
    to write; put a short ''project-specific content goes here'' region outside the
    markers; (3) warn instead of silently dropping — when regeneration replaces a
    managed block whose current content differs from what the template last produced
    AND contains lines the incoming render does not, report that operator content
    inside the block was discarded (naming the file) through InitResult warnings.
    Above-START/below-END preservation in Project._init_agents_md is designed behavior
    — state it in output or docs, do not change it. Tests: tests/test_project.py,
    tests/test_migration markers tests if present.'
  depends_on:
  - 0
  - 1
  chunk_directory: claudemd_marker_safety
created_after:
- cursor_plugin_port
---

## Advances Trunk Goal

"Required Properties: Following the workflow must maintain the health of
documents over time and should not grow more difficult over time." `ve init`
is the workflow's most-repeated touchpoint; when regeneration destroys
operator directives or teaches a single-tree working arrangement to a
28-tree workspace, the workflow actively degrades document health. This
narrative makes the regenerated instructions match the repository they land
in, and makes regeneration incapable of silently destroying what operators
wrote.

## Driving Ambition

The third Cloud Capital field report (2026-08-01, after driving their
28-member workspace to zero defects on ve 0.4.0) found four things wrong with
`ve init` in a federated repository, one of which cost real content: operator
security directives authored inside the VE:MANAGED block were silently
destroyed on regeneration (first write leaves no safe region and the bare
markers say nothing); the CLAUDE.md→symlink conversion is unannounced; and —
the big one — the regenerated managed block is single-tree-shaped even when
.ve-workspace.yaml exists, to the point of actively wrong advice: our own
rename mandate tells workspace agents to run the single-tree validator, which
reports ~723 phantoms at their root. (A fourth finding — ve init deleting
.agents/skills/, the vendor-neutral harness surface — is held out of this
narrative pending an operator policy decision.)

Success: a fresh or regenerated AGENTS.md in a workspace teaches the
qualified reference form, peer pointers, the right validator, and the
deletion ledger; a single-tree render is byte-identical to today; the managed
markers explain themselves; first write seeds a safe region; and dropping
operator content ever again requires ve init to say so out loud. The
reporter offered their 28-tree, zero-defect repo as a regression target for
the workspace-aware template.

## Chunks

1. `template_workspace_awareness` — workspace-aware managed block: qualified
   form, peer pointers + 1-reader/2+-readers rule, workspace validate in the
   rename mandate, code_references guidance, deletion ledger pointer.
   (prompt 0)
2. `claudemd_symlink_notice` — ve init announces the AGENTS.md/CLAUDE.md
   arrangement it creates. (prompt 1)
3. `claudemd_marker_safety` — self-documenting markers, seeded safe region
   on first write, loud warning when regeneration discards in-block operator
   content. (prompt 2, after 1 and 2 — all three touch the template and
   _init_agents_md; this one reshapes the file edges both others render
   through)

## Completion Criteria

When complete, an operator in a federated workspace can run `ve init` and:

- the regenerated agent instructions demonstrate member-qualified
  references, peer pointers with the 1-reader/2+-readers rule, prescribe
  `ve workspace validate` wherever a manifest is present, prefer
  code_references, and point at the deletion ledger — while single-tree
  projects render exactly as before;
- see in the output what happened to AGENTS.md and CLAUDE.md;
- read on the markers themselves what `ve init` will and will not touch,
  have somewhere safe to write from the very first render, and never again
  lose in-block content without ve init saying so.

Acceptance beyond unit tests: the field reporter runs the workspace-aware
render against their 28-tree, zero-defect repository and confirms it
describes that repo's actual working arrangement.
