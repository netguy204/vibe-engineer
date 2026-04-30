"""Full-collapse demotion of cross-repo chunks to a single project.

# Chunk: docs/chunks/chunk_demote - Full-collapse demotion path for cross-repo chunks
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

This module handles demoting a chunk that lives in an architecture/external
repository (with external.yaml pointers in all participating projects) down
to a single project's docs/chunks/ directory in one atomic operation.

Complements task.demote (which does a lightweight single-project demotion
without frontmatter rewriting or full cascade pointer cleanup).
"""

import shutil
from pathlib import Path

import yaml

from frontmatter import extract_frontmatter_dict
from task.config import load_task_config, resolve_repo_directory, resolve_project_ref


class ChunkDemoteError(Exception):
    """Raised when chunk demotion cannot proceed."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_pointer_dir(chunk_dir: Path) -> bool:
    """Return True if chunk_dir is an external.yaml pointer (not a real chunk)."""
    return (chunk_dir / "external.yaml").exists() and not (chunk_dir / "GOAL.md").exists()


def _is_real_chunk_dir(chunk_dir: Path) -> bool:
    """Return True if chunk_dir contains actual chunk content (GOAL.md)."""
    return (chunk_dir / "GOAL.md").exists()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_chunk_scope(chunk_dir: Path, target_repo: str) -> list[str]:
    """Return offending code_paths that reference a repo other than target_repo.

    A code_path is offending if it contains '::' and the repo component before
    '::' does not match target_repo (regardless of org prefix).

    Args:
        chunk_dir: Path to the chunk directory containing GOAL.md.
        target_repo: Short repo name (e.g. 'dotter'), matched against the
                     repo component in any 'org/repo::' prefix.

    Returns:
        List of offending code_path strings (empty means all-clear).
    """
    fm = extract_frontmatter_dict(chunk_dir / "GOAL.md") or {}
    code_paths = fm.get("code_paths") or []

    offenders = []
    for path in code_paths:
        if "::" not in path:
            continue  # bare path — always OK
        prefix = path.split("::")[0]
        # prefix is "org/repo" — extract just the repo name
        repo_part = prefix.split("/")[-1] if "/" in prefix else prefix
        if repo_part != target_repo:
            offenders.append(path)

    return offenders


def strip_project_prefix(value: str, org_repo: str) -> str:
    """Strip 'org_repo::' prefix from value if present.

    Args:
        value: A code_path or code_reference ref string.
        org_repo: The full 'org/repo' string to strip (e.g. 'cloudcapitalco/dotter').

    Returns:
        Value with prefix stripped, or original value if prefix not present.
    """
    prefix = org_repo + "::"
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


def rewrite_chunk_frontmatter(file_path: Path, org_repo: str) -> None:
    """Rewrite frontmatter in-place: strip org_repo prefixes, remove dependents.

    Reads the file, parses frontmatter, applies transformations, writes back.
    Idempotent: re-running on already-rewritten frontmatter is a no-op.

    Transformations:
    - code_paths: strip 'org_repo::' prefix from each entry
    - code_references[].ref: strip 'org_repo::' prefix
    - dependents: remove key entirely

    Args:
        file_path: Path to the markdown file (GOAL.md or PLAN.md).
        org_repo: The full 'org/repo' string to strip from prefixes.
    """
    import re

    content = file_path.read_text()

    # Split into frontmatter and body
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        # No frontmatter — nothing to rewrite
        return

    fm_text = match.group(1)
    body = match.group(2)

    fm = yaml.safe_load(fm_text) or {}

    # Strip prefixes from code_paths
    if fm.get("code_paths"):
        fm["code_paths"] = [strip_project_prefix(p, org_repo) for p in fm["code_paths"]]

    # Strip prefixes from code_references[].ref
    if fm.get("code_references"):
        new_refs = []
        for cr in fm["code_references"]:
            if isinstance(cr, dict) and "ref" in cr:
                cr = dict(cr)
                cr["ref"] = strip_project_prefix(cr["ref"], org_repo)
            elif isinstance(cr, str):
                cr = strip_project_prefix(cr, org_repo)
            new_refs.append(cr)
        fm["code_references"] = new_refs

    # Remove dependents key entirely
    fm.pop("dependents", None)

    new_fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    file_path.write_text(f"---\n{new_fm_yaml}---\n{body}")


def demote_chunk(
    task_dir: Path,
    chunk_name: str,
    target_project_ref: str,
) -> dict:
    """Demote a cross-repo chunk to a single project, collapsing all bookkeeping.

    Full-collapse demotion sequence:
    1. Load task config, resolve architecture path and target project path.
    2. Validate architecture/docs/chunks/<name>/ exists (or detect already-removed).
    3. Validate target project has external.yaml (or detect already-copied).
    4. Check no other participating project has non-pointer chunk content.
    5. Validate scope: all code_paths must be bare or target-prefixed.
    6. Copy GOAL.md + PLAN.md to target project (skip if already done).
    7. Rewrite frontmatter in target (strip prefixes, remove dependents).
    8. Delete external.yaml pointer dirs in all non-target projects.
    9. shutil.rmtree the architecture source dir (skip if already gone).

    Returns:
        {
            "demoted_chunk": str,        # chunk name
            "target_project": str,       # org/repo of target
            "pointers_removed": int,     # count of non-target pointer dirs deleted
            "source_removed": bool,      # whether architecture source was removed
        }

    Raises:
        ChunkDemoteError: with a user-friendly message if any precondition fails.
    """
    task_dir = Path(task_dir)

    # -----------------------------------------------------------------------
    # Step 1: Load task config
    # -----------------------------------------------------------------------
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise ChunkDemoteError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # -----------------------------------------------------------------------
    # Step 1b: Resolve architecture repo path
    # -----------------------------------------------------------------------
    try:
        arch_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise ChunkDemoteError(
            f"Architecture repository '{config.external_artifact_repo}' not found."
        )

    # -----------------------------------------------------------------------
    # Step 1c: Resolve target project
    # -----------------------------------------------------------------------
    try:
        target_org_repo = resolve_project_ref(target_project_ref, config.projects)
    except ValueError as e:
        raise ChunkDemoteError(str(e))

    try:
        target_project_path = resolve_repo_directory(task_dir, target_org_repo)
    except FileNotFoundError:
        raise ChunkDemoteError(
            f"Target project '{target_org_repo}' not found or not accessible."
        )

    # -----------------------------------------------------------------------
    # Step 2: Determine architecture source state
    # -----------------------------------------------------------------------
    arch_chunk_dir = arch_path / "docs" / "chunks" / chunk_name
    arch_exists = arch_chunk_dir.exists()

    # -----------------------------------------------------------------------
    # Step 3: Determine target project's chunk state
    # -----------------------------------------------------------------------
    target_chunk_dir = target_project_path / "docs" / "chunks" / chunk_name
    target_has_content = _is_real_chunk_dir(target_chunk_dir)
    target_has_pointer = _is_pointer_dir(target_chunk_dir)

    # Decide where to read the dependents list from
    if arch_exists:
        # Normal case: read from architecture source
        arch_fm = extract_frontmatter_dict(arch_chunk_dir / "GOAL.md") or {}
        dependents = arch_fm.get("dependents") or []
    elif target_has_content:
        # Architecture already removed (idempotent re-run after full completion or
        # after step 9).  Use target's GOAL.md to check if already done.
        # We still need to enumerate participating projects for pointer cleanup.
        # Fall back to scanning all configured projects for external.yaml pointers.
        dependents = []
        arch_fm = {}
    else:
        raise ChunkDemoteError(
            f"Chunk '{chunk_name}' not found in architecture repository at "
            f"{arch_chunk_dir} and not present in target project '{target_org_repo}'."
        )

    # -----------------------------------------------------------------------
    # Step 4: Check no non-target participating project has real chunk content
    # -----------------------------------------------------------------------
    # Build the set of participating projects from dependents (if we have them)
    # plus a scan of all configured projects for extra safety.
    dep_repos = {d.get("repo") for d in dependents if isinstance(d, dict)}
    all_projects = set(config.projects)
    candidate_projects = dep_repos | all_projects

    for proj_ref in candidate_projects:
        if proj_ref == target_org_repo:
            continue
        try:
            proj_path = resolve_repo_directory(task_dir, proj_ref)
        except FileNotFoundError:
            continue

        proj_chunk_dir = proj_path / "docs" / "chunks" / chunk_name
        if not proj_chunk_dir.exists():
            continue

        if _is_real_chunk_dir(proj_chunk_dir):
            raise ChunkDemoteError(
                f"Project '{proj_ref}' has actual chunk content (GOAL.md) in "
                f"{proj_chunk_dir}, not just a pointer. "
                f"Cannot demote while another project owns the chunk."
            )

    # -----------------------------------------------------------------------
    # Step 5: Validate scope (only when arch source is available)
    # -----------------------------------------------------------------------
    if arch_exists:
        target_repo = target_org_repo.split("/")[-1]
        offenders = validate_chunk_scope(arch_chunk_dir, target_repo)
        if offenders:
            raise ChunkDemoteError(
                f"Cannot demote chunk '{chunk_name}' to '{target_org_repo}': "
                f"the following code_paths reference other repositories:\n"
                + "\n".join(f"  - {o}" for o in offenders)
            )

    # -----------------------------------------------------------------------
    # Step 6: Copy GOAL.md + PLAN.md to target project (idempotent)
    # -----------------------------------------------------------------------
    already_copied = target_has_content

    if not already_copied:
        if not arch_exists:
            raise ChunkDemoteError(
                f"Architecture source for chunk '{chunk_name}' is gone but "
                f"target project '{target_org_repo}' has neither content nor a pointer. "
                f"Cannot complete demotion."
            )
        # Remove external.yaml pointer if present
        target_pointer = target_chunk_dir / "external.yaml"
        if target_pointer.exists():
            target_pointer.unlink()

        # Ensure target directory exists
        target_chunk_dir.mkdir(parents=True, exist_ok=True)

        # Copy GOAL.md and PLAN.md
        for filename in ["GOAL.md", "PLAN.md"]:
            src_file = arch_chunk_dir / filename
            if src_file.exists():
                shutil.copy2(src_file, target_chunk_dir / filename)

    # -----------------------------------------------------------------------
    # Step 7: Rewrite frontmatter in target (idempotent)
    # -----------------------------------------------------------------------
    for filename in ["GOAL.md", "PLAN.md"]:
        dest_file = target_chunk_dir / filename
        if dest_file.exists():
            rewrite_chunk_frontmatter(dest_file, target_org_repo)

    # -----------------------------------------------------------------------
    # Step 8: Delete external.yaml pointer dirs in all non-target projects
    # -----------------------------------------------------------------------
    pointers_removed = 0

    # Collect all projects to scan for pointer cleanup
    scan_projects = candidate_projects - {target_org_repo}

    # Also scan all configured projects (in case dependents list was incomplete)
    scan_projects |= all_projects - {target_org_repo}

    for proj_ref in scan_projects:
        try:
            proj_path = resolve_repo_directory(task_dir, proj_ref)
        except FileNotFoundError:
            continue

        proj_chunk_dir = proj_path / "docs" / "chunks" / chunk_name
        if not proj_chunk_dir.exists():
            continue

        if _is_pointer_dir(proj_chunk_dir):
            shutil.rmtree(proj_chunk_dir)
            pointers_removed += 1

    # -----------------------------------------------------------------------
    # Step 9: Remove architecture source dir (idempotent)
    # -----------------------------------------------------------------------
    source_removed = False
    if arch_exists:
        shutil.rmtree(arch_chunk_dir)
        source_removed = True

    return {
        "demoted_chunk": chunk_name,
        "target_project": target_org_repo,
        "pointers_removed": pointers_removed,
        "source_removed": source_removed,
    }
