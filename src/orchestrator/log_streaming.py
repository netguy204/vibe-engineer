"""Log streaming utilities for orchestrator work units.

This module contains the log file management and streaming logic extracted from
the CLI layer to enable independent testing and reuse.
"""
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/cli_decompose - Extract log streaming from CLI

from pathlib import Path
from typing import Callable, Iterator

from orchestrator.models import WorkUnitPhase


# Phase order for log file iteration
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase between IMPLEMENT and REVIEW
PHASE_ORDER = [
    WorkUnitPhase.GOAL,
    WorkUnitPhase.PLAN,
    WorkUnitPhase.IMPLEMENT,
    WorkUnitPhase.REBASE,
    WorkUnitPhase.REVIEW,
    WorkUnitPhase.COMPLETE,
]


def get_phase_log_files(log_dir: Path) -> list[tuple[WorkUnitPhase, Path]]:
    """Get list of existing phase log files in order.

    Returns log files that exist in the log directory, ordered by the standard
    phase order (GOAL, PLAN, IMPLEMENT, REBASE, REVIEW, COMPLETE).

    Args:
        log_dir: Path to the log directory for a work unit

    Returns:
        List of (phase, log_file_path) tuples for existing log files
    """
    if not log_dir.exists():
        return []

    result = []
    for phase in PHASE_ORDER:
        log_file = log_dir / f"{phase.value.lower()}.txt"
        if log_file.exists():
            result.append((phase, log_file))
    return result


def stream_phase_log(
    log_file: Path,
    start_position: int = 0,
) -> Iterator[tuple[str, int]]:
    """Stream lines from a phase log file.

    Reads new content from the log file starting at the given position and
    yields each line along with the new file position.

    Args:
        log_file: Path to the log file to stream
        start_position: Byte position to start reading from (default: 0)

    Yields:
        Tuples of (line, new_position) where line includes the newline character
        and new_position is the byte offset after reading that line
    """
    try:
        with open(log_file) as f:
            f.seek(start_position)
            while True:
                line = f.readline()
                if not line:
                    break
                yield line, f.tell()
    except FileNotFoundError:
        return


def display_phase_log(
    phase: WorkUnitPhase,
    log_file: Path,
    show_header: bool = True,
    output: Callable[[str], None] = print,
) -> None:
    """Display a complete phase log file.

    Parses and formats log entries using the log_parser module, then outputs
    them using the provided output function.

    Args:
        phase: The phase of this log file
        log_file: Path to the log file to display
        show_header: Whether to show a phase header before entries
        output: Function to call with each output line (default: print)
    """
    from orchestrator.log_parser import (
        parse_log_file,
        format_entry,
        format_phase_header,
    )

    entries = parse_log_file(log_file)
    if not entries:
        return

    # Show phase header
    if show_header and entries:
        header = format_phase_header(phase.value, entries[0].timestamp)
        output(f"\n{header}\n")

    # Display entries
    for entry in entries:
        lines = format_entry(entry)
        for line in lines:
            output(line)
