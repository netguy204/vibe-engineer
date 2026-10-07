"""The deletion-grant ledger: operator-authorized reference deletions.

# Chunk: docs/chunks/crossref_absence_evidence - Recorded authorized-deletion disposition

The validate-fix skills' vocabulary says "never delete a reference" — a
reference is somebody's record that this code is governed by that intent, and
silently removing one destroys information no audit can recover. But
"reference to deliberately deleted code" is a real case, and before this
ledger existed there was no blessed way to record that an operator authorized
a deletion: the choice was between an unauditable deletion and a permanent
escalation.

This module adds the third disposition — neither fix nor silence. A grant is
recorded in `docs/trunk/DELETIONS.md` (created on first record) with the
reference as written, the location it was deleted from, who authorized it,
why, and optionally the absence evidence (typically a `ve exists` summary).
The record lands in the same diff that removes the reference, so a reviewer
sees the grant next to the deletion.

A grant is needed for removals that abandon a chunk's intent and for fix-loop
removals of references to code deleted outside the current diff. The author
of a diff that removes or moves code updates references whose intent survives
without a grant; the ledger header states the three tiers.

Nothing here performs git operations (DEC-005), and the validators do not
read the ledger — once the reference is gone there is nothing left to
validate. The ledger is the audit trail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LEDGER_FILENAME = "DELETIONS.md"

_LEDGER_HEADER = """\
# Deletion Grants

<!--
GUIDANCE FOR AGENTS — DO NOT REMOVE THIS COMMENT

This ledger records operator-authorized reference deletions. It is managed by
`ve deletion record`; do not append entries by hand.

A reference is somebody's record of governing intent. Removing one falls in
one of three tiers:

1. Ordinary edit, no entry here. The author of a diff that removes or moves
   code updates the references to that code in the same diff while the intent
   survives: retarget a reference to the code that now carries the intent,
   drop it if another reference already covers that intent, or drop it when
   the intent no longer belongs to any chunk. The PR reviewer checks it.
2. Operator sign-off plus an entry here. Removing the last reference that
   carries a chunk's intent abandons that intent, including when the same diff
   deletes the code that carried a chunk's whole intent.
3. Fix loops (validate-fix, workspace-validate-fix) reaching a reference to
   code deleted earlier, outside the current diff: an entry here once the
   operator authorizes the removal.

An entry is recorded BEFORE the reference is removed, so the removal and its
authorization land in the same diff and a reviewer can see the grant.

Each entry carries: the reference as written, the location it was deleted
from, who authorized it, why, and (when available) the absence evidence —
typically the summary line of `ve exists <name>`.
-->

## Grants
"""

_ENTRY_HEADING = re.compile(
    r"^### (?P<id>D\d+): (?P<date>\d{4}-\d{2}-\d{2}) — "
    r"`(?P<reference>.*?)` deleted from `(?P<location>.*?)`\s*$"
)
_FIELD = re.compile(r"^- \*\*(?P<name>[A-Za-z ]+)\*\*: (?P<value>.*)$")


class DeletionLedgerError(Exception):
    """Raised when the ledger cannot be used where asked."""


@dataclass(frozen=True)
class DeletionGrant:
    """One recorded operator-authorized deletion."""

    id: str
    date: str
    reference: str
    location: str
    authorized_by: str
    reason: str
    evidence: str | None = None

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {
            "id": self.id,
            "date": self.date,
            "reference": self.reference,
            "location": self.location,
            "authorized_by": self.authorized_by,
            "reason": self.reason,
            "evidence": self.evidence,
        }


# Chunk: docs/chunks/crossref_absence_evidence - Append-only grant ledger
class DeletionLedger:
    """The `docs/trunk/DELETIONS.md` ledger of one VE tree."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.trunk_dir = self.project_dir / "docs" / "trunk"
        self.path = self.trunk_dir / LEDGER_FILENAME

    def record(
        self,
        reference: str,
        location: str,
        authorized_by: str,
        reason: str,
        evidence: str | None = None,
        entry_date: str | None = None,
    ) -> str:
        """Append one grant, creating the ledger on first use.

        Args:
            reference: The reference as written (e.g. `docs/chunks/foo`).
            location: Where it was deleted from (e.g. `src/bar.py:12`).
            authorized_by: The operator who granted the deletion.
            reason: Why the deletion is correct.
            evidence: Optional absence evidence (e.g. a `ve exists` summary).
            entry_date: Optional ISO date; defaults to today.

        Returns:
            The new grant's id (e.g. "D001").

        Raises:
            DeletionLedgerError: If `project_dir` is not a VE tree.
        """
        if not self.trunk_dir.is_dir():
            raise DeletionLedgerError(
                f"No VE tree at {self.project_dir} (docs/trunk/ does not exist). "
                f"Record the grant in the tree that governed the deleted reference."
            )

        if not self.path.is_file():
            self.path.write_text(_LEDGER_HEADER)

        next_number = max(
            (int(grant.id[1:]) for grant in self.entries()), default=0
        ) + 1
        entry_id = f"D{next_number:03d}"
        entry_date = entry_date or date.today().isoformat()

        lines = [
            "",
            f"### {entry_id}: {entry_date} — `{reference}` deleted from `{location}`",
            "",
            f"- **Authorized by**: {authorized_by}",
            f"- **Reason**: {reason}",
        ]
        if evidence:
            lines.append(f"- **Evidence**: {evidence}")

        content = self.path.read_text().rstrip("\n")
        self.path.write_text(content + "\n" + "\n".join(lines) + "\n")
        return entry_id

    def entries(self) -> list[DeletionGrant]:
        """Parse every grant in the ledger, in file order."""
        if not self.path.is_file():
            return []

        grants: list[DeletionGrant] = []
        current: dict | None = None

        def finish():
            if current is not None:
                grants.append(
                    DeletionGrant(
                        id=current["id"],
                        date=current["date"],
                        reference=current["reference"],
                        location=current["location"],
                        authorized_by=current.get("Authorized by", ""),
                        reason=current.get("Reason", ""),
                        evidence=current.get("Evidence"),
                    )
                )

        for line in self.path.read_text().splitlines():
            heading = _ENTRY_HEADING.match(line)
            if heading:
                finish()
                current = dict(heading.groupdict())
                continue
            if current is not None:
                field = _FIELD.match(line)
                if field:
                    current[field.group("name")] = field.group("value")
        finish()
        return grants


__all__ = ["DeletionGrant", "DeletionLedger", "DeletionLedgerError", "LEDGER_FILENAME"]
