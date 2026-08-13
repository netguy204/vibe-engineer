---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/AGENTS.md.jinja2
- tests/fixtures/agents_md_single_tree.md
- tests/test_template_system.py
code_references:
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: "The unconditional prior-art search directive, appended to the \"Read\
    \ GOAL.md first\" imperative rather than given its own heading. Scope is the whole\
    \ repository, not docs/, because a repository may hold several VE trees whose\
    \ findings live in member packages; a docs/-scoped grep returns a false empty,\
    \ which reads as \"no prior art exists\" and closes the question. \"Nouns\" is\
    \ plural because one key does not cover it \u2014 a proper noun and the domain\
    \ nouns reach different documents."
- ref: tests/fixtures/agents_md_single_tree.md
  implements: Byte-for-byte pin of the single-tree render, which is what proves the
    directive renders identically whether or not project.in_workspace is true.
- ref: tests/test_template_system.py#TestWorkspaceAwareAgentsTemplate
  implements: 'Golden-pin and workspace-render coverage for the claude AGENTS.md template.
    Holds no CLAUDE.md.jinja2 tests: that template was deleted with this chunk, so
    the former two-template lockstep pin has no subject.'
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- crossref_declaration_union
---
# Chunk Goal

## Minor Goal

The VE-managed block carries one **unconditional** instruction to search the
project's accumulated findings for the subject of the agent's own task, and it
scopes that search to the **whole repository**.

Every other read-directive in the managed block is reactive — gated on already
creating a chunk (`Before creating a chunk, read CHUNKS.md`), on having already
opened a file that carries a backreference (`When you see these, read the
referenced artifact`), or on already recognizing an artifact type (`When you
encounter these situations`). The block therefore teaches the *structure* of the
artifact tree without ever directing an agent to *query* it about its own
subject. This chunk owns the instruction that closes that gap, and the scope
decision that makes it work in a federated repository.

The directive attaches to the existing `Read GOAL.md first` imperative in the
Project Documentation section rather than occupying a heading of its own,
because the block is read top-to-bottom in one pass and a new H2 costs more
attention than the forward reference to `docs/subsystems/` does.

**Why the scope is the whole repository, not `docs/`.** A repository may hold
several VE trees, each with its own `docs/subsystems/` and
`docs/investigations/` inside a member package. A grep scoped to the root
`docs/` misses every finding held by a member tree and returns **empty** — and
an empty search is read as *"no prior art exists,"* which closes the question
and converts an unexamined subject into a settled one. That is a worse outcome
than giving no instruction at all, because it manufactures false confidence. The
same managed block already documents this repository shape in its
nearest-enclosing-tree worked example
(`packages/libs/pybusiness/docs/subsystems/...`), so a `docs/`-scoped grep would
contradict a worked example printed roughly eighty lines below it.

The named directories — `docs/subsystems/`, `docs/investigations/`, and code
comments — appear as **where findings live**, never as the search path. That
distinction is load-bearing: it is what lets one tree-neutral sentence serve the
federated reader, and it is why no workspace-conditional variant of this
directive exists.

## Success Criteria

- `src/templates/claude/CLAUDE.md.jinja2` carries the directive appended to the
  existing `Read GOAL.md first ...` line in the Project Documentation section,
  not as a new heading.
- The directive names a **verb and a search key**: grep, and the nouns the
  task names. A disposition ("consult prior art", "search the artifact tree")
  does not satisfy this criterion — see Rejected Ideas.
- The search scope is the whole repository. No form of the directive scopes it
  to `docs/`.
- The directive renders **identically** whether or not `project.in_workspace`
  is true; it adds no branch to the workspace conditional.
- `uv run ve init` re-renders `AGENTS.md` and `CLAUDE.md` from the template,
  and the rendered managed blocks carry the new text.
- `uv run ve validate` exits zero.

## Known Limit

This directive is **necessary but not sufficient**, and the rationale must not
claim otherwise. A repository can hold an artifact named precisely for the
subject under investigation whose content resolves to nothing — an
`external.yaml` whose cross-repository target was never committed. Such a
pointer is the single most on-target hit a correct grep returns, and it fails
*worse* than an empty result: an empty grep says "no prior art," while a
dangling artifact named for the exact subject says "someone already looked at
this and it went nowhere," which is more authoritative and closes the question
harder.

`ve validate` cannot close this by design: cross-repository (`repo:`) targets
are reported as *unverified* rather than checked, because resolving them needs
network or cache state, and per `docs/trunk/EXTERNAL.md` "a gate whose verdict
depends on a warm cache is not a gate." Peer (`tree:`) pointers *are* checked,
via the `missing-target` fix class. The unclosed case is therefore narrow and
specific: a `repo:` pointer that has never resolved since the day it was
written is indistinguishable from one that is merely unverified today. Closing
it is separate work with its own argument, not part of this chunk.

## Rejected Ideas

### Scope the search to `docs/` and the source

The directive was drafted as "grep `docs/` and the source for the nouns your
task names."

Rejected because: it returns **empty** on the exact class of document that
motivates the change. In a repository holding several VE trees, findings live
in member packages (`packages/<member>/docs/subsystems/...`), which a root
`docs/` grep never reaches. The false empty is the failure mode this chunk
exists to prevent, so a scope that produces one is not a weaker version of the
directive — it is the bug. Anyone tempted to re-narrow this scope should read
the Minor Goal before doing so.

### Add a workspace-conditional variant of the directive

Rejected because: it is unnecessary once the named directories are framed as
*where findings live* rather than as the search path. A tree-neutral sentence
already serves the federated reader. The workspace conditional in the template
is long, and a further subsection would bury the directive rather than sharpen
it.

### Give the directive its own "Before You Start" heading

Rejected because: a new H2 costs more reader attention than appending to the
imperative that already exists. Attaching to `Read GOAL.md first` places the
directive in the first section of the block, which is early enough.

### Key the search on one noun — "the subject of your task"

Rejected because: **"nouns" is plural and load-bearing.** Measured on the
repository that produced the motivating incident, one key does not cover it:

- The customer's proper noun appears **zero** times in the subsystem OVERVIEW
  that pre-stated the incident's structural conclusion — that document is about
  the domain and never names the customer. The proper noun reaches the code
  comment and the (dangling) investigation directory, and misses the document
  that would have helped.
- Domain nouns reach it instead — three distinct ones returned 12, 4, and 13
  hits — while a fourth plausible domain noun returned zero. So even a
  domain-noun search is not reliably one query.
- The customer's own name splits by spelling: closed form in 23 files,
  underscored in 4, spaced in 3, and the sets are **disjoint** — the
  investigation directory appears only under the underscored form, because
  every prose mention uses the closed form.

Anyone compressing this to "search for the subject of your task" reintroduces
the single-key assumption that the measurement refutes. Any future search tool
must normalize separators for the same reason.

### Include `docs/narratives/` in the list of places findings live

Rejected because: narratives decompose initiatives and rarely hold domain
findings. A fourth item turns an instruction to follow into a list to skim.

### Point the directive at a `ve` subcommand

Rejected because: no subject search exists. `ve exists` is a path/symbol
existence check, `ve chunk list` filters by status and recency only, and
`ve artifact` has no search subcommand. Naming a command that does not exist
would leave the agent to satisfy the directive by reopening the files it
already knows about. A dedicated docs-search command would be a better answer
than grep, and would remove the need to enumerate directories at all; if one is
built, this directive should be revised to invoke it.

### Rely on a skill or other mechanism to fire

Rejected because: in the incident that motivated this chunk, domain-adjacent
skills were present and loadable, and there were zero skill invocations across
42 turns. The plain grep does all the work here.

## Why This Is Not Obvious

Recorded because the change looks like a nicety and is not, and because the
reasons are not legible from the diff.

The agent in the motivating incident was **fluent** in the artifact system: it
created a well-formed chunk, wrote GOAL and PLAN, maintained its references,
and passed validation. Nothing about its artifact behavior looked wrong. It
also spent 42 turns and roughly $210 behaving, in its operator's words, "like
an engineer that doesn't understand the domain" — with roughly 40 touches of
its own chunk directory, 3 touches of the one subsystem OVERVIEW covering the
domain, and **zero** reads under `docs/trunk/` or `docs/investigations/`. It
measured a reference input reporting roughly 3x the true value, called it "not
decision-blocking" across five consecutive turns, and redesigned its statistic
to avoid the bad number rather than stopping. Its operator had to write by hand
on the pull request: *"The fact that we are over-reporting the optimized
coverage is a critical bug to fix, not work around."* The customer's exact
pathology was already recorded in a code comment naming a prior ticket, and the
subsystem OVERVIEW already pre-stated, in general terms, the structural
conclusion the agent spent five turns re-deriving.

An editor who reads the managed block asking *"does this teach the workflow"*
will correctly conclude that it does, and will see this directive as
redundant. The gap is visible only under a different question: **does anything
here tell an agent to look up its own subject?**