#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "jinja2",
#   "click",
# ]
# ///

import pathlib

import click
import jinja2

template_dir = pathlib.Path(__file__).parent.parent / "templates"

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

    def create_chunk(self, ticket_id: str, short_name: str):
        """instantiate the chunk templates for the given ticket and short name"""

        next_chunk_id = self.num_chunks + 1
        next_chunk_id_str = f"{next_chunk_id:04d}"
        chunk_path = self.chunk_dir / f"{next_chunk_id_str}-{short_name}-{ticket_id}"
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

@click.group()
def cli():
    """Vibe Engineer"""
    pass

@cli.command()
def init():
    """Initialize the Vibe Engineer document store."""
    pass

@cli.group()
def chunk():
    """Chunk commands"""
    pass

@chunk.command()
@click.argument("ticket_id")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def start(ticket_id, short_name, project_dir):
    """Start a new chunk."""
    chunks = Chunks(project_dir)
    chunks.create_chunk(ticket_id, short_name)


if __name__ == "__main__":
    cli()
