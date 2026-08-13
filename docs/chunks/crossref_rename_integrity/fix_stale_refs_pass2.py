"""Second pass: re-point package-directory refs at their defining modules.

# Chunk: docs/chunks/crossref_rename_integrity - Backfill for the chunk→file check

Pass 1 (fix_stale_refs.py) mapped module→package splits to the package
directory when the symbol was not a class/def (endpoints decorated at module
level, ALL_CAPS constants). This pass resolves those symbols to the module
that defines them, matching class/def, decorated defs, and assignments.
Also catches directory-level refs pass 1's token regex could not see.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

PACKAGES = ["src/models", "src/orchestrator/api"]

DIR_MAPPINGS = {
    "commands": "skills",
    "src/templates/commands": "src/templates/plugin/skills",
}


def resolve_symbol(package_dir: pathlib.Path, symbol_path: str) -> str | None:
    head = symbol_path.split("::")[0]
    escaped = re.escape(head)
    pattern = re.compile(
        rf"^\s*(?:class|def|async def)\s+{escaped}\b|^{escaped}\s*[:=]"
    )
    for candidate in sorted(package_dir.glob("*.py")):
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


def main() -> int:
    fixed: list[str] = []
    unresolved: list[str] = []

    for goal in sorted((ROOT / "docs" / "chunks").glob("*/GOAL.md")):
        text = goal.read_text()
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        status = re.search(r"^status:\s*(\S+)", frontmatter, re.MULTILINE)
        if not status or status.group(1) not in ("ACTIVE", "COMPOSITE"):
            continue

        new_frontmatter = frontmatter

        for package in PACKAGES:
            for match in re.finditer(
                rf"ref:\s+({re.escape(package)})#([\w:.-]+)", new_frontmatter
            ):
                symbol = match.group(2)
                resolved = resolve_symbol(ROOT / package, symbol)
                if resolved:
                    new_frontmatter = new_frontmatter.replace(
                        f"ref: {package}#{symbol}", f"ref: {resolved}#{symbol}"
                    )
                    fixed.append(f"{goal.parent.name}: {package}#{symbol} -> {resolved}")
                else:
                    unresolved.append(f"{goal.parent.name}: {package}#{symbol}")

        for old_dir, new_dir in DIR_MAPPINGS.items():
            if not (ROOT / new_dir).exists() or (ROOT / old_dir).exists():
                continue
            new_frontmatter = re.sub(
                rf"^(\s*-\s+){re.escape(old_dir)}\s*$",
                rf"\g<1>{new_dir}",
                new_frontmatter,
                flags=re.MULTILINE,
            )

        if new_frontmatter != frontmatter:
            if not fixed or frontmatter.count("\n") == new_frontmatter.count("\n"):
                goal.write_text(parts[0] + "---" + new_frontmatter + "---" + parts[2])

    print(f"Re-pointed {len(fixed)} ref(s):")
    for line in fixed:
        print(f"  {line}")
    print(f"\nUnresolved symbols ({len(unresolved)}):")
    for line in unresolved:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
