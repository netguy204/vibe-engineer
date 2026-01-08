"""Pydantic models for chunk validation."""

from pydantic import BaseModel


class CodeRange(BaseModel):
    """A range of lines in a file that implements a specific requirement."""

    lines: str  # "N-M" or "N" format
    implements: str


class CodeReference(BaseModel):
    """A file with code ranges that implement requirements."""

    file: str
    ranges: list[CodeRange]
