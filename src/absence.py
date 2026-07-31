"""Evidence-of-absence: does this name exist anywhere I can see?

# Chunk: docs/chunks/crossref_absence_evidence - Workspace-wide existence query

This module answers one operator question about a name — a path, a symbol, or
a `file#symbol` reference fragment — across everything the current position
can legitimately see: the whole workspace when a `.ve-workspace.yaml` manifest
governs, otherwise the nearest enclosing VE tree, otherwise the directory
itself.

The point is *evidence*, in both directions:

- **Presence** distinguishes "still there" (a path match) from "moved" (the
  same final name at a different path). In field use that distinction turned
  18 lost-or-moved judgment calls into one operator decision backed by fact.
- **Absence** is a claim with a stated basis: the report always carries the
  scope that was scanned and the file counts, so "not found" is never
  silence.

Symbol presence deliberately reuses the conservative whole-word semantics of
``workspace_validation._symbol_is_absent``: a name counts as present when it
appears anywhere in a source file as a whole word. This query and the
validator must never disagree about what "present" means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from project import find_enclosing_tree
from source_files import enumerate_all_files, enumerate_source_files
from workspace import find_workspace_root, load_workspace


# Chunk: docs/chunks/crossref_absence_evidence - Query parsing (path, symbol, or both)
@dataclass(frozen=True)
class ExistenceQuery:
    """A parsed existence question: a path part, a symbol part, or both."""

    raw: str
    path_query: str | None
    symbol_query: str | None

    @classmethod
    def parse(cls, raw: str) -> "ExistenceQuery":
        """Parse a raw name into path and symbol questions.

        Mirrors the reference grammar already in use for `code_references`
        (`file#symbol::path`):

        - `a/b.py#Sym::method` asks about the path `a/b.py` *and* the symbol
          `method` (the last `::` component);
        - a name containing `/` (or a dot in its final component) is a path
          question;
        - a bare identifier asks about both a name on disk (files, artifact
          directories) and a symbol in source;
        - anything else is searched literally in source content.
        """
        text = raw.strip()
        if "#" in text:
            file_part, _, symbol_part = text.partition("#")
            symbol = symbol_part.split("::")[-1].strip()
            return cls(
                raw=raw,
                path_query=file_part.strip().strip("/") or None,
                symbol_query=symbol or None,
            )
        if "/" in text or "." in text.rsplit("/", 1)[-1]:
            return cls(raw=raw, path_query=text.strip("/") or None, symbol_query=None)
        return cls(raw=raw, path_query=text or None, symbol_query=text or None)


@dataclass(frozen=True)
class PathMatch:
    """A file or directory whose path answers the query."""

    path: str  # scope-root-relative POSIX path
    kind: str  # "file" | "directory"

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {"path": self.path, "kind": self.kind}


@dataclass(frozen=True)
class SymbolMatch:
    """A line in a source file where the queried name appears."""

    path: str  # scope-root-relative POSIX path
    line: int  # 1-indexed
    text: str  # the matching line, stripped

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {"path": self.path, "line": self.line, "text": self.text}


# Chunk: docs/chunks/crossref_absence_evidence - The visibility scope of a query
@dataclass(frozen=True)
class Scope:
    """What "anywhere I can see" means from a given starting directory."""

    kind: str  # "workspace" | "tree" | "directory"
    root: Path
    members: tuple[str, ...] = ()
    roots: tuple[Path, ...] = field(default=())

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {
            "kind": self.kind,
            "root": str(self.root),
            "members": list(self.members),
        }

    def describe(self) -> str:
        """One human-readable line naming the scope."""
        if self.kind == "workspace":
            names = ", ".join(self.members) or "(no members)"
            return f"workspace at {self.root} (members: {names})"
        if self.kind == "tree":
            return f"VE tree at {self.root}"
        return f"directory {self.root} (no workspace manifest or VE tree found)"


def resolve_scope(start: Path) -> Scope:
    """Resolve the visibility scope for a query starting at `start`.

    A workspace manifest found upward wins (the query sees the workspace root
    plus every registered member, matching the workspace validator's file
    enumeration); failing that, the nearest enclosing VE tree; failing that,
    the directory itself — the report says which, so absence claims always
    name their basis.
    """
    workspace_root = find_workspace_root(start)
    if workspace_root is not None:
        workspace = load_workspace(workspace_root)
        roots = [workspace.root, *(workspace.member_path(m) for m in workspace.members)]
        return Scope(
            kind="workspace",
            root=workspace.root.resolve(),
            members=tuple(m.name for m in workspace.members),
            roots=tuple(root for root in roots if root.is_dir()),
        )
    tree = find_enclosing_tree(start if start.is_dir() else start.parent)
    if tree is not None:
        resolved = tree.resolve()
        return Scope(kind="tree", root=resolved, roots=(resolved,))
    resolved = start.resolve()
    return Scope(kind="directory", root=resolved, roots=(resolved,))


# Chunk: docs/chunks/crossref_absence_evidence - The evidence a query returns
@dataclass(frozen=True)
class ExistenceReport:
    """Everything one existence query found — or the basis for its absence."""

    query: str
    scope: Scope
    path_matches: tuple[PathMatch, ...] = ()
    basename_matches: tuple[PathMatch, ...] = ()
    symbol_matches: tuple[SymbolMatch, ...] = ()
    files_scanned: int = 0
    source_files_scanned: int = 0

    @property
    def found(self) -> bool:
        """True when anything matched, in any class."""
        return bool(self.path_matches or self.basename_matches or self.symbol_matches)

    def to_dict(self) -> dict:
        """JSON-serializable form — the contract fix-loop skills consume."""
        return {
            "query": self.query,
            "found": self.found,
            "scope": self.scope.to_dict(),
            "path_matches": [m.to_dict() for m in self.path_matches],
            "basename_matches": [m.to_dict() for m in self.basename_matches],
            "symbol_matches": [m.to_dict() for m in self.symbol_matches],
            "counts": {
                "files_scanned": self.files_scanned,
                "source_files_scanned": self.source_files_scanned,
                "path_matches": len(self.path_matches),
                "basename_matches": len(self.basename_matches),
                "symbol_matches": len(self.symbol_matches),
            },
        }


def _relative(path: Path, root: Path) -> str:
    """Scope-root-relative POSIX path, absolute when outside the root."""
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _dedup_files(roots: tuple[Path, ...], enumerate) -> list[Path]:
    """Union of an enumeration over several roots, each file exactly once."""
    seen: set[Path] = set()
    for root in roots:
        for path in enumerate(root):
            seen.add(path.resolve())
    return sorted(seen)


def _symbol_pattern(symbol: str) -> re.Pattern:
    """Whole-word for identifiers (the validator's semantics), literal otherwise."""
    if symbol.isidentifier():
        return re.compile(rf"\b{re.escape(symbol)}\b")
    return re.compile(re.escape(symbol))


# Chunk: docs/chunks/crossref_absence_evidence - The search itself
def search_existence(scope: Scope, query: ExistenceQuery) -> ExistenceReport:
    """Search `scope` for `query` and return the full evidence report.

    Path questions see *every* file (and every directory that contains one —
    artifact directories are findable by name), not just source extensions:
    the field cases were `requirements.txt` and `Dockerfile`. Symbol
    questions scan source files with whole-word semantics.
    """
    all_files = _dedup_files(scope.roots, enumerate_all_files)
    rel_files = [_relative(path, scope.root) for path in all_files]

    path_matches: list[PathMatch] = []
    basename_matches: list[PathMatch] = []
    if query.path_query:
        needle = query.path_query
        needle_base = needle.rsplit("/", 1)[-1]

        # Directories are derived from file parents: an empty directory is
        # invisible to git as well, so this matches the enumeration's view.
        directories: set[str] = set()
        for rel in rel_files:
            parts = rel.split("/")[:-1]
            for depth in range(1, len(parts) + 1):
                directories.add("/".join(parts[:depth]))

        for rel in rel_files:
            if rel == needle or rel.endswith("/" + needle):
                path_matches.append(PathMatch(path=rel, kind="file"))
            elif rel.rsplit("/", 1)[-1] == needle_base:
                basename_matches.append(PathMatch(path=rel, kind="file"))
        for rel in sorted(directories):
            if rel == needle or rel.endswith("/" + needle):
                path_matches.append(PathMatch(path=rel, kind="directory"))
            elif rel.rsplit("/", 1)[-1] == needle_base:
                basename_matches.append(PathMatch(path=rel, kind="directory"))

    symbol_matches: list[SymbolMatch] = []
    source_files: list[Path] = []
    if query.symbol_query:
        source_files = _dedup_files(scope.roots, enumerate_source_files)
        pattern = _symbol_pattern(query.symbol_query)
        for path in source_files:
            try:
                content = path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if not pattern.search(content):
                continue
            rel = _relative(path, scope.root)
            for line_number, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    symbol_matches.append(
                        SymbolMatch(path=rel, line=line_number, text=line.strip())
                    )

    return ExistenceReport(
        query=query.raw,
        scope=scope,
        path_matches=tuple(path_matches),
        basename_matches=tuple(basename_matches),
        symbol_matches=tuple(symbol_matches),
        files_scanned=len(all_files),
        source_files_scanned=len(source_files),
    )


__all__ = [
    "ExistenceQuery",
    "ExistenceReport",
    "PathMatch",
    "Scope",
    "SymbolMatch",
    "resolve_scope",
    "search_existence",
]
