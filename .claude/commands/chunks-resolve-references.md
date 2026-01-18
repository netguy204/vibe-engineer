---
description: Update code references across all chunks and resolve or notify the operator about ambiguities.
---



<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/chunks-resolve-references.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->


1. Identify all active chunks with `grep -l "status: ACTIVE" docs/chunks/*/GOAL.md`

2. In parallel sub-agents run `/chunk-update-references <path to goal>` for
   each of the directories containing active GOALs