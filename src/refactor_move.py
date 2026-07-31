"""Evidence-backed reference rewriting for file moves: `ve refactor move`.

# Chunk: docs/chunks/crossref_refactor_move - Evidence-backed rename propagation

The operator declares one fact — "the code at `<old>` now lives at `<new>`" —
and this module propagates it into every chunk frontmatter reference
(`code_paths` entries, `code_references` file parts) and every subsystem
OVERVIEW `code_references` file part naming the old path. Field-tested
guards are baked in from day one:

- **Git evidence over inference.** Rename records (`git log --follow
  --name-status`) and the deletion sha of the old path (`--diff-filter=D`)
  are gathered once and attached to the report, so a reviewer can check the
  move against history instead of trusting name similarity.
- **The parent-directory guard.** Basename-based inference never accepts a
  candidate unless its immediate parent directory name matches the
  original's. (Documented near-miss: a unique basename match resolving
  `update-potential-savings/requirements.txt` to a *different* package's
  `requirements.txt`.)
- **`implements:` prose at every ambiguous decision point.** For
  module→package splits, an entry's prose out-performs name similarity;
  every AMBIGUOUS decision carries it so the operator decides with the best
  available signal.
- **NEVER_EXISTED is a distinct disposition.** A symbol with no successor
  anywhere in scope is a reconstruct-or-drop decision backed by an
  evidence-of-absence report — not a "renamed or removed" verdict that
  sends the fixer hunting for a rename that does not exist. (8 field refs
  named symbols that never existed in code.)

The tool never deletes a reference: AMBIGUOUS and NEVER_EXISTED entries are
left unchanged and reported for operator disposition (`ve deletion record`
is the blessed drop path).
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from absence import ExistenceQuery, Scope, resolve_scope, search_existence
from chunks import Chunks
from models import ChunkStatus
from subsystems import Subsystems
from symbols import extract_symbols


DISPOSITION_REWRITTEN = "REWRITTEN"
DISPOSITION_AMBIGUOUS = "AMBIGUOUS"
DISPOSITION_NEVER_EXISTED = "NEVER_EXISTED"

# Chunk statuses whose references are live addressing, not archaeology.
# HISTORICAL/SUPERSEDED chunks keep stale paths on purpose; rewriting them
# would falsify the record (mirrors IntegrityValidator's skip).
_REWRITABLE_CHUNK_STATUSES = {
    ChunkStatus.FUTURE,
    ChunkStatus.IMPLEMENTING,
    ChunkStatus.ACTIVE,
    ChunkStatus.COMPOSITE,
}


class RefactorMoveError(Exception):
    """A structural problem that prevents the move from being propagated."""


def _normalize(path: str) -> str:
    """Normalize a user-supplied or frontmatter path for comparison."""
    text = path.strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


# Chunk: docs/chunks/crossref_refactor_move - One frontmatter entry naming the old path
@dataclass(frozen=True)
class RefEntry:
    """A single frontmatter value that names the moved path."""

    artifact_file: Path  # absolute path to the GOAL.md / OVERVIEW.md
    artifact: str  # project-relative artifact id, e.g. docs/chunks/foo
    artifact_kind: str  # "chunk" | "subsystem"
    field_name: str  # "code_paths" | "code_references"
    raw: str  # the exact scalar value as it appears in frontmatter
    file_part: str  # normalized file part
    symbol_part: str | None
    implements: str | None


@dataclass(frozen=True)
class GitMoveEvidence:
    """What git history says about the declared move."""

    rename_records: tuple[tuple[str, str, str], ...] = ()  # (sha, src, dst)
    deletion_sha: str | None = None

    @property
    def detected(self) -> bool:
        """True when history corroborates the move in any form."""
        return bool(self.rename_records or self.deletion_sha)

    def summary(self) -> str:
        """One human-readable line describing the evidence basis."""
        parts: list[str] = []
        if self.rename_records:
            shas = sorted({sha[:12] for sha, _, _ in self.rename_records})
            parts.append(f"git rename detected in {', '.join(shas)}")
        if self.deletion_sha:
            parts.append(f"old path deleted in {self.deletion_sha[:12]}")
        if not parts:
            return "no git evidence; operator-asserted move"
        return "; ".join(parts)

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {
            "detected": self.detected,
            "rename_records": [
                {"sha": sha, "from": src, "to": dst}
                for sha, src, dst in self.rename_records
            ],
            "deletion_sha": self.deletion_sha,
        }


@dataclass(frozen=True)
class MoveDecision:
    """The disposition of one entry, with the evidence behind it."""

    entry: RefEntry
    disposition: str
    new_value: str | None = None
    evidence: tuple[str, ...] = ()
    candidates: tuple[str, ...] = ()
    absence_basis: dict | None = None

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {
            "artifact": self.entry.artifact,
            "artifact_kind": self.entry.artifact_kind,
            "field": self.entry.field_name,
            "value": self.entry.raw,
            "implements": self.entry.implements,
            "disposition": self.disposition,
            "new_value": self.new_value,
            "evidence": list(self.evidence),
            "candidates": list(self.candidates),
            "absence_basis": self.absence_basis,
        }


@dataclass
class MoveReport:
    """Everything one `ve refactor move` invocation decided, with evidence."""

    old: str
    new: str
    applied: bool
    git_evidence: GitMoveEvidence
    decisions: list[MoveDecision] = field(default_factory=list)

    def by_disposition(self, disposition: str) -> list[MoveDecision]:
        """Decisions with the given disposition."""
        return [d for d in self.decisions if d.disposition == disposition]

    def to_dict(self) -> dict:
        """JSON-serializable form — the contract fix-loop skills consume."""
        return {
            "old": self.old,
            "new": self.new,
            "applied": self.applied,
            "git_evidence": self.git_evidence.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "counts": {
                "rewritten": len(self.by_disposition(DISPOSITION_REWRITTEN)),
                "ambiguous": len(self.by_disposition(DISPOSITION_AMBIGUOUS)),
                "never_existed": len(
                    self.by_disposition(DISPOSITION_NEVER_EXISTED)
                ),
            },
        }


def _is_project_qualified(ref: str) -> bool:
    """True for org/repo::path refs — cross-repo addressing is out of scope."""
    hash_pos = ref.find("#")
    check = ref if hash_pos == -1 else ref[:hash_pos]
    return "::" in check


def _matches(file_part: str, old: str) -> bool:
    """Does a normalized file part name the old path (itself or beneath it)?"""
    return file_part == old or file_part.startswith(old + "/")


# Chunk: docs/chunks/crossref_refactor_move - Enumerate every reference naming the old path
def collect_references(project_dir: Path, old: str) -> list[RefEntry]:
    """Find every rewritable frontmatter entry naming `old`.

    Covers chunk GOAL.md `code_paths` and `code_references` (skipping
    HISTORICAL/SUPERSEDED archaeology) and subsystem OVERVIEW.md
    `code_references` (all statuses — the validators check them all).
    Project-qualified refs are skipped. Duplicate values within the same
    (file, field) are collected once, matching the rewriter's one-line-per-
    decision contract.
    """
    entries: list[RefEntry] = []
    seen: set[tuple[Path, str, str]] = set()

    def add(entry: RefEntry) -> None:
        key = (entry.artifact_file, entry.field_name, entry.raw)
        if key in seen:
            return
        seen.add(key)
        entries.append(entry)

    chunks = Chunks(project_dir)
    if chunks.chunk_dir.is_dir():
        for chunk_name in chunks.enumerate_chunks():
            frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
            if frontmatter is None:
                continue
            if frontmatter.status not in _REWRITABLE_CHUNK_STATUSES:
                continue
            goal_path = chunks.chunk_dir / chunk_name / "GOAL.md"
            artifact = f"docs/chunks/{chunk_name}"
            for path in frontmatter.code_paths or []:
                normalized = _normalize(path)
                if _matches(normalized, old):
                    add(
                        RefEntry(
                            artifact_file=goal_path,
                            artifact=artifact,
                            artifact_kind="chunk",
                            field_name="code_paths",
                            raw=path,
                            file_part=normalized,
                            symbol_part=None,
                            implements=None,
                        )
                    )
            for ref in frontmatter.code_references or []:
                entry = _reference_entry(goal_path, artifact, "chunk", ref, old)
                if entry is not None:
                    add(entry)

    subsystems = Subsystems(project_dir)
    if subsystems.subsystems_dir.is_dir():
        for subsystem_name in subsystems.enumerate_subsystems():
            frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_name)
            if frontmatter is None:
                continue
            overview_path = (
                subsystems.subsystems_dir / subsystem_name / "OVERVIEW.md"
            )
            artifact = f"docs/subsystems/{subsystem_name}"
            for ref in frontmatter.code_references or []:
                entry = _reference_entry(
                    overview_path, artifact, "subsystem", ref, old
                )
                if entry is not None:
                    add(entry)

    return entries


def _reference_entry(
    artifact_file: Path, artifact: str, kind: str, ref, old: str
) -> RefEntry | None:
    """Build a RefEntry from a SymbolicReference when it names `old`."""
    if _is_project_qualified(ref.ref):
        return None
    file_part, _, symbol_part = ref.ref.partition("#")
    normalized = _normalize(file_part)
    if not _matches(normalized, old):
        return None
    return RefEntry(
        artifact_file=artifact_file,
        artifact=artifact,
        artifact_kind=kind,
        field_name="code_references",
        raw=ref.ref,
        file_part=normalized,
        symbol_part=symbol_part or None,
        implements=ref.implements,
    )


def _run_git(project_dir: Path, args: list[str]) -> str:
    """Run a git command, returning stdout ('' on any failure)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


# Chunk: docs/chunks/crossref_refactor_move - Git history as reviewable move evidence
def gather_git_evidence(project_dir: Path, old: str, new: str) -> GitMoveEvidence:
    """Ask git history whether it corroborates the declared move.

    Rename records come from `git log --name-status` over the new path
    (`--follow` when it is a single file — git's rename tracing is
    per-file); the deletion sha of the old path comes from
    `git log --diff-filter=D`. Absent or non-git directories yield empty
    evidence, not an error: the report then says "operator-asserted".
    """
    rename_records: list[tuple[str, str, str]] = []

    log_args = ["log", "--name-status", "--format=%H"]
    if (project_dir / new).is_file():
        log_args.append("--follow")
    else:
        log_args.extend(["-n", "500"])
    output = _run_git(project_dir, [*log_args, "--", new])

    current_sha: str | None = None
    for line in output.splitlines():
        stripped = line.strip()
        if len(stripped) == 40 and all(c in "0123456789abcdef" for c in stripped):
            current_sha = stripped
            continue
        if not stripped.startswith("R"):
            continue
        parts = stripped.split("\t")
        if len(parts) != 3 or current_sha is None:
            continue
        _, src, dst = parts
        src_norm = _normalize(src)
        if _matches(src_norm, old):
            rename_records.append((current_sha, src_norm, _normalize(dst)))

    deletion_output = _run_git(
        project_dir,
        ["log", "--diff-filter=D", "--format=%H", "-n", "1", "--", old],
    )
    deletion_sha = deletion_output.strip().splitlines()[0].strip() if deletion_output.strip() else None

    return GitMoveEvidence(
        rename_records=tuple(rename_records), deletion_sha=deletion_sha
    )


def _defined_names(file_path: Path) -> set[str]:
    """All names a Python file defines, in `::`-path form.

    Extends AST function/class extraction with module-level and class-level
    assignment targets, so constants (e.g. VALID_STATUS_TRANSITIONS) resolve
    to their defining file rather than to every importer.
    """
    names = set(extract_symbols(file_path))
    if not str(file_path).endswith(".py") or not file_path.exists():
        return names
    try:
        tree = ast.parse(file_path.read_text())
    except (SyntaxError, UnicodeDecodeError, OSError):
        return names

    def walk(node: ast.AST, prefix: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        names.add("::".join([*prefix, target.id]))
            elif isinstance(child, ast.AnnAssign):
                if isinstance(child.target, ast.Name):
                    names.add("::".join([*prefix, child.target.id]))
            elif isinstance(child, ast.ClassDef):
                walk(child, [*prefix, child.name])

    walk(tree, [])
    return names


def _python_files_under(project_dir: Path, root_rel: str) -> list[Path]:
    """Python files under a project-relative directory, junk excluded."""
    root = project_dir / root_rel
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def find_symbol_definers(
    project_dir: Path, root_rel: str, symbol_path: str
) -> list[str]:
    """Project-relative Python files under `root_rel` that define the symbol."""
    definers: list[str] = []
    for path in _python_files_under(project_dir, root_rel):
        if symbol_path in _defined_names(path):
            definers.append(path.relative_to(project_dir).as_posix())
    return definers


def _whole_word_occurrences(
    project_dir: Path, root_rel: str, name: str
) -> list[str]:
    """Files under `root_rel` where `name` occurs as a whole word (weak signal)."""
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    hits: list[str] = []
    for path in _python_files_under(project_dir, root_rel):
        try:
            content = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(content):
            hits.append(path.relative_to(project_dir).as_posix())
    return hits


# Chunk: docs/chunks/crossref_refactor_move - The parent-directory guard on basename inference
def _guarded_basename_candidates(
    project_dir: Path, new: str, original_rel: str
) -> list[str]:
    """Candidates under `new` matching the original's basename AND parent dir.

    The guard is the point: a basename match alone once resolved
    `update-potential-savings/requirements.txt` to a different package's
    `requirements.txt`. The immediate parent directory name must also match.
    """
    original_parts = original_rel.split("/")
    basename = original_parts[-1]
    parent_name = original_parts[-2] if len(original_parts) >= 2 else None

    root = project_dir / new
    if not root.is_dir():
        return []
    candidates: list[str] = []
    for path in sorted(root.rglob(basename)):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if parent_name is not None and path.parent.name != parent_name:
            continue
        candidates.append(path.relative_to(project_dir).as_posix())
    return candidates


def _absence_basis(scope: Scope, name: str) -> tuple[dict, list[str]]:
    """Scope-wide evidence about a symbol name: (report dict, files seen in)."""
    query = ExistenceQuery(raw=name, path_query=None, symbol_query=name)
    report = search_existence(scope, query)
    files = sorted({m.path for m in report.symbol_matches})
    return report.to_dict(), files


def _path_absence_basis(scope: Scope, basename: str) -> tuple[dict, list[str]]:
    """Scope-wide *path* evidence about a file name: (report dict, matches).

    Symbol-less entries are path questions, not symbol questions: "does a
    file of this name exist anywhere I can see" must be answered with path
    matches, so a file that moved outside the declared destination surfaces
    as a candidate instead of being mislabeled never-existed.
    """
    query = ExistenceQuery(raw=basename, path_query=basename, symbol_query=None)
    report = search_existence(scope, query)
    matches = sorted(
        {m.path for m in (*report.path_matches, *report.basename_matches)}
    )
    return report.to_dict(), matches


def _compose_value(entry: RefEntry, new_file: str) -> str:
    """The rewritten scalar for an entry given its successor file part."""
    if entry.field_name == "code_references" and entry.symbol_part:
        return f"{new_file}#{entry.symbol_part}"
    return new_file


# Chunk: docs/chunks/crossref_refactor_move - Per-entry disposition with evidence
def resolve_entry(
    project_dir: Path,
    entry: RefEntry,
    old: str,
    new: str,
    git_evidence: GitMoveEvidence,
    scope: Scope,
) -> MoveDecision:
    """Decide one entry's disposition: rewrite, ambiguous, or never-existed.

    The escalation ladder: exact successor mapping → AST symbol verification
    → parent-dir-guarded basename inference → scope-wide absence evidence.
    Every step that fires leaves an evidence line; nothing is rewritten
    without one.
    """
    new_target = project_dir / new
    new_is_dir = new_target.is_dir()
    evidence: list[str] = [git_evidence.summary()]

    # --- Determine the successor file part -------------------------------
    successor: str | None = None
    if entry.file_part == old:
        if not new_is_dir:
            successor = new
            evidence.append(f"successor file {new} exists on disk")
        elif entry.symbol_part is None:
            # Module→package split (or dir→dir) with no symbol anchor: the
            # package directory itself is the successor — directories are
            # legitimate reference targets (crossref_workspace_parity).
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_REWRITTEN,
                new_value=_compose_value(entry, new),
                evidence=tuple(
                    [
                        *evidence,
                        f"successor {new}/ is a directory; directories are "
                        "valid reference targets",
                    ]
                ),
            )
        # new_is_dir with a symbol anchor: resolved below by symbol search.
    else:
        # Entry lies beneath old/: map the suffix under new/.
        rest = entry.file_part[len(old) + 1 :]
        mapped = f"{new}/{rest}"
        if (project_dir / mapped).exists():
            successor = mapped
            evidence.append(f"mapped {entry.file_part} -> {mapped} (exists on disk)")
        else:
            guarded = _guarded_basename_candidates(
                project_dir, new, entry.file_part
            )
            if len(guarded) == 1:
                successor = guarded[0]
                evidence.append(
                    f"basename inference accepted {guarded[0]}: basename and "
                    "immediate parent directory both match the original "
                    "(parent-dir guard)"
                )
            elif len(guarded) > 1:
                return MoveDecision(
                    entry=entry,
                    disposition=DISPOSITION_AMBIGUOUS,
                    evidence=tuple(
                        [
                            *evidence,
                            f"{mapped} does not exist; multiple parent-dir-"
                            "guarded basename candidates",
                        ]
                    ),
                    candidates=tuple(guarded),
                )
            # No guarded candidate: fall through to the symbol/absence ladder
            # (for symbol-less entries this becomes NEVER_EXISTED below).

    # --- Symbol resolution ------------------------------------------------
    if entry.symbol_part is None:
        if successor is not None:
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_REWRITTEN,
                new_value=_compose_value(entry, successor),
                evidence=tuple(evidence),
            )
        basename = entry.file_part.rsplit("/", 1)[-1]
        basis, path_candidates = _path_absence_basis(scope, basename)
        if path_candidates:
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_AMBIGUOUS,
                evidence=tuple(
                    [
                        *evidence,
                        f"no successor for {entry.file_part} under {new} "
                        "(mapped path missing, no parent-dir-guarded "
                        f"basename match), but '{basename}' exists elsewhere "
                        f"in scope ({len(path_candidates)} path match(es)) — "
                        "the file may have moved outside the declared "
                        "destination; operator decision",
                    ]
                ),
                candidates=tuple(path_candidates),
                absence_basis=basis,
            )
        return MoveDecision(
            entry=entry,
            disposition=DISPOSITION_NEVER_EXISTED,
            evidence=tuple(
                [
                    *evidence,
                    f"no successor for {entry.file_part} under {new} and no "
                    f"path named '{basename}' anywhere in "
                    f"{basis['scope']['kind']} scope — never-existed/"
                    "reconstruct-or-drop (record a drop with "
                    "`ve deletion record`)",
                ]
            ),
            absence_basis=basis,
        )

    symbol = entry.symbol_part
    leaf = symbol.rsplit("::", 1)[-1]

    if successor is not None:
        successor_path = project_dir / successor
        if successor.endswith(".py"):
            defined = _defined_names(successor_path)
            if symbol in defined:
                return MoveDecision(
                    entry=entry,
                    disposition=DISPOSITION_REWRITTEN,
                    new_value=_compose_value(entry, successor),
                    evidence=tuple(
                        [*evidence, f"symbol {symbol} defined in {successor} (AST)"]
                    ),
                )
            # Not an indexed definition — mirror check_reference_target's
            # honesty: whole-word presence keeps the ref (unverifiable),
            # total absence escalates.
            try:
                content = successor_path.read_text()
            except (OSError, UnicodeDecodeError):
                content = ""
            if re.search(rf"\b{re.escape(leaf)}\b", content):
                return MoveDecision(
                    entry=entry,
                    disposition=DISPOSITION_REWRITTEN,
                    new_value=_compose_value(entry, successor),
                    evidence=tuple(
                        [
                            *evidence,
                            f"symbol {symbol} present as text in {successor} "
                            "(not an indexed definition; kept, unverifiable)",
                        ]
                    ),
                )
            evidence.append(f"symbol {symbol} absent from successor {successor}")
        else:
            # Non-Python successor: symbol anchors are not AST-checkable.
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_REWRITTEN,
                new_value=_compose_value(entry, successor),
                evidence=tuple(
                    [
                        *evidence,
                        f"non-Python successor {successor}; symbol anchor "
                        "not AST-checkable (kept)",
                    ]
                ),
            )
    elif new_is_dir:
        # Module→package split: find the file under new that defines the
        # symbol. `implements:` prose out-performs name similarity here, so
        # ambiguity surfaces it rather than guessing.
        definers = find_symbol_definers(project_dir, new, symbol)
        if len(definers) == 1:
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_REWRITTEN,
                new_value=_compose_value(entry, definers[0]),
                evidence=tuple(
                    [
                        *evidence,
                        f"symbol {symbol} has exactly one definition under "
                        f"{new}/: {definers[0]} (AST)",
                    ]
                ),
            )
        if len(definers) > 1:
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_AMBIGUOUS,
                evidence=tuple(
                    [
                        *evidence,
                        f"symbol {symbol} defined in {len(definers)} files "
                        f"under {new}/",
                    ]
                ),
                candidates=tuple(definers),
            )
        weak = _whole_word_occurrences(project_dir, new, leaf)
        if weak:
            return MoveDecision(
                entry=entry,
                disposition=DISPOSITION_AMBIGUOUS,
                evidence=tuple(
                    [
                        *evidence,
                        f"symbol {symbol} has no definition under {new}/ but "
                        f"the name occurs in {len(weak)} file(s) (weak text "
                        "signal — not rewritten)",
                    ]
                ),
                candidates=tuple(weak),
            )
        evidence.append(f"symbol {symbol} not found under {new}/")

    # --- Scope-wide absence ladder ---------------------------------------
    basis, files_with_symbol = _absence_basis(scope, leaf)
    if files_with_symbol:
        return MoveDecision(
            entry=entry,
            disposition=DISPOSITION_AMBIGUOUS,
            evidence=tuple(
                [
                    *evidence,
                    f"name {leaf} occurs elsewhere in scope "
                    f"({len(files_with_symbol)} file(s)) — successor is not "
                    "under the declared destination; operator decision",
                ]
            ),
            candidates=tuple(files_with_symbol),
            absence_basis=basis,
        )
    return MoveDecision(
        entry=entry,
        disposition=DISPOSITION_NEVER_EXISTED,
        evidence=tuple(
            [
                *evidence,
                f"name {leaf} not found anywhere in {basis['scope']['kind']} "
                "scope — never-existed/reconstruct-or-drop, not a rename "
                "hunt (record a drop with `ve deletion record`)",
            ]
        ),
        absence_basis=basis,
    )


# Chunk: docs/chunks/crossref_refactor_move - Frontmatter-scoped, line-precise rewriting
def apply_rewrites(decisions: list[MoveDecision]) -> None:
    """Apply REWRITTEN decisions by editing frontmatter lines in place.

    Only the YAML frontmatter block is touched, and only lines whose scalar
    value is exactly the decision's old value (`- value` list items and
    `ref: value` mappings, quoted or not). A value that cannot be located
    raises rather than half-rewriting a drifted file silently.
    """
    by_file: dict[Path, list[MoveDecision]] = {}
    for decision in decisions:
        if decision.disposition != DISPOSITION_REWRITTEN:
            continue
        by_file.setdefault(decision.entry.artifact_file, []).append(decision)

    for artifact_file, file_decisions in by_file.items():
        content = artifact_file.read_text()
        lines = content.splitlines(keepends=True)
        end = _frontmatter_end(lines)
        if end is None:
            raise RefactorMoveError(
                f"{artifact_file}: no frontmatter block found"
            )
        consumed: set[int] = set()
        for decision in file_decisions:
            index = _find_value_line(
                lines, end, decision.entry, consumed
            )
            if index is None:
                raise RefactorMoveError(
                    f"{artifact_file}: could not locate frontmatter line for "
                    f"{decision.entry.field_name} value "
                    f"'{decision.entry.raw}'"
                )
            assert decision.new_value is not None
            lines[index] = lines[index].replace(
                decision.entry.raw, decision.new_value, 1
            )
            consumed.add(index)
        artifact_file.write_text("".join(lines))


def _frontmatter_end(lines: list[str]) -> int | None:
    """Index of the closing `---` line, or None when there is no block."""
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    return None


def _find_value_line(
    lines: list[str],
    frontmatter_end: int,
    entry: RefEntry,
    consumed: set[int],
) -> int | None:
    """Find the frontmatter line carrying the entry's exact scalar value."""
    raw = entry.raw
    if entry.field_name == "code_paths":
        accepted = {f"- {raw}", f"- '{raw}'", f'- "{raw}"'}
    else:
        accepted = {f"ref: {raw}", f"ref: '{raw}'", f'ref: "{raw}"'}
        # code_references list items may inline the mapping start.
        accepted |= {f"- ref: {raw}", f"- ref: '{raw}'", f'- ref: "{raw}"'}
    for index in range(1, frontmatter_end):
        if index in consumed:
            continue
        if lines[index].strip() in accepted:
            return index
    return None


# Chunk: docs/chunks/crossref_refactor_move - The move operation end to end
def execute_move(
    project_dir: Path, old: str, new: str, apply: bool = True
) -> MoveReport:
    """Propagate a declared move into every reference, with evidence.

    Refuses when the old path still exists (that is not a completed move —
    the field case where `src/ve.py` still holds code) or when the new path
    does not exist (nothing to verify successors against).
    """
    project_dir = Path(project_dir).resolve()
    old = _normalize(old)
    new = _normalize(new)
    if not old or not new:
        raise RefactorMoveError("old and new paths must be non-empty")
    if old == new:
        raise RefactorMoveError("old and new paths are identical")

    if (project_dir / old).exists():
        raise RefactorMoveError(
            f"'{old}' still exists on disk — this is not a completed move. "
            "Complete the move first (or, if code was split out while the "
            "file remains, fix those references individually)."
        )
    if not (project_dir / new).exists():
        raise RefactorMoveError(
            f"'{new}' does not exist on disk — successors cannot be verified"
        )

    git_evidence = gather_git_evidence(project_dir, old, new)
    entries = collect_references(project_dir, old)
    scope = resolve_scope(project_dir)

    decisions = [
        resolve_entry(project_dir, entry, old, new, git_evidence, scope)
        for entry in entries
    ]

    report = MoveReport(
        old=old,
        new=new,
        applied=apply,
        git_evidence=git_evidence,
        decisions=decisions,
    )
    if apply:
        apply_rewrites(report.by_disposition(DISPOSITION_REWRITTEN))
    return report


__all__ = [
    "DISPOSITION_AMBIGUOUS",
    "DISPOSITION_NEVER_EXISTED",
    "DISPOSITION_REWRITTEN",
    "GitMoveEvidence",
    "MoveDecision",
    "MoveReport",
    "RefEntry",
    "RefactorMoveError",
    "apply_rewrites",
    "collect_references",
    "execute_move",
    "find_symbol_definers",
    "gather_git_evidence",
    "resolve_entry",
]
