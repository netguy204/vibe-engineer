"""One-time fixup of stale code_paths/code_references in ACTIVE/COMPOSITE chunks.

# Chunk: docs/chunks/crossref_rename_integrity - Backfill for the chunk→file check

Run from the repo root. Applies deterministic rename mappings (commands/ →
skills/ plugin migration, module→package splits, retired numbered chunk prefix)
to chunk GOAL.md frontmatter only. Every rewrite requires the mapped target to
exist on disk; anything unmapped or unresolvable is left alone and reported so
the operator can triage deletions (scratchpad, sync, steward-skill tests, ...).
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

REGEX_MAPPINGS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^tests/test_plugin_commands\.py$"), "tests/test_plugin_skills.py"),
    (re.compile(r"^\.claude/commands/([\w-]+)\.md$"), r"skills/\1/SKILL.md"),
    (re.compile(r"^commands/([\w-]+)\.md$"), r"skills/\1/SKILL.md"),
    (
        re.compile(r"^src/templates/commands/([\w-]+)\.md\.jinja2$"),
        r"src/templates/plugin/skills/\1.md.jinja2",
    ),
    (
        re.compile(r"^src/templates/plugin/commands/([\w-]+)\.md\.jinja2$"),
        r"src/templates/plugin/skills/\1.md.jinja2",
    ),
    (re.compile(r"^src/templates/plugin/commands/?$"), "src/templates/plugin/skills"),
    (
        re.compile(r"^docs/chunks/0042-causal_ordering_migration/(.+)$"),
        r"docs/chunks/causal_ordering_migration/\1",
    ),
    (
        re.compile(r"^docs/reviewers/baseline/DECISION_LOG\.md$"),
        "docs/reviewers/baseline/decisions",
    ),
]

# Module → package splits: the path maps to the package directory, and symbol
# refs are re-pointed at the file inside the package that defines the symbol.
PACKAGE_SPLITS = {
    "src/models.py": "src/models",
    "src/orchestrator/api.py": "src/orchestrator/api",
}


def resolve_symbol(package_dir: pathlib.Path, symbol_path: str) -> str | None:
    """Find which module in a package defines the first symbol component."""
    head = symbol_path.split("::")[0]
    pattern = re.compile(rf"^\s*(?:class|def)\s+{re.escape(head)}\b")
    candidates = sorted(package_dir.glob("*.py"))
    # Prefer defining modules over __init__ re-exports.
    for candidate in candidates:
        if candidate.name == "__init__.py":
            continue
        if any(pattern.match(line) for line in candidate.read_text().splitlines()):
            return str(candidate.relative_to(ROOT))
    init = package_dir / "__init__.py"
    if init.exists() and any(
        pattern.match(line) for line in init.read_text().splitlines()
    ):
        return str(init.relative_to(ROOT))
    return None


def map_path(path: str, symbol: str | None) -> str | None:
    """Return the new path for a stale one, or None if unmapped/unverifiable."""
    if path in PACKAGE_SPLITS:
        package_dir = ROOT / PACKAGE_SPLITS[path]
        if symbol:
            resolved = resolve_symbol(package_dir, symbol)
            if resolved:
                return resolved
        return PACKAGE_SPLITS[path] if package_dir.exists() else None
    for pattern, replacement in REGEX_MAPPINGS:
        if pattern.match(path):
            new_path = pattern.sub(replacement, path)
            return new_path if (ROOT / new_path).exists() else None
    return None


# Matches a path token, optionally with a #symbol suffix, inside a frontmatter
# line. Path chars are conservative: no spaces, quotes, or YAML punctuation.
TOKEN = re.compile(r"(?P<path>[\w./-]+\.[\w-]+|[\w./-]+/)(?:#(?P<symbol>[\w:.-]+))?")


def status_of(frontmatter: str) -> str | None:
    match = re.search(r"^status:\s*(\S+)", frontmatter, re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    fixed: list[str] = []
    unfixed: set[str] = set()

    for goal in sorted((ROOT / "docs" / "chunks").glob("*/GOAL.md")):
        text = goal.read_text()
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        if status_of(frontmatter) not in ("ACTIVE", "COMPOSITE"):
            continue

        def replace(match: re.Match[str]) -> str:
            path, symbol = match.group("path"), match.group("symbol")
            normalized = path.rstrip("/")
            if (ROOT / normalized).exists():
                return match.group(0)
            new_path = map_path(normalized, symbol)
            if new_path is None:
                unfixed.add(f"{goal.parent.name}: {normalized}")
                return match.group(0)
            fixed.append(f"{goal.parent.name}: {normalized} -> {new_path}")
            # A symbol ref resolved into a package keeps its symbol suffix.
            return f"{new_path}#{symbol}" if symbol else new_path

        new_frontmatter = "\n".join(
            TOKEN.sub(replace, line)
            if re.match(r"\s*(-\s|- ref:|ref:)", line) or "ref:" in line
            else line
            for line in frontmatter.splitlines()
        )
        if new_frontmatter != frontmatter:
            goal.write_text(parts[0] + "---" + new_frontmatter + "\n---" + parts[2])

    print(f"Rewrote {len(fixed)} reference(s):")
    for line in fixed:
        print(f"  {line}")
    print(f"\nLeft {len(unfixed)} unmapped (operator triage):")
    for line in sorted(unfixed):
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
