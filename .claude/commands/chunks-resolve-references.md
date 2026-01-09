Update code references across all chunks and resolve or notify the operator about ambiguities. 

1. Identify all active chunks with `grep -l "status: ACTIVE" docs/chunks/*/GOAL.md`

2. In parallel sub-agents run `/chunk-update-references <path to goal>` for
   each of the directories containing active GOALs