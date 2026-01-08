"""Chunks module - business logic for chunk management."""

import pathlib
import re

import jinja2
import yaml

template_dir = pathlib.Path(__file__).parent / "templates"


def render_template(template_name, **kwargs):
    template_path = template_dir / template_name
    with open(template_path, "r") as template_file:
        template = jinja2.Template(template_file.read())
        return template.render(**kwargs)


class Chunks:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.chunk_dir = project_dir / "docs" / "chunks"
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

    def enumerate_chunks(self):
        return [f.name for f in self.chunk_dir.iterdir() if f.is_dir()]

    @property
    def num_chunks(self):
        return len(self.enumerate_chunks())

    def find_duplicates(self, short_name: str, ticket_id: str | None) -> list[str]:
        """Find existing chunks with the same short_name and ticket_id."""
        if ticket_id:
            suffix = f"-{short_name}-{ticket_id}"
        else:
            suffix = f"-{short_name}"
        return [name for name in self.enumerate_chunks() if name.endswith(suffix)]

    def list_chunks(self) -> list[tuple[int, str]]:
        """List all chunks sorted by numeric prefix descending.

        Returns:
            List of (chunk_number, chunk_name) tuples, sorted by chunk_number
            descending. Returns empty list if no chunks exist.
        """
        chunks = []
        pattern = re.compile(r"^(\d{4})-")
        for name in self.enumerate_chunks():
            match = pattern.match(name)
            if match:
                chunk_number = int(match.group(1))
                chunks.append((chunk_number, name))
        chunks.sort(key=lambda x: x[0], reverse=True)
        return chunks

    def get_latest_chunk(self) -> str | None:
        """Return the highest-numbered chunk directory name.

        Returns:
            The chunk directory name if chunks exist, None otherwise.
        """
        chunks = self.list_chunks()
        if chunks:
            return chunks[0][1]
        return None

    def create_chunk(self, ticket_id: str | None, short_name: str):
        """Instantiate the chunk templates for the given ticket and short name."""
        next_chunk_id = self.num_chunks + 1
        next_chunk_id_str = f"{next_chunk_id:04d}"
        if ticket_id:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}-{ticket_id}"
        else:
            chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}"
        chunk_path.mkdir(parents=True, exist_ok=True)
        for chunk_template in template_dir.glob("chunk/*.md"):
            rendered_template = render_template(
                chunk_template.relative_to(template_dir),
                ticket_id=ticket_id,
                short_name=short_name,
                next_chunk_id=next_chunk_id_str,
            )
            with open(chunk_path / chunk_template.name, "w") as chunk_file:
                chunk_file.write(rendered_template)
        return chunk_path

    def resolve_chunk_id(self, chunk_id: str) -> str | None:
        """Resolve a chunk ID (4-digit or full name) to its directory name.

        Returns:
            The full chunk directory name, or None if not found.
        """
        chunks = self.enumerate_chunks()
        # Exact match
        if chunk_id in chunks:
            return chunk_id
        # Prefix match (e.g., "0003" matches "0003-feature")
        for name in chunks:
            if name.startswith(f"{chunk_id}-"):
                return name
        return None

    def get_chunk_goal_path(self, chunk_id: str) -> pathlib.Path | None:
        """Resolve chunk ID to GOAL.md path.

        Returns:
            Path to GOAL.md, or None if chunk not found.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            return None
        return self.chunk_dir / chunk_name / "GOAL.md"

    def parse_chunk_frontmatter(self, chunk_id: str) -> dict | None:
        """Parse YAML frontmatter from a chunk's GOAL.md.

        Returns:
            Dictionary of frontmatter fields, or None if chunk not found.
            Returns empty dict if frontmatter is malformed or missing.
        """
        goal_path = self.get_chunk_goal_path(chunk_id)
        if goal_path is None or not goal_path.exists():
            return None

        content = goal_path.read_text()
        # Extract frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}

        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if isinstance(frontmatter, dict) else {}
        except yaml.YAMLError:
            return {}

    def parse_code_references(self, refs: list) -> dict[str, tuple[int, int]]:
        """Parse code_references from frontmatter into file -> (earliest, latest) mapping.

        Expected format: [{file: "src/main.py", ranges: [{lines: "10-20", ...}]}]

        Returns:
            Dict mapping file paths to (earliest_line, latest_line) tuples.
        """
        result: dict[str, tuple[int, int]] = {}

        for ref in refs:
            if not isinstance(ref, dict) or "file" not in ref:
                continue

            file_path = ref["file"]
            ranges = ref.get("ranges", [])
            for r in ranges:
                lines = r.get("lines") if isinstance(r, dict) else None
                if lines:
                    # Parse "10-20" or "10" format
                    lines_str = str(lines)
                    if "-" in lines_str:
                        parts = lines_str.split("-")
                        start, end = int(parts[0]), int(parts[1])
                    else:
                        start = end = int(lines_str)

                    if file_path in result:
                        curr_earliest, curr_latest = result[file_path]
                        result[file_path] = (min(curr_earliest, start), max(curr_latest, end))
                    else:
                        result[file_path] = (start, end)

        return result

    def find_overlapping_chunks(self, chunk_id: str) -> list[str]:
        """Find ACTIVE chunks with lower IDs that have overlapping code references.

        Args:
            chunk_id: The chunk ID to check (4-digit or full name).

        Returns:
            List of affected chunk directory names.

        Raises:
            ValueError: If chunk_id doesn't exist.
        """
        chunk_name = self.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Parse target chunk
        frontmatter = self.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        code_refs = frontmatter.get("code_references", [])
        if not code_refs:
            return []

        # Parse target's references
        target_refs = self.parse_code_references(code_refs)
        if not target_refs:
            return []

        # Extract numeric ID of target chunk
        target_match = re.match(r'^(\d{4})-', chunk_name)
        if not target_match:
            return []
        target_num = int(target_match.group(1))

        # Find all ACTIVE chunks with lower IDs
        affected = []
        for name in self.enumerate_chunks():
            # Parse chunk number
            num_match = re.match(r'^(\d{4})-', name)
            if not num_match:
                continue
            chunk_num = int(num_match.group(1))

            # Only check chunks with lower IDs
            if chunk_num >= target_num:
                continue

            # Check if ACTIVE
            fm = self.parse_chunk_frontmatter(name)
            if fm is None or fm.get("status") != "ACTIVE":
                continue

            candidate_refs_raw = fm.get("code_references", [])
            if not candidate_refs_raw:
                continue

            candidate_refs = self.parse_code_references(candidate_refs_raw)

            # Check for overlap
            for file_path, (_, candidate_latest) in candidate_refs.items():
                if file_path in target_refs:
                    target_earliest, _ = target_refs[file_path]
                    # Overlap: target's earliest line <= candidate's latest line
                    if target_earliest <= candidate_latest:
                        affected.append(name)
                        break

        return sorted(affected)
