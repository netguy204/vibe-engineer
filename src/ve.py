#!/usr/bin/env python3
"""Vibe Engineer CLI - Thin entry point.

This module serves as the entry point for the `ve` command.
The actual CLI implementation is modularized in the cli/ package.
"""
# Chunk: docs/chunks/cli_modularize - Thin entry point delegating to cli package

from cli import cli


def main():
    """Main entry point for the ve CLI."""
    cli()


if __name__ == "__main__":
    main()
