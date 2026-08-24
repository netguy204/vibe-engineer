# Deletion Grants

<!--
GUIDANCE FOR AGENTS — DO NOT REMOVE THIS COMMENT

This ledger records operator-authorized reference deletions. It is managed by
`ve deletion record`; do not append entries by hand.

Deleting a backreference or code_reference is normally out of vocabulary for
validation fix loops: a reference is somebody's record of governing intent.
When code was deliberately deleted and the operator explicitly authorizes
removing the reference to it, the grant is recorded here BEFORE the reference
is removed, so the deletion and its authorization land in the same diff and a
reviewer can see the grant.

Each entry carries: the reference as written, the location it was deleted
from, who authorized it, why, and (when available) the absence evidence —
typically the summary line of `ve exists <name>`.
-->

## Grants

### D001: 2026-08-07 — `tests/fixtures/claude_md_single_tree.md` deleted from `docs/chunks/claudemd_marker_safety/GOAL.md:12`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The fixture pinned the render of src/templates/claude/CLAUDE.md.jinja2, a template deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical; CLAUDE.md is a symlink). The intent the entry carried — pinning the single-tree render byte-for-byte — is fully held by the sibling entry tests/fixtures/agents_md_single_tree.md, which both chunks already list.
- **Evidence**: ve exists: Absent: 0 matches for 'tests/fixtures/claude_md_single_tree.md' (scanned 2059 files)

### D002: 2026-08-07 — `tests/fixtures/claude_md_single_tree.md` deleted from `docs/chunks/template_workspace_awareness/GOAL.md:13`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The fixture pinned the render of src/templates/claude/CLAUDE.md.jinja2, a template deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical; CLAUDE.md is a symlink). The intent the entry carried — pinning the single-tree render byte-for-byte — is fully held by the sibling entry tests/fixtures/agents_md_single_tree.md, which both chunks already list.
- **Evidence**: ve exists: Absent: 0 matches for 'tests/fixtures/claude_md_single_tree.md' (scanned 2059 files)

### D003: 2026-08-07 — `src/templates/claude/CLAUDE.md.jinja2 (mirror code_references entry)` deleted from `docs/chunks/claudemd_marker_safety/GOAL.md:17`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The entry described src/templates/claude/CLAUDE.md.jinja2 as a lockstep mirror kept content-identical to AGENTS.md.jinja2. That template was deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical, CLAUDE.md is a symlink). ve refactor move retargeted the ref onto AGENTS.md.jinja2, leaving the entry asserting that the file mirrors itself. The mirroring intent no longer exists; the sibling entry on the same file carries the surviving intent.
- **Evidence**: ve exists: Absent: 0 matches for 'src/templates/claude/CLAUDE.md.jinja2'

### D004: 2026-08-07 — `src/templates/claude/CLAUDE.md.jinja2 (mirror code_references entry)` deleted from `docs/chunks/federation_tree_discovery/GOAL.md:40`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The entry described src/templates/claude/CLAUDE.md.jinja2 as a lockstep mirror kept content-identical to AGENTS.md.jinja2. That template was deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical, CLAUDE.md is a symlink). ve refactor move retargeted the ref onto AGENTS.md.jinja2, leaving the entry asserting that the file mirrors itself. The mirroring intent no longer exists; the sibling entry on the same file carries the surviving intent.
- **Evidence**: ve exists: Absent: 0 matches for 'src/templates/claude/CLAUDE.md.jinja2'

### D005: 2026-08-07 — `src/templates/claude/CLAUDE.md.jinja2 (mirror code_references entry)` deleted from `docs/chunks/plugin_init_slimdown/GOAL.md:33`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The entry described src/templates/claude/CLAUDE.md.jinja2 as a lockstep mirror kept content-identical to AGENTS.md.jinja2. That template was deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical, CLAUDE.md is a symlink). ve refactor move retargeted the ref onto AGENTS.md.jinja2, leaving the entry asserting that the file mirrors itself. The mirroring intent no longer exists; the sibling entry on the same file carries the surviving intent.
- **Evidence**: ve exists: Absent: 0 matches for 'src/templates/claude/CLAUDE.md.jinja2'

### D006: 2026-08-07 — `src/templates/claude/CLAUDE.md.jinja2 (mirror code_references entry)` deleted from `docs/chunks/template_workspace_awareness/GOAL.md:18`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The entry described src/templates/claude/CLAUDE.md.jinja2 as a lockstep mirror kept content-identical to AGENTS.md.jinja2. That template was deleted in priorart_subject_search because nothing in src/ rendered it (AGENTS.md is canonical, CLAUDE.md is a symlink). ve refactor move retargeted the ref onto AGENTS.md.jinja2, leaving the entry asserting that the file mirrors itself. The mirroring intent no longer exists; the sibling entry on the same file carries the surviving intent.
- **Evidence**: ve exists: Absent: 0 matches for 'src/templates/claude/CLAUDE.md.jinja2'

### D007: 2026-08-14 — `src/task_init.py#TaskInit::_render_skills` deleted from `docs/chunks/agentskills_migration/GOAL.md:29`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: The symbol was deleted by plugin_init_slimdown (402e280) when DEC-010 moved skill distribution to the plugin: ve init/task-init no longer render skills into .agents/skills/, so the intent this reference guarded no longer exists in code. Found by a symbol-anchor spot check during plugin_local_skills completion; ve validate does not check symbol anchors, which is why it sat broken.
- **Evidence**: ve exists: Absent: 0 matches for 'TaskInit::_render_skills'

### D008: 2026-08-14 — `src/project.py#Project::_init_skills` deleted from `docs/chunks/agentskills_migration/GOAL.md:21`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: Deleted by plugin_init_slimdown (402e280) with DEC-010: ve init stopped rendering skills into .agents/skills/, so the intent this reference guarded (per-project skill rendering with .claude/commands symlinks) no longer exists in code. Same migration casualty as D007, same chunk.
- **Evidence**: grep src/project.py: class Project has no _init_skills; ve exists absent

### D009: 2026-08-24 — `src/investigations.py#Investigations::get_status` deleted from `docs/chunks/valid_transitions/GOAL.md:32`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: artifact_manager_base hoisted get_status from the per-type managers into ArtifactManager; Investigations no longer defines it. The sibling Narratives::get_status entry is repointed to src/artifact_manager.py#ArtifactManager::get_status in the same diff, which now carries the intent for every artifact type; a second entry on the same base symbol would be a duplicate.
- **Evidence**: Absent: 0 matches for 'Investigations::get_status'.

### D010: 2026-08-24 — `src/investigations.py#Investigations::update_status` deleted from `docs/chunks/valid_transitions/GOAL.md:34`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: artifact_manager_base hoisted update_status into ArtifactManager; Investigations no longer defines it. The sibling Narratives::update_status entry is repointed to src/artifact_manager.py#ArtifactManager::update_status in the same diff, which now carries the transition-validation intent for every artifact type; a second entry on the same base symbol would be a duplicate.
- **Evidence**: Absent: 0 matches for 'Investigations::update_status'.

### D011: 2026-08-24 — `src/investigations.py#Investigations::_update_overview_frontmatter` deleted from `docs/chunks/valid_transitions/GOAL.md:36`

- **Authorized by**: brian@cloudcapital.co
- **Reason**: artifact_manager_base hoisted the frontmatter-update helper into ArtifactManager._update_frontmatter; Investigations no longer defines _update_overview_frontmatter. The sibling Narratives entry is repointed to src/artifact_manager.py#ArtifactManager::_update_frontmatter in the same diff; a second entry on the same base symbol would be a duplicate.
- **Evidence**: Absent: 0 matches for 'Investigations::_update_overview_frontmatter'.
