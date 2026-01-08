"""Chunks module - business logic for chunk management."""

import pathlib
import re

import jinja2

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
