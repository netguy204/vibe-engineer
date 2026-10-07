---
name: workspace-validate-fix
description: Drive `ve workspace validate` to zero across a monorepo of VE trees. Runs the validator, groups defects by fix class, applies the mechanical fixes (qualify a cross-tree reference, create a peer pointer, normalize a legacy qualifier, retarget a stale pointer, register an unlisted tree), escalates the genuine judgment calls with their candidates, and loops until clean. Use when `ve workspace validate` fails, when a CI resolution gate is red, or when retrofitting a monorepo whose backreferences resolve differently depending on where you stand.
---

<!-- GENERATED from src/templates/plugin/skills/workspace-validate-fix.md.jinja2 — edit that template and run `ve plugin render --flavor cursor`; direct edits here will be overwritten. -->
<!-- Chunk: docs/chunks/federation_validate_fix_skill - Workspace compliance loop -->

## Context

Run these commands first and read their output as the context for everything
below. They are safe, read-only probes; run all of them before acting on any
instruction in this skill.

- **ve CLI** — run: `ve --help >/dev/null 2>&1 && echo "installed" || echo "(ve CLI not found)"`
- **Workspace manifest** — run: `cat .ve-workspace.yaml 2>/dev/null || echo "(no .ve-workspace.yaml in this directory)"`
- **Project config** — run: `cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults apply)"`
- **Project hook** — run: `ve hooks show workspace-validate-fix 2>/dev/null || echo "(no project hook)"`

## Runtime context

Interpret the context above before following the instructions:

- **ve CLI**: The `ve` command is an installed CLI tool, not a file in the
  repository. Do not search for it — run it directly via Bash. If the context
  shows "(ve CLI not found)", tell the operator that the vibe-engineer plugin
  requires the separately installed `ve` CLI, suggest
  `uv tool install vibe-engineer` (or `pip install vibe-engineer`), and stop.
- **Workspace manifest**: `.ve-workspace.yaml` names the VE trees in this
  repository, and it is the resolution surface this whole loop depends on —
  nothing can be qualified against a tree the manifest does not name. Every
  command below takes `--workspace-dir`, which searches *upward*, so run from
  anywhere inside the workspace. If the context shows no manifest here, check
  whether one exists above you (`ve workspace list`). If there is none at all,
  tell the operator that `ve workspace init --scan` bootstraps one — it proposes
  the trees it finds and asks before writing — and stop. Do not write a manifest
  yourself: which directories are intentional trees is the operator's call.
- **Single-tree project**: If the repository holds exactly one VE tree, this
  command has nothing to do. Use `/validate-fix`, which drives the single-tree
  validator (`ve validate`).
- **Project config**: `.ve-config.yaml` holds project configuration. When the
  context shows "(no .ve-config.yaml — defaults apply)", use the defaults.
- **Project hook**: `docs/hooks/workspace-validate-fix.md` holds this repository's
  own requirements for this command. When the context shows hook content,
  treat it as a binding instruction from the operator: satisfy it before
  reporting this command complete, and say so when you do. When it shows
  "(no project hook)", there are none. If a hook contradicts this command's
  own instructions, do not silently choose — surface the conflict to the
  operator and ask.

## Arguments

The operator's request optionally scopes the pass. It may be a fix class
(`misrouted-bare`), a member name (`pybusiness`), or a path prefix
(`packages/libs/`). Scope filters which defects you *fix*; always run the
validator over the whole workspace, and always report the out-of-scope defects
you left alone. With no arguments, work the whole report.

## Overview

`ve workspace validate` reports every reference in the repository that does not
resolve, each with a fix class. This command is the loop that drives that report
to zero:

1. Run the validator and read the JSON.
2. Group the defects by fix class.
3. Apply the mechanical fixes — the ones where the validator already computed a
   unique answer.
4. Collect the judgment calls as escalations, with their candidates.
5. Re-run the validator and repeat.

The loop terminates when the report is clean, when only escalations remain, or
after **10 iterations** — whichever comes first. It also stops when a pass makes
**no progress**: the report is deterministic and byte-stable across runs, so if
the same defect set survives a pass that claimed to fix something, the fix did
not take. Say so and stop rather than looping.

This is the retrofit workflow for a monorepo whose trees grew independently. It
is also safe to run on a clean workspace: the first validation returns `ok: true`
and you are done.

## Invariants

These are not preferences. Breaking one of them destroys information that no
audit can recover, which is the failure this tooling exists to prevent.

- **Never delete a reference.** Outside tier 1 below, your entire edit
  vocabulary is: insert a qualifier prefix, normalize a qualifier, create a
  pointer, retarget a pointer, register a tree, correct a `code_references`
  path. A reference is somebody's
  record that this code is governed by that intent. If the only way to satisfy
  the validator would be removing the reference, that is an escalation, not a
  fix. Peer-pointer coverage is never grounds for deletion either: "this ref is
  covered by the pointer" is not deduplication, because the pointer records a
  tree-level interest edge and a chunk's `code_references` typically name only
  its public surface — a backreference on a private helper is often the only
  record anywhere tying that code to its intent, and deleting it loses that
  record without any validator ever noticing. Removing a reference falls in
  one of three tiers:
  1. **Ordinary edit: no grant, no escalation.** The author of a diff that
     removes or moves code updates the references to that code in the same
     diff while the intent they recorded survives: retarget a reference to
     the code that now carries the intent, drop it if another reference
     already covers that intent, or drop it when the intent no longer belongs
     to any chunk. The PR reviewer checks it in the diff. This tier applies to
     you only when the defect points at code removed by the current,
     uncommitted diff.
  2. **Operator sign-off plus a ledger entry.** Removing the last reference
     that carries a chunk's intent abandons that intent. This includes a diff
     that deletes the code carrying a chunk's whole intent: sign-off wins over
     tier 1.
  3. **Fix loops: this skill's usual case.** For a reference to code deleted
     earlier, outside the current diff, gather evidence with `ve exists
     <name>`; a same-name match elsewhere means the target moved, so retarget
     it. Otherwise present the case to the operator. When the **operator
     explicitly authorizes** deleting it, record the grant *first* with
     `ve deletion record <reference> --location <file:line> --by <operator>
     --reason "<why>" --evidence "<ve exists summary>"`. It writes the grant
     into the governing tree's `docs/trunk/DELETIONS.md`, so the
     authorization lands in the same diff as the deletion. Then remove the
     reference, and report it under **Authorized deletions**, never as a fix.

  Never delete a reference just to make the validator pass. A tier 2 or tier 3
  deletion the ledger does not know about is out of vocabulary, and nothing an
  agent says counts as the operator's grant.
- **Never fabricate a target.** Do not run `ve chunk create` or
  `ve subsystem create` to conjure a directory the reference could point at. Do
  not author GOAL.md or OVERVIEW.md prose so a name resolves. Do not pass
  `--force` to `ve external point`. Do not invent a repository name. Every target
  you write must come from the validator's `candidates` list or from a pointer
  that already exists in the workspace.
- **Never choose between candidates.** Two candidate trees means two plausible
  meanings, and picking one silently is exactly how the case-study repository
  nearly shipped a wrong customer-facing number. Escalate with both.

## Step 1: Run the validator

```bash
ve workspace validate --format json > /tmp/ve-workspace-validate.json
```

The JSON is the contract. Read these fields:

| Field | Use |
|-------|-----|
| `ok` | `true` means stop, you are done |
| `defects[]` | what to fix, each with `fix_class`, `path`, `line`, `location`, `reference`, `message`, `member` |
| `defects[].candidates[]` | trees that *do* hold the named artifact: `member`, `path`, `qualifier` |
| `unverified[]` | references the validator cannot check: `org/repo` targets it declines to resolve offline, and UNCHECKED symbol anchors (glob patterns, non-identifier anchors, directory targets) with a `reason` each. Report them; never "fix" them |
| `manifest_errors[]` | a member whose path is gone. These gate `ok`, so the loop cannot report clean while one stands |
| `unregistered_trees[]` | VE trees no member registers. A note, not a defect |
| `members[]` | the registered member names — the qualifiers you are allowed to write |
| `counts` | compare against the previous pass to detect progress |

A `candidate` whose `member` is `null` means the artifact lives in a tree nobody
registered: `ve workspace add` it before you can qualify anything against it.

On a large repository the report is long. Slice it instead of reading it whole:

```bash
# How big is the problem, and of what kinds?
jq '.counts' /tmp/ve-workspace-validate.json
jq -r '.defects[].fix_class' /tmp/ve-workspace-validate.json | sort | uniq -c

# One line per defect: class, where, and the reference as written
jq -r '.defects[] | "\(.fix_class)\t\(.location)\t\(.reference)"' /tmp/ve-workspace-validate.json

# One class in full, when you are working that batch
jq '[.defects[] | select(.fix_class == "misrouted-bare")]' /tmp/ve-workspace-validate.json

# The escalation shortlist: more than one candidate means you must not choose
jq -r '.defects[] | select(.candidates | length > 1) | .location' /tmp/ve-workspace-validate.json
```

The report also carries a coverage caveat worth passing on to the operator: a
backreference is scanned at any indentation, but it must be a comment on its own
line — a reference trailing after code on the same line is not seen.

## Step 2: Dispatch on the fix class

| `fix_class` | Condition | Action |
|-------------|-----------|--------|
| `misrouted-bare` | one candidate with a `member`, and it is the only reference in this tree naming that artifact | qualify in place |
| `misrouted-bare` | one candidate with a `member`, and two or more references in this tree name that artifact | create a peer pointer, leave the references bare |
| `misrouted-bare` | one candidate whose `member` is `null` | `ve workspace add`, then qualify |
| `misrouted-bare` | two or more candidates | **escalate** |
| `malformed-qualifier` | the legacy prefix names a registered member, or exactly one candidate names one | normalize to the `::` form |
| `malformed-qualifier` | the prefix names an unregistered tree that exists on disk | `ve workspace add`, then normalize |
| `malformed-qualifier` | neither | **escalate** |
| `unknown-qualifier` | the named tree exists on disk but is unregistered | `ve workspace add <name> <path>` |
| `unknown-qualifier` | exactly one candidate names a different member | retarget the qualifier, or the pointer's `tree:` |
| `unknown-qualifier` | no such tree anywhere, or two or more candidates | **escalate** |
| `missing-target` | exactly one candidate | requalify the reference, or retarget the pointer |
| `missing-target` | no candidate, two or more candidates, or the pointer cannot be read | **escalate** |
| `unresolvable-bare` | always | **escalate** |
| `unresolvable-frontmatter` | the named file exists at exactly one other path in the same tree | correct the `code_references` path |
| `unresolvable-frontmatter` | the symbol is gone, or the file is ambiguous | **escalate** |

Work the classes in report order, one class per batch (see Batching). Within a
batch, apply every edit to a file in one read-modify-write so intermediate states
never reach the validator.

### `misrouted-bare` — the silent failure

The reference resolves somewhere, just not in the tree that governs the file. It
is the case study's most damaging class: from one working directory it looks
fine, from another it lands in a real-but-wrong artifact.

**Qualify or point?** Both fixes are correct; they record different things.
Qualifying says "this one file reads that tree's artifact". A peer pointer says
"this tree depends on that artifact" and makes every bare reference to it in the
tree resolve. Count the defects in the same governing tree naming the same
artifact:

- **One** → qualify in place. Insert the candidate's `qualifier` immediately
  before `docs/`, changing nothing else on the line:

  ```
  # Subsystem: docs/subsystems/commitment_baseline
  # Subsystem: architecture::docs/subsystems/commitment_baseline
  ```

- **Two or more** → create the interest edge once, from the governing tree, and
  leave the references bare:

  ```bash
  ve external point architecture docs/subsystems/commitment_baseline \
    --why "realized savings are computed against this baseline" \
    --project-dir packages/libs/pybusiness
  ```

  Write a `--why` that names what this tree depends on; it is the note a future
  reader gets instead of guessing. Do **not** pass `--name`: the pointer's local
  directory name is what the bare references resolve against, so it must stay the
  artifact's own name.

**Does the pointer make the references redundant?** No. The pointer is the
resolution mechanism for the bare references, not a replacement for them —
creating a pointer and then deleting the references it serves would defeat the
fix you just applied. The two records mean different things: the pointer says
"this tree depends on that artifact" (an interest edge over the chunk's public
surface), while each per-symbol backreference says "this code is governed by
that intent" — and for a private helper, the backreference is usually the only
such record, because the chunk's own `code_references` name its public surface.
A reference that resolves through the pointer is correct and finished, not a
cleanup candidate. If a reference is broken, work its fix class; if the only
remaining move looks like deletion, escalate — see Invariants.

**Is the candidate the owner, or another reader?** A candidate tree counts as
holding the artifact even when what it holds is itself an `external.yaml`
pointer. Qualifying against such a tree resolves fine, but *pointing* at it
would create a pointer at a pointer, which does not resolve — the target has no
main document — and the next validation would report a fresh `missing-target`.
Before pointing, check what the candidate actually holds:

```bash
ls architecture/docs/subsystems/commitment_baseline
```

If it is an `external.yaml`, read the tree or repo it names and point there
instead — at the owner — or qualify and move on.

**Which tree would hold the pointer?** The one that governs the file — the
nearest ancestor directory containing `docs/trunk/`, never the working directory
and never the repository root:

```bash
d=$(dirname packages/libs/pybusiness/savings/realized.py)
while :; do [ -d "$d/docs/trunk" ] && echo "$d" && break; [ "$d" = "." ] && echo "(none)" && break; d=$(dirname "$d"); done
```

If the file has no governing tree — the defect message says so, and it is the
normal case for a package that consumes intent without owning any — **qualify**.
A pointer in a pointer-only or trunk-less package does not make bare references
beneath it resolve: such a tree is addressable but not governing. When such a
package reads several foreign artifacts, tell the operator that
`ve package scaffold <path> --interest '<member>::docs/...: <why>'` records those
dependencies as interest edges; that is a recommendation for the operator, not a
fix for these defects, and the references still need qualifying.

**Unregistered candidate tree.** When the single candidate's `member` is `null`,
the target tree is real but unaddressable. Register it under its directory name —
the convention `ve workspace init --scan` uses — then qualify against the name
you just registered, in the same batch:

```bash
ve workspace add platform packages/libs/platform
```

Register only trees a defect's candidate actually names. The other entries in
`unregistered_trees` get reported, not registered: a scan cannot tell an
intentional tree from a scaffolding template that happens to ship a `docs/`
tree, and that is the operator's call.

### `malformed-qualifier` — legacy prefix style

`architecture/docs/chunks/rsv2_pybusiness_model` reads like a qualified
reference, but `architecture/` is a path prefix rather than a qualifier, so the
reference addresses no tree at all. Every other `ve` command skips these
deliberately — reading the tail as a local id is exactly the misresolution the
`::` grammar exists to surface — so this validator is where they come to light.
Replace the `/` after the tree name with `::`:

```
# Chunk: architecture/docs/chunks/rsv2_pybusiness_model
# Chunk: architecture::docs/chunks/rsv2_pybusiness_model
```

The defect message's `Normalize it to '<member>::...'` is a template — `<member>`
is a placeholder, not an answer. Take the member from the legacy prefix itself
and confirm it appears in `members`; if it does not but the tree exists on disk,
`ve workspace add` it first; if the prefix matches no tree and exactly one
candidate names a member, use that; otherwise escalate.

### `unknown-qualifier` — the qualifier names no member

Either a reference says `<name>::docs/...` or a pointer says `tree: <name>`, and
`<name>` is not registered (or is registered at a path with no tree). Two
mechanical cases:

- The tree exists on disk → `ve workspace add <name> <path>`, registering it
  under the name **the reference already uses**, so no reference needs rewriting
  and every other reference to that tree starts resolving too. A single candidate
  with `member: null` is the evidence of where it lives; the defect message also
  lists the registered members, so you can see what is missing.
- Exactly one candidate names a different member → the qualifier is simply
  wrong; retarget it (for a pointer, rewrite `tree:`).

If the name matches nothing and no candidate is offered, escalate: a qualifier
naming a tree that does not exist is a question about history, not a typo you can
resolve.

### `missing-target` — the tree resolves, the artifact does not

A qualified reference or a pointer names a real tree that does not hold the
artifact. `candidates` is the whole triage:

- **Exactly one candidate** → the artifact moved. For a reference, requalify it.
  For a pointer, rewrite `tree:` (and `artifact_id:` if the id differs) in the
  existing `external.yaml`, keeping the `why:` note — the reason for the
  dependency is the part that is expensive to reconstruct. Do not delete and
  recreate the pointer; you would lose the note.
- **No candidate** → the artifact is gone from the whole workspace. Escalate.
- **The pointer cannot be read** → escalate with the parse error. A pointer
  nobody can read is a finding; guessing its intended contents is fabrication.

### `unresolvable-bare` — possibly born dangling

No tree in the workspace holds the named artifact under any name, so this
reference may never have resolved from anywhere — there was no deletion event for
an audit to catch. **Always escalate.** Three things make the escalation useful:

- Establish evidence of absence before asking. `ve exists <name>` answers
  "does this path or symbol exist anywhere I can see" across the whole
  workspace and states the scanned scope, so its summary line turns a pile of
  lost-or-moved judgment calls into one operator decision backed by fact.
  Same-name-elsewhere matches mean "moved" (a retarget question); zero matches
  mean the operator is deciding about genuinely absent code. Attach the
  summary to the escalation. If the operator then authorizes deleting the
  reference, that is tier 3 of the removal rule in Invariants:
  `ve deletion record` first, delete second, report under
  **Authorized deletions**.

- Check whether the workspace already points at an external repository that
  could own it (`ve chunk list --workspace --json` and
  `ve subsystem list --workspace --json` show pointer rows with their target,
  e.g. `[EXTERNAL: repo:acme/architecture]`). If a hub repository dominates,
  name it as the hypothesis: "if `run_rate_cloud_capital_split` lives in
  `acme/architecture`, the fix is a pointer at it — confirm and I will create
  it." That is a question, not a guess: you may not create the pointer until the
  operator confirms the target exists.
- Quote the reference and its `location` so the operator can read the code that
  claims to be governed by it. What it *meant* is recoverable from the code far
  more often than from the name.

Do not delete the reference. Do not create the artifact.

### `unresolvable-frontmatter` — a `code_references` entry rotted

A chunk's or subsystem's frontmatter points at a file or symbol that is gone.
Mechanical only when the file plainly moved: exactly one file with that basename
exists elsewhere in the same tree → update the path in the entry. A missing
symbol, an ambiguous basename, or a file that exists nowhere → escalate. Renames
are judgment calls, and a wrong `code_references` entry is worse than a stale
one because it looks current.

### `manifest_errors` — a member's path is gone

Not a defect, but it gates `ok`, so the loop cannot report clean while one
stands. If the tree is findable at exactly one other path, correct that member's
path in `.ve-workspace.yaml`. Otherwise escalate: removing the member would make
every qualified reference to it unresolvable, which trades one honest error for
many silent ones.

## Step 3: Re-run and loop

Re-run the validator after each pass and compare with the previous report:

```bash
ve workspace validate --format json > /tmp/ve-workspace-validate.next.json
jq -r '.counts.defects' /tmp/ve-workspace-validate.json /tmp/ve-workspace-validate.next.json
```

- `ok: true` → done.
- Defect count fell and mechanical work remains → next iteration.
- Every remaining defect is an escalation → stop and report.
- The defect set is unchanged after a pass that applied fixes → **no progress**;
  stop, and report which fixes did not take. The report is deterministic, so an
  identical set is real evidence, not noise.
- 10 iterations → stop and report what remains.

A fix that turns one defect into a different one is normal (registering a tree
turns an unaddressable candidate into a qualifiable one). A fix that *increases*
the defect count is not: stop, undo that batch, and report it.

## Batching

Apply and report one fix class at a time so each batch is reviewable on its own —
an operator can audit "all qualifications" separately from "all new pointers",
which is impossible once they are mixed.

Whether and when to commit is the operator's call — vibe engineering's commands
do not prescribe git operations (DEC-005). If this work is committed, make it
**one commit per fix class**, never a mixed one:

```
fix(refs): qualify 14 cross-tree references
fix(refs): record 3 peer interest edges for repeated cross-tree readers
fix(refs): normalize 9 legacy prefix-style qualifiers
fix(refs): retarget 2 pointers whose artifacts moved
chore(workspace): register 1 tree the manifest was missing
```

Never stage a fix you have not seen the validator accept, and never stage an
escalation as though it were resolved.

## Step 4: Report

```
## Workspace Validate-Fix Results

### Fixed
- misrouted-bare (4): qualified packages/libs/pybusiness/savings/realized.py:3
  as architecture::docs/subsystems/pricing_rules; created peer pointer
  pybusiness -> architecture::docs/subsystems/commitment_baseline (2 readers)
- malformed-qualifier (1): realized.py:4 -> architecture::docs/chunks/rsv2_pybusiness_model
- missing-target (1): retargeted docs/subsystems/rate_card/external.yaml to tree:viz
- registered 1 tree: platform -> packages/libs/platform

### Escalations (need your decision)
- backend-api-lib/client.py:1 — `# Subsystem: docs/subsystems/rounding`
  Two trees own an artifact with this name, and this file's package has no docs
  tree, so nothing decides which one it means:
    - pybusiness::docs/subsystems/rounding
    - architecture::docs/subsystems/rounding
  Which tree governs rounding for this consumer? I have changed nothing here.

### Authorized deletions (1)
- D001: `# Chunk: docs/chunks/run_rate_legacy` deleted from
  reports/run_rate.py:9 — authorized by the operator this session; evidence:
  `ve exists run_rate_legacy` found 0 matches across 4212 files. Grant
  recorded in packages/libs/pybusiness/docs/trunk/DELETIONS.md.

### Not verified (2)
- vendor/sdk.py:11 — `acme/architecture::docs/chunks/pricing` — cross-repository
  targets are not resolved offline.

### Unregistered trees (1)
- tools/cookiecutter-lib/package-template — holds a docs/trunk/. If it is a
  scaffolding template rather than a real tree, it is minting a namespace per
  generated package; `ve package scaffold` is the fix.

### Summary
- Iterations: 2
- Defects: 7 -> 1
- Escalations: 1
- Coverage caveat: a backreference is scanned at any indentation, but must be
  a comment on its own line.
```

State the numbers against the first pass, list every escalation with its
candidates, and never present an escalation as fixed. An authorized deletion is
its own section — never counted among fixes, because it removed information
rather than repairing it, and the section is where a reviewer finds the grant.
A report that claims a clean workspace when one reference is still ambiguous
recreates the exact silence this tooling exists to break.
