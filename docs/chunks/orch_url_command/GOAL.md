---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/orchestrator/daemon.py
- tests/test_orchestrator_cli.py
code_references:
- ref: src/orchestrator/daemon.py#get_daemon_url
  implements: "Helper function to read port file and construct HTTP URL"
- ref: src/ve.py#orch_url
  implements: "CLI command that prints orchestrator URL with --json support"
- ref: tests/test_orchestrator_cli.py#TestOrchUrl
  implements: "Test suite for URL command covering happy path, errors, and JSON output"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
created_after:
- chunknaming_drop_ticket
---

# Chunk Goal

## Minor Goal

Add a `ve orch url` command that prints the orchestrator's HTTP URL. This enables users to quickly get the base URL for the orchestrator API without having to look up the port number manually.

Example usage:
```bash
$ ve orch url
http://localhost:8080
```

## Success Criteria

1. `ve orch url` prints the orchestrator URL (e.g., `http://localhost:8080`)
2. Command reads the port from the same source as other `ve orch` commands
3. Returns error with helpful message if orchestrator is not running
4. Tests added for the new command

