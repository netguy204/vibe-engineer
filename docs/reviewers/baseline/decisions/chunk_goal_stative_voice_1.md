---
decision: APPROVE
summary: "All success criteria satisfied — the Minor Goal placeholder now teaches stative, evergreen, intent-owning prose at the point of authorship with clear examples and ACTIVE status anchoring."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: The `## Minor Goal` placeholder in `src/templates/chunk/GOAL.md.jinja2` is rewritten so the prompts elicit stative voice; transitory phrasings removed.

- **Status**: satisfied
- **Evidence**: `git diff` confirms the old placeholder ("What does this chunk accomplish?", "Why is this the right next step?", "What does completing this enable?") is fully removed and replaced in `src/templates/chunk/GOAL.md.jinja2` lines 236–261.

### Criterion 2: The new placeholder explicitly directs the writer to describe the state of the architecture once the chunk owns its intent.

- **Status**: satisfied
- **Evidence**: "Write this as a present-tense architectural fact — the state of the system once this chunk is ACTIVE and fully owns its intent." (template line 237–239)

### Criterion 3: Write in present tense as if the chunk is already ACTIVE.

- **Status**: satisfied
- **Evidence**: "Write this as a present-tense architectural fact" plus the three-year evergreen framing: "If this chunk has been merged and is governing its code for the next three years, what is true about the architecture?" (template lines 241–242)

### Criterion 4: Avoid action verbs ("add", "wire", "make"); prefer state verbs ("emits", "enforces", "exposes", "tolerates").

- **Status**: satisfied
- **Evidence**: PREFER/AVOID lists present at template lines 244–250. PREFER includes "emits", "enforces", "exposes", "tolerates", "owns", "validates". AVOID includes "add", "wire", "make", "implement", "migrate", "fix".

### Criterion 5: Phrase the goal so it remains true years later if the chunk's intent continues to govern the code.

- **Status**: satisfied
- **Evidence**: "If this chunk has been merged and is governing its code for the next three years, what is true about the architecture?" directly instructs evergreen phrasing (template lines 241–242).

### Criterion 6: The placeholder includes at least one stative example alongside (or replacing) any implicit transitory example.

- **Status**: satisfied
- **Evidence**: Contrast block at template lines 252–257 shows ❌ transitory ("Wire progress() calls...") and ✅ stative rewrite ("The snapshot pipeline emits progress() events...").

### Criterion 7: The connection between "ACTIVE: Fully owns the intent" and the stative-voice requirement is made explicit at the point of authorship.

- **Status**: satisfied
- **Evidence**: The placeholder opens by quoting the STATUS VALUES definition inline: `("ACTIVE: Fully owns the intent that governs the code.")` (template lines 238–239), directly linking the schema concept to the writing instruction.

### Criterion 8: A fresh `ve chunk create <name>` (and `ve chunk create --future <name>`) produces a GOAL.md whose Minor Goal section guides the author toward stative phrasing.

- **Status**: satisfied
- **Evidence**: Test chunk was created and removed (no leftover in `docs/chunks/`). Git working tree is clean. Both `ve chunk create` paths use the same `src/templates/chunk/GOAL.md.jinja2` template, so both regular and `--future` creation are covered by the single template change.
