---
status: ACTIVE
advances_trunk_goal: 'Required Properties: ''Maintaining the referential integrity
  of documents is an agent problem'', ''It must be possible to retrofit a legacy project
  into the workflow'', and ''Following the workflow must maintain the health of documents
  over time and should not grow more difficult over time.'''
proposed_chunks:
- prompt: 'Reify the pre-existing FUTURE chunk `backref_comment_forms`, which already
    owns this intent: the backreference comment grammar recognises each language''s own
    line-comment marker, mapped by file extension, rather than the literal `#` that
    `backreferences.py#_build_backref_pattern` emits today. Field measurement: `ve validate`
    reports `Chunk backrefs: 0` across 240 scanned files in a tree where `grep -c "// Chunk:"
    crates/` returns 1359. Added to that chunk by this narrative: the marker must be captured
    and re-emitted (the round-trip hazard — a parser that matches `//` and a writer that emits
    `#` inserts syntax errors into every file consolidation touches), `src/cluster_rename.py`
    carries a fifth, divergent copy of the grammar as the literal `"# Chunk: docs/chunks/"`
    and must consume the shared parser, and the chunk''s indentation half is already shipped
    by `backref_indented_comments` so its counts and framing on that point are corrected.'
  depends_on: []
  chunk_directory: backref_comment_forms
- prompt: 'A validator never reports success over claims it did not verify. `ve chunk
    validate` on a chunk with non-Python symbol anchors prints one `Symbol anchor ''...''
    in non-Python file ... is not checked` per reference and then prints "Chunk X is ready
    for completion" and exits 0 (measured; the field report hit 33 such warnings in one
    chunk). A `chunk-complete` pass read that green and shipped a corpus containing a
    `ref:` to a symbol deleted two chunks earlier; nine such live defects were found by
    a hand-written checker, and zero were visible to `ve`. Two changes, both language-independent:
    the success line states its own coverage rather than reporting an unqualified "ready
    for completion" when anchors were skipped, and `ve chunk validate` gains `--strict`,
    under which unchecked anchors exit nonzero. This is the seam with `crossref_unchecked_anchors`,
    whose criterion "UNCHECKED never gates" governs the default path and is preserved:
    `--strict` is opt-in, and the default exit code does not change. Second, `symbols.py#extract_symbols`
    returns a three-valued disposition — verified / contradicted / not-analysable — instead
    of a bare `set()`. Today an unsupported language is indistinguishable from "this file
    defines nothing", which is what makes the silence total; the three-valued contract is
    what makes an unsupported language degrade loudly to "not checked" and is the seam any
    later extractor plugs into. No new language support in this chunk.'
  depends_on: []
  chunk_directory: crossref_anchor_disposition
- prompt: 'The status gate on chunk→file validation sits on `code_paths`, not on `code_references`.
    `integrity.py#IntegrityValidator::_validate_chunk_file_paths` returns early for any
    status outside ACTIVE/COMPOSITE, before any path checking and before the unchecked-anchor
    counter, so FUTURE and IMPLEMENTING chunks are invisible to `ve validate` twice over.
    Measured with a probe chunk carrying `code_paths: [crates/does/not/exist.rs]` and
    `code_references: [crates/also/not/real.rs#Nope]`, changing nothing but `status:`:
    FUTURE and IMPLEMENTING both print "Validation passed"; ACTIVE reports both errors.
    The exemption is right for `code_paths` — the template calls those "files you expect
    to create" — and wrong for `code_references`, which the same template says are "populated
    after implementation", so a FUTURE chunk with a `ref:` pointing at nothing is not the
    expected-creation case; IMPLEMENTING is the status of the chunk someone is working on
    right now, which is when a path typo is cheapest to catch. Check `code_references` file
    parts for FUTURE, IMPLEMENTING, ACTIVE and COMPOSITE; keep the `code_paths` exemption
    for FUTURE and IMPLEMENTING. HISTORICAL and SUPERSEDED stay fully excluded from both
    and from symbol checking: a HISTORICAL chunk no longer owns intent (CHUNKS.md principle
    4), its references describe code as it was, and "fixing" them turns an archaeological
    record into a false claim about the present. Independently of the gate, the early return
    must stop suppressing `_symbol_anchors_unchecked`: a count whose job is to state what
    the validator is not seeing cannot itself omit whole chunks. Measured on this repository
    (400 ACTIVE / 39 HISTORICAL / 22 FUTURE): the gate change adds zero new errors and
    raises the unchecked-anchor count from 2275 to 2294.'
  depends_on: []
  chunk_directory: crossref_status_gate
- prompt: 'Symbol anchors are verified in the languages `SOURCE_EXTENSIONS` already claims
    to scan, via tree-sitter, filling the `not-analysable` half of the three-valued extraction
    contract with real answers. Language support is a table of grammars, and a language
    without a grammar still degrades to a stated "not checked" rather than to silence —
    extraction never becomes a second way to pass unverified. Four traps are known from
    a working Rust prototype that resolves 967 anchors with no false positives, and each
    needs a test: comments and string literals must not satisfy a check (a tree documenting
    its own renames — "this used to be `SEAM_HOVER_ZONE_PX`" — would otherwise satisfy the
    very check the rename broke, using the prose recording the breakage); `A::b` resolves
    against `A`''s body, not "both names appear in the file"; in `impl Trait for Type` the
    *self type* owns the method, and taking the first identifier after `impl` files real
    methods as defects; and a bare call at the top of a method body (`emit_chip(...)`) is
    not an enum variant — the false negatives are the expensive kind, and this one hid three
    real defects from the prototype''s author until it was fixed. The `::` nesting separator
    of the reference format maps onto each language''s own nesting, and where a language has
    no such notion the anchor is not-analysable rather than guessed at.'
  depends_on:
  - 1
  chunk_directory: crossref_treesitter_symbols
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

**Required Properties** — three of them, jointly:

- *"Maintaining the referential integrity of documents is an agent problem."* The
  validator is the instrument the agent uses to know whether integrity holds. When
  it reports success over claims it never examined, it does not merely fail to help
  — it converts an unknown into a false negative that an agent and a human then rely
  on.
- *"It must be possible to retrofit a legacy project into the workflow."* A legacy
  project is overwhelmingly likely not to be written in Python. Today, retrofitting
  a Rust, Go or TypeScript project yields a workflow whose reference checking is
  structurally inert while reporting itself green.
- *"Following the workflow must maintain the health of documents over time and should
  not grow more difficult over time."* Health that is reported rather than measured
  decays silently, and the cost of the eventual correction grows with the corpus.

## Driving Ambition

VE reports a clean corpus over references it never looked at. The three defects
below share one root: **the file *enumerator* was made language-agnostic and the
*parsers* that read what it enumerates were not.** `backref_language_agnostic`
generalized enumeration to ~20 languages; `symbolic_code_refs` and
`crossref_unchecked_anchors` left the grammar and the symbol table Python-only.
The seam runs exactly between them, and every symptom below is that seam.

The evidence is a field report from vibe-engineer 0.8.1 driving a ~30k-line Rust
repository with 115 chunks and 1068 `code_references`. Every claim in it reproduces
in this repository (measured, on a probe project under `ve init`):

| Defect | Measurement |
|---|---|
| Backreference comments invisible in curly-brace languages | `// Chunk:`, `-- Chunk:`, `; Chunk:`, `% Chunk:` all parse to `None`; a probe with one `//` backreference reports `Files scanned: 1`, `Chunk backrefs: 0`. Field: `Chunk backrefs: 0` over 240 files against 1359 real markers. |
| No symbol anchor outside Python is checked, by anything | `ve chunk validate` on an ACTIVE chunk referencing a genuinely absent `crates/lib.rs#State::totally_deleted_symbol` prints a warning, then "ready for completion", exit 0. |
| `ve validate` skips FUTURE and IMPLEMENTING chunks entirely | A probe with two dead paths: FUTURE → "Validation passed"; IMPLEMENTING → "Validation passed"; ACTIVE → 2 errors. Flipping only `status:` makes the same defects appear and disappear. |

The durable point, in the reporter's words: *a validator that reports success over
unverified claims is worse than one that reports nothing.* The cheapest fix for the
worst symptom is therefore not a parser at all — it is that VE stop claiming coverage
it does not have. That is why the honest-reporting work is a separate chunk from the
extraction work and does not depend on it.

Two scope decisions were taken by the operator against the report's open questions,
and are recorded here because the report deliberately left both open:

1. **Extraction is in scope, via tree-sitter** rather than per-language regex. The
   report offered a working ~200-line regex prototype as *prior art for the traps,
   not a design to adopt*; tree-sitter buys the four traps for free at the cost of a
   dependency and a grammar table.
2. **The status gate moves to `code_paths` only.** `code_references` are checked at
   FUTURE and IMPLEMENTING as well as ACTIVE and COMPOSITE.

A third decision was already on the books and is honored rather than revisited:
`backref_comment_forms` selects the comment marker **by file extension**, not by
alternation over all markers, and records its reasoning (`#` begins a preprocessor
directive in C and a shebang anywhere; `;` terminates statements in half the
enumerated languages). That costs threading the file's extension into the
single-line parser, and it is the more precise rule.

## Chunks

1. **Backreference comment markers follow the language** (`backref_comment_forms`,
   a pre-existing FUTURE chunk this narrative adopts and corrects). Map the marker
   by file extension, capture it so rewrites re-emit what they matched, and collapse
   `cluster_rename.py`'s duplicate copy of the grammar into the module that owns it.
   Blocked behind `validate_backref_literals`, which edits the same parser.

2. **Unchecked anchors are stated, and `--strict` gates on them.** `ve chunk
   validate` reports its own coverage instead of an unqualified success;
   `extract_symbols` returns verified / contradicted / not-analysable so an
   unsupported language degrades loudly rather than to silence. No new language
   support.

3. **The status gate sits on `code_paths`, not on `code_references`.** And the early
   return stops suppressing the unchecked-anchor count.

4. **Tree-sitter symbol extraction for the languages `SOURCE_EXTENSIONS` claims.**
   Depends on chunk 2's three-valued contract, which is the seam it plugs into.

## Completion Criteria

A user retrofitting VE onto a non-Python project gets reference checking that is
either *real* or *visibly absent*, and never silently absent:

- A backreference comment written in that language's line-comment syntax is scanned,
  counted, validated against the artifact it names, and survives a consolidation or
  cluster rename byte-correct in its own syntax.
- A `code_references` anchor into a supported language is verified against the actual
  symbol table; an anchor into an unsupported one is reported as unchecked, counted in
  a coverage number, and — under `--strict` — refuses to pass.
- No command in the suite prints an unqualified success over a check it skipped.
