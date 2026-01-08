Update code references across all chunks and resolve or notify the user about ambiguities. 

1. Identify all active chunks with `grep -l "status: ACTIVE" docs/chunks/*/GOAL.md`

2. And parallel sub-agents run `/chunk-update-references <path to goal>` for
   each of the identified active goals. 