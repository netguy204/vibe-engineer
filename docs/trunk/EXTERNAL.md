<!-- Chunk: docs/chunks/claudemd_external_prompt - Full External Artifacts documentation -->
<!-- Chunk: docs/chunks/progressive_disclosure_external - Comprehensive external artifacts documentation -->
<!-- Chunk: docs/chunks/federation_peer_refs - Peer (tree) references, why: notes, and the point-vs-promote rule -->
# External Artifacts Reference

External artifacts are pointers: an artifact directory that records where the real
document lives instead of holding it. They come in two flavors, and the difference
is how far away the target is:

- **Cross-repository** (`repo: org/other-repo`) — the target lives in another
  repository with its own history, so the pointer names a branch to track and VE
  fetches the content for you.
- **Peer** (`tree: <member>`) — the target lives in another VE tree of the *same*
  working copy, registered in the workspace manifest (`.ve-workspace.yaml`). There
  is nothing to fetch and no branch to track: same working copy means same commit,
  so resolution is a manifest lookup and a file read.

Both flavors express the same thing — *this tree depends on an artifact it does not
own* — and both may carry a `why:` note saying what the dependency is.

## What External Artifacts Are

An artifact directory may contain an `external.yaml` file instead of the usual
GOAL.md or OVERVIEW.md. That file tells VE where to find the actual artifact
content. Every VE command treats such a directory uniformly regardless of flavor:
it is "an artifact whose content lives elsewhere".

**Cross-repo scenario:** A task directory spans three repositories. Each repo has
`docs/chunks/shared_feature/external.yaml` pointing to a single canonical chunk
GOAL.md in one repository.

**Peer scenario:** A monorepo holds a library tree and a visualization tree. The
library owns `docs/subsystems/commitment_baseline` because its code enforces that
invariant; the visualization tree has
`docs/subsystems/commitment_baseline/external.yaml` pointing at the library tree,
recording that it reads those definitions.

## File Structure

A cross-repository reference:

```yaml
artifact_id: some_feature
artifact_type: chunk          # chunk, narrative, investigation, or subsystem
repo: org/other-repo          # Repository containing the actual artifact
track: main                   # Branch to follow
```

A peer reference:

```yaml
artifact_id: commitment_baseline
artifact_type: subsystem
tree: pybusiness              # Workspace member owning the artifact
why: Charts render realized savings from this baseline
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `artifact_id` | Yes | The artifact's directory name in the owning tree or repo |
| `artifact_type` | Yes | One of: `chunk`, `narrative`, `investigation`, `subsystem` |
| `repo` | Cross-repo only | GitHub repository path (e.g., `org/repo-name`) |
| `tree` | Peer only | Workspace member name from `.ve-workspace.yaml` |
| `track` | Cross-repo only | Branch name to follow (usually `main`) |
| `why` | No | One line: what this tree depends on in the target |
| `last_resolved` | Written by VE | UTC instant of the last successful resolve |

Exactly one of `repo` and `tree` must be present — a pointer with neither has no
target, and a pointer with both has two. `track` (and the legacy `pinned`) are
rejected alongside `tree`: a peer target is already at the same commit as the tree
pointing at it, so there is nothing to pin. `last_resolved` is rejected alongside
`tree` for the same reason — see below.

### `last_resolved`: Has Anybody Ever Looked?

`ve external resolve` writes `last_resolved` into a `repo:` pointer every time it
reads the target successfully; a failed resolve leaves it untouched. Don't
hand-edit it.

`ve validate` reports a `repo:` pointer with **no** `last_resolved` as
`external→never-resolved` — a warning, naming the `ve external resolve` command
that clears it.

This does not reopen the decision two sections below. VE still declines to say
whether a cross-repository target *exists*, because that needs network or cache
state. The never-resolved finding needs neither: *"no successful read has ever
been recorded"* is a fact about the local file. VE does not claim the target is
missing; it reports that nobody has ever checked.

The distinction earns its keep because the two cases are not equally likely to be
fine. A pointer created months ago that has never once resolved may have dangled
**from birth** — the far side committed nothing, and nothing ever noticed.
Such a directory is worse than absent when it is named for the subject someone is
investigating: it is the most on-target hit their search returns, and it answers
*"someone already looked at this and it went nowhere"* with more authority than
finding nothing at all.

It is a warning rather than an error because every pointer is never-resolved from
the moment it is written until someone resolves it. An error would fail correctly
created work, and a gate that fails correct work is one people learn to skip.

Peer (`tree:`) pointers carry no `last_resolved`: they resolve through the
manifest against the same commit, so `ve workspace validate` already answers the
question structurally and reports a broken one as `missing-target`.

## Peer References (Same Repository)

Peer references require a workspace manifest at the root of the repository holding
your VE trees, because a member name is what the pointer resolves against:

```yaml
# .ve-workspace.yaml
members:
  pybusiness: packages/libs/pybusiness
  viz: apps/viz
```

Create a pointer with `ve external point`, run from the tree that has the
dependency:

```bash
cd apps/viz
ve external point pybusiness docs/subsystems/commitment_baseline \
  --why "Charts render realized savings from this baseline"
```

This writes `apps/viz/docs/subsystems/commitment_baseline/external.yaml`. The
artifact may be named as `docs/<type>/<name>`, `<type>/<name>`, or — when it
already exists in the member's tree — just `<name>`. Useful options:

| Option | Effect |
|--------|--------|
| `--why` | Record what this tree depends on (one line) |
| `--name` | Use a different local directory name than the target's |
| `--force` | Create the pointer even though the target does not exist yet |

The command **refuses** to point at an artifact that does not exist in the member's
tree unless you pass `--force`. A pointer that was never resolvable produces no
deletion event for an audit to find, so the cheapest place to catch it is at
creation.

**Resolution is trackless and cache-free.** A peer reference resolves through the
manifest to `<member_path>/docs/<type>/<artifact_id>` and reads the working copy —
uncommitted changes included, because the whole point is that both trees move
together. Resolution starts from the pointer's own directory, never the working
directory of the command, so a reference means the same thing no matter where it is
followed from.

**Interest edges may form cycles.** Two trees may point at each other's artifacts;
that is a normal consequence of mutual dependency. Only `created_after` causal
ordering must stay acyclic.

## Point When Readers Multiply; Promote When Writers Change

When an artifact acquires readers outside the tree that owns it, the tempting move
is to *promote* it — move the document up to the repository-root tree where
everyone can see it. Resist that.

- **Point when readers multiply.** A new consumer adds a pointer at its own level,
  peer-to-peer. Ownership does not move: the subsystem doc stays beside the code
  that enforces its invariants, where a change to that code will be made by someone
  reading it.
- **Promote when writers change.** Promotion is an *ownership* operation. Move an
  artifact to the root tree when the intent genuinely has no single owner — several
  trees write to it and none governs it.

Promoting on every new reader converges on everything living at the root, which is
flattening by another name: it dislocates documents from the code they govern and
records nothing about who consumes what. Pointers, by contrast, keep ownership put
and make the consumer set enumerable.

## Querying Interest in Reverse

Pointers are directed edges, and the cost of keeping ownership put is that a
document no longer sits somewhere everyone browses. Two commands pay that cost
with queries instead of with ownership dislocation.

### Who consumes this artifact?

```bash
ve artifact consumers docs/subsystems/commitment_baseline
```

Run from the tree that owns the artifact (or anywhere inside it — `--project-dir`
resolves to the nearest enclosing tree). The command walks every member the
manifest names and reports each inbound pointer with its member name, the
pointer's own location, and its `why:` note. `ARTIFACT_PATH` accepts
`docs/<type>/<name>`, `<type>/<name>`, or a bare `<name>` that exists in this
tree.

The report keeps two kinds of answer apart, because they carry different
certainty:

| Section | Match | Meaning |
|---------|-------|---------|
| Consumers | Resolved target directory | The pointer resolves to *this* artifact — the same resolution `ve external resolve` performs |
| Cross-repo pointers | Artifact id | A `repo:` pointer names an artifact with this id in another repository; nothing inside the workspace can verify it is this one |

Failure modes are distinguished rather than collapsed into "none":

- **No manifest** — exit 1. There is no registry of trees to search; run
  `ve workspace init --scan`.
- **Owning tree not registered** — exit 1. A peer pointer names a member, so
  nothing can address an unregistered tree's artifacts; run `ve workspace add`.
- **No consumers** — exit 0, stating plainly that no tree points here.
- **Artifact missing** — the query is still answered, with a warning. Pointers at
  an artifact that was renamed or deleted are exactly what needs finding: their
  disappearance produced no event an audit could catch.

Pointers that cannot be parsed are listed too. A pointer nobody can read is a
finding, not a reason to abandon the query.

### What exists across the whole workspace?

```bash
ve chunk list --workspace
ve subsystem list --workspace
```

Both walk every member tree and print one row per artifact, addressed as a
qualified reference:

```
pybusiness::docs/chunks/baseline_calc [ACTIVE]
viz::docs/chunks/baseline_chart [FUTURE]
viz::docs/subsystems/commitment_baseline [EXTERNAL: tree:pybusiness]
```

A row is therefore a working address: paste it into a backreference and it
resolves from anywhere in the workspace, which a bare `docs/...` row would not.
Status filters compose (`ve chunk list --workspace --future` answers "what is
queued anywhere?"); `--json` adds a `member` field to each row.

Two properties worth knowing:

- **Aggregation is read-only.** Artifact directories are enumerated rather than
  ordered through the artifact index, so browsing never writes an ordering file
  into a member tree. The price is that aggregated rows carry no tip indicator and
  no causal ordering — both describe one tree's DAG and do not merge across trees.
- **Cursor flags do not aggregate.** `--current`, `--last-active`, and `--recent`
  name a position in one tree's history; combined with `--workspace` they are
  refused rather than silently answered for an arbitrary tree.

A registered tree that has vanished is reported as a warning and the remaining
members still list, so one stale manifest entry does not hide the workspace.

## Pointer-Only Trees

A tree may consist of *nothing but* pointers: interest edges naming what it reads,
with no `docs/trunk/` of its own. This is the lightweight membership tier, and it is
what a scaffolded package should get by default.

Such a package is fully addressable — other trees reference it as
`<member>::docs/...`, and its own pointers resolve normally — while **not** being an
addressing root. Membership and governance are separate predicates on purpose:
registration accepts any `docs/` directory holding an artifact directory, whereas a
bare reference resolves against the nearest enclosing directory holding
`docs/trunk/`. A pointer-only package therefore has local names for the intent it
consumes without capturing the bare references written beneath it.

```bash
ve package scaffold apps/viz \
  --interest 'pybusiness::docs/subsystems/commitment_baseline: charts render this baseline'
```

That writes `apps/viz/docs/subsystems/commitment_baseline/external.yaml`, registers
`viz` in `.ve-workspace.yaml`, and renders an `AGENTS.md` telling agents which tree
governs the package. It creates no `docs/trunk/` and no artifact directory that holds
no pointer — an empty `docs/chunks/` would be a new namespace and nothing else.

Scaffolding is where a monorepo's namespace count comes from. A package template that
ships a literal `docs/trunk` + `docs/chunks` mints a namespace per generated package
*by construction*, so cleanup regresses with the next `cookiecutter` run; a template
that calls `ve package scaffold` instead mints none. `--full-tree` is the opt-in for a
package that will own intent of its own, and `ve init` inside a workspace says out
loud that it is creating a new addressing root.

Promotion from pointer-only to full tree stays available (`ve init` in the package,
then `ve workspace add`) and is an ownership decision: a trunk means bare references
in files beneath that directory stop resolving upward and start resolving there.

## Bringing a Workspace Into Compliance

Compliance is a loop, not a cleanup. `ve workspace validate` walks every source
file in the repository and every registered member's artifacts and reports each
reference that does not resolve, with a **fix class** naming the kind of repair it
needs. It exits nonzero on any defect, so CI can gate on it, and
`--format json` is the machine-readable form the fix loop consumes.

| Fix class | What it means |
|-----------|---------------|
| `misrouted-bare` | A bare reference that resolves in *some other* tree — the silent failure, correct-looking from one working directory and wrong from another |
| `unresolvable-bare` | A bare reference no tree in the workspace can resolve; it may never have resolved anywhere, and nothing recorded its disappearance |
| `unknown-qualifier` | `<name>::docs/...` or a pointer's `tree:` naming no registered member |
| `missing-target` | The tree resolves but holds no such artifact — a renamed or moved target |
| `malformed-qualifier` | Legacy prefix style (`architecture/docs/chunks/x`), which reads like an address but is a path |
| `unresolvable-frontmatter` | A `code_references` entry pointing at a file or symbol that is gone |

Each defect carries `path:line`, the reference as written, and the **candidate
trees that do hold the named artifact**. The candidate count is what separates a
mechanical repair from a judgment call: exactly one candidate is an answer the
tooling already computed, two are two plausible meanings, and none means the
target is gone from the whole repository.

The `/workspace-validate-fix` command drives the report to zero. It groups
defects by fix class, applies the mechanical repairs (qualify a one-off
cross-tree reference; record a peer pointer when several references in one tree
read the same foreign artifact; normalize a legacy qualifier; retarget a pointer
whose artifact moved; `ve workspace add` a tree a candidate names), escalates the
rest to the operator with the candidates listed, and re-runs until clean. It
never deletes a reference and never fabricates a target: a reference is the
record that this code is governed by that intent, so an ambiguous one is a
question, not a cleanup opportunity. Fixes land in fix-class-grouped batches, so
"all qualifications" can be reviewed apart from "all new pointers".

Two limits are stated on every run rather than hidden. Only backreference
comments starting at column 0 are scanned, so a clean run means every column-0
reference resolves, not every reference. And `org/repo` targets are reported as
*unverified* rather than checked, because resolving them needs network or cache
state, and a gate whose verdict depends on a warm cache is not a gate.

## Resolving External Artifacts

Use the `ve external resolve` command to view the actual artifact content:

```bash
ve external resolve <artifact_id>
```

For a cross-repository reference this fetches the current HEAD of the tracked
branch — you don't need to clone the external repo, VE handles the fetch. For a
peer reference it resolves through the workspace manifest and reads the file
directly; the output reports the target (`tree:pybusiness`) and the `why:` note so
the reason for the dependency travels with the content.

When a peer reference cannot be resolved, the error distinguishes the cases: no
workspace manifest above the pointer, a member name the manifest does not
register, a registered member whose tree has no such artifact, and an artifact
directory with no main document.

## Common Scenarios

### Task Directories Spanning Multiple Projects

When a feature touches multiple codebases, create the canonical chunk in one repository and use `external.yaml` pointers in the others:

```
# In repo-a (canonical)
docs/chunks/shared_feature/GOAL.md
docs/chunks/shared_feature/PLAN.md

# In repo-b (pointer)
docs/chunks/shared_feature/external.yaml
```

Each repository's codebase can reference the chunk using local paths (`docs/chunks/shared_feature`), while the actual documentation lives in a single location.

### Shared Narratives Across Codebases

Multi-repo initiatives can use a shared narrative:

```yaml
# docs/narratives/cross_repo_initiative/external.yaml
artifact_id: cross_repo_initiative
artifact_type: narrative
repo: org/planning-repo
track: main
```

All participating repositories can reference the narrative in chunk frontmatter using the local path.

### Cross-Repository Investigations

When investigating issues that span repositories:

```yaml
# docs/investigations/api_latency/external.yaml
artifact_id: api_latency
artifact_type: investigation
repo: org/core-services
track: main
```

The investigation findings and proposed chunks live in one place, but all affected repos can reference it.

## Code Backreferences with External Artifacts

When adding code backreferences, always use the **local path** within the current repository:

```python
# Chunk: docs/chunks/shared_feature - Implements the shared feature
```

Even if the chunk is external, the local `docs/chunks/shared_feature/` directory exists (containing `external.yaml`), so the path is valid. This keeps backreferences consistent regardless of whether the artifact is local or external.

## Directory Layout

An external artifact directory contains only the `external.yaml` file:

```
docs/chunks/external_feature/
└── external.yaml
```

Contrast with a local artifact:

```
docs/chunks/local_feature/
├── GOAL.md
└── PLAN.md
```

VE commands recognize both patterns and handle them appropriately.

## When to Use External Artifacts

**Use external artifacts when:**
- Work spans multiple repositories
- You need a single source of truth for documentation
- Teams coordinate across codebases on shared initiatives
- Task directories cross project boundaries

**Avoid external artifacts when:**
- Work is contained within a single repository
- The overhead of cross-repo coordination isn't justified
- You need offline access to all documentation

## Demoting External Artifacts

Over time a cross-repo chunk's scope may collapse — the implementation ended up
landing entirely in one repository. When that happens, carrying the architecture
source directory and all the pointer directories is unnecessary overhead. The
demotion commands let you collapse this bookkeeping.

### Two demotion commands

| Command | When to use | What it does |
|---------|-------------|--------------|
| `ve task demote <name>` | Standard demotion — scope may still span multiple repos | Copies artifact to target project, removes the target's pointer, updates the `dependents` list in the architecture source. Architecture source stays in place. |
| `ve chunk demote <name> <target>` | Full-collapse — scope has definitively landed in one repo | Strips `org/repo::` prefixes from `code_paths` and `code_references`, removes the `dependents` block, deletes pointer dirs in all other participating projects, and removes the architecture source directory entirely. |

### When to use `ve chunk demote`

Use `ve chunk demote` when **all** of the following are true:

1. The chunk is implemented — `status` is `ACTIVE` or `IMPLEMENTING` and the
   work is known to be single-project.
2. Every `code_path` in the chunk's GOAL.md references only the target project
   (or carries no cross-repo prefix at all).
3. All other participating projects only have `external.yaml` pointer directories
   (not real GOAL.md content).

The command **refuses** with a clear error if any `code_path` references a repo
other than the target, pointing at the offending entries. This prevents silent
corruption of frontmatter.

### What `ve chunk demote` does

Running `ve chunk demote <chunk_name> <target_project>` from a task directory:

1. Validates the architecture source exists and the target project has a pointer.
2. Verifies all `code_paths` are scoped to the target (or bare).
3. Copies `GOAL.md` and `PLAN.md` to `<target_project>/docs/chunks/<chunk_name>/`.
4. Rewrites frontmatter in the target:
   - Strips `org/repo::` prefix from `code_paths` and `code_references[].ref`
   - Removes the `dependents` block entirely
5. Deletes `external.yaml` pointer directories in every other participating project.
6. Removes `architecture/docs/chunks/<chunk_name>/` from the filesystem.

Decision documents at `architecture/docs/reviewers/baseline/decisions/<chunk_name>_*.md`
are **preserved** — these are review-history artifacts, not chunk artifacts.

### Invariants enforced

- No dangling pointer directories left after demotion.
- No `org/repo::` prefix pollution in the demoted chunk's frontmatter.
- No silent demotion when scope hasn't actually collapsed (scope validator rejects it).
- The operation is **idempotent**: re-running a partially-completed demotion
  finishes the remaining steps rather than failing or duplicating state.

### After demotion: commit changes

`ve chunk demote` makes filesystem changes only — it does not run `git` commands.
After a successful demotion, commit the changes in each affected repository:

```bash
# In the target project
git add docs/chunks/<chunk_name>/
git commit -m "Demote <chunk_name> from architecture (full-collapse)"

# In each other participating project
git rm -r docs/chunks/<chunk_name>/
git commit -m "Remove external pointer for demoted chunk <chunk_name>"

# In the architecture repo
git rm -r docs/chunks/<chunk_name>/   # or verify it's already absent
git commit -m "Remove architecture source for demoted chunk <chunk_name>"
```

### When NOT to use `ve chunk demote`

- When implementation is **not yet complete** and scope is still uncertain.
- When any `code_path` references more than one repository — use `ve task demote`
  (which leaves the architecture source intact) or split the chunk first.
- When another participating project has real GOAL.md content (not a pointer) — the
  command will refuse and tell you which project has conflicting content.
