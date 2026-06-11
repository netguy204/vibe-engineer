# Implementation Plan

## Approach

Introduce a single module `src/cli/canonical_clone.py` that exports
`ensure_canonical_clone(name, *, config_path=None) -> pathlib.Path` plus a
small exception hierarchy. The helper is consumed from Python by the next
two chunks (`entity_worktree_attach`, `entity_claude_autoattach`); no new
CLI surface is added in this chunk.

The module sits beside `src/cli/config.py` because both belong to the
operator-config-driven entity flow that Wave 1 started; placing it under
`src/cli/` keeps the consuming imports short (`from cli.canonical_clone
import ensure_canonical_clone, ...`) and keeps the new entity-portability
layer cleanly separated from the legacy `entity_repo.py` (which still
governs the in-project submodule-based attach until chunk 3 replaces it).

The "are we cloned yet?" check is a fast filesystem probe: we treat
`<entities_dir>/<name>` as cloned if it's a directory containing a `.git`
entry (file or directory — covers both worktree-host repos and standalone
clones). When that check fails, we shell out to `git clone <url> <dest>`
and classify the resulting stderr into one of three distinguishable
exception subclasses.

We deliberately do NOT do a `git pull` on the second call. The helper's
contract is "ensure cloned, idempotently" — sync semantics belong to a
future `ve entity sync` command, not here. The next chunk
(`entity_worktree_attach`) explicitly relies on this: re-attaching to a
project must not surprise the user with a network fetch.

### Exception hierarchy

A single base class makes downstream callers' `except` blocks tidy while
still letting them distinguish the three failure modes when they want to:

- `CanonicalCloneError(Exception)` — base class. Carries `entity_name`
  and `clone_url` attributes so error formatting is consistent.
- `AuthFailure(CanonicalCloneError)` — git auth was rejected. Message
  mentions auth and points at `clone_url`.
- `MissingRemoteRepo(CanonicalCloneError)` — git host returned a
  "repository not found" error. Message names `entity_name` and the
  full `clone_url` so a typoed name is obvious.
- `NetworkFailure(CanonicalCloneError)` — DNS, connection refused, or
  timeout. Distinct so callers can suggest retry vs. fix-your-typo.

`ConfigError` from `cli.config` is intentionally NOT caught here — per
the Wave 1 handoff, it propagates up so the operator sees the same
config-loading message regardless of which command triggered the load.

### Classification of git's stderr

Git's exit code is always non-zero on failure, so classification works
off stderr substring matching. We keep the matcher narrow and explicit:

- Auth: stderr contains any of `Permission denied`, `authentication
  failed`, `could not read Username`, `fatal: Authentication failed`.
- Missing repo: stderr contains any of `Repository not found`, `does not
  exist`, `not found`, or HTTP `404`. (We check missing-repo BEFORE
  network because some hosts return both "not found" and a generic
  network-ish message; missing-repo is the more actionable diagnosis.)
- Network: stderr contains any of `Could not resolve host`, `Connection
  refused`, `Connection timed out`, `Network is unreachable`,
  `Operation timed out`, `unable to access`.
- Anything else falls through to a plain `CanonicalCloneError` with the
  raw stderr appended, so unexpected failures still surface clearly
  rather than getting misclassified.

The classification order matters: a host that's both unreachable AND
unauthenticated should report network failure first (no point telling
the user to fix auth they can't reach). The implemented order is
**auth, missing-repo, network, fallback** — we hit auth first because
auth failure stderr is the most distinctive (and git always reaches the
auth step before reporting missing-repo, so a real auth failure means
DNS + connect already succeeded).

### Partial-clone cleanup

`git clone` is mostly atomic — it creates the destination, populates it,
and either succeeds or leaves it empty/partial. To honor the success
criterion "a failed clone cleans up so the next invocation can retry
cleanly," we wrap the clone in a try/except: on failure, if
`<entities_dir>/<name>` exists, we `shutil.rmtree` it before re-raising
the classified exception. We only remove it if it didn't exist before
we tried to clone — never delete a directory the caller already had.

### `entities_dir` creation

Wave 1's handoff states `entities_dir` may not exist when the helper is
first called. Before the existence check, we `mkdir(parents=True,
exist_ok=True)` on `config.entities_dir`. This is cheap and idempotent.

## Subsystem Considerations

None. This is small, narrow, and doesn't touch any documented
architectural pattern.

## Sequence

### Step 1: Create `src/cli/canonical_clone.py` with the exception classes

Define `CanonicalCloneError`, `AuthFailure`, `MissingRemoteRepo`, and
`NetworkFailure`. Each carries `entity_name` and `clone_url` attributes
set in `__init__`. Include a `Chunk:` backreference comment at module
level.

### Step 2: Implement `ensure_canonical_clone`

Signature:

```python
def ensure_canonical_clone(
    name: str,
    *,
    config_path: pathlib.Path | None = None,
) -> pathlib.Path: ...
```

Flow:
1. Validate `name` is non-empty and contains no path separators or
   leading dots. Raise `ValueError` if invalid (this is a programmer
   error from the caller, not a `CanonicalCloneError`).
2. `cfg = load_config(config_path)` — let `ConfigError` propagate.
3. `cfg.entities_dir.mkdir(parents=True, exist_ok=True)`.
4. `dest = cfg.entities_dir / name`.
5. If `dest` exists AND `(dest / ".git").exists()` — return `dest`
   immediately (fast path, no git calls).
6. If `dest` exists but is not a git clone — raise
   `CanonicalCloneError` explaining the conflict (don't clobber). This
   is a corner case: a stray directory with the entity's name.
7. `clone_url = f"{cfg.git_base}/{name}.git"`.
8. Record `pre_existed = dest.exists()` (should be False at this point
   but defend against TOCTOU).
9. Run `git clone <clone_url> <dest>` via `subprocess.run(..., capture_output=True, text=True)`.
   - On returncode 0: return `dest`.
   - On returncode != 0:
     - If `dest.exists()` and not `pre_existed`: `shutil.rmtree(dest, ignore_errors=True)`.
     - Classify stderr and raise the appropriate subclass.

### Step 3: Helper `_classify_clone_error(stderr, name, clone_url)`

Pure function returning an instance of one of the four exception
classes. Keep the substring patterns as module-level tuples so tests
can sanity-check coverage. The function is exported (no underscore in
the eventual public surface? — keep the underscore; it's an internal
helper) so tests can hit it directly.

### Step 4: Tests in `tests/test_entity_canonical_clone.py`

Use a local bare git repo as the "remote" so the happy-path tests run
fully offline. For the failure modes we don't actually call git — we
unit-test `_classify_clone_error` with representative stderr samples.

Test cases:

1. **First-time clone**: create a bare repo `<tmp>/origin/foo.git`,
   write a config with `git_base = "<tmp>/origin"` and
   `entities_dir = "<tmp>/Entities"`. Call
   `ensure_canonical_clone("foo")`. Assert
   `<tmp>/Entities/foo/.git` exists and the returned path equals
   `<tmp>/Entities/foo`.
2. **Idempotent re-call**: after step 1, monkeypatch
   `subprocess.run` to raise if called, then call
   `ensure_canonical_clone("foo")` again. Assert it returns the same
   path without invoking subprocess.
3. **`entities_dir` auto-created**: point `entities_dir` at a
   nonexistent subdirectory, run the helper, assert the directory was
   created.
4. **Auth failure classification**: feed
   `_classify_clone_error` a representative SSH auth-denied stderr,
   assert `AuthFailure` instance with `clone_url` and `entity_name`
   populated and message mentions auth.
5. **Missing-repo classification**: feed it a "Repository not found"
   stderr; assert `MissingRemoteRepo`, message contains the entity
   name and the full URL.
6. **Network failure classification**: feed it
   "Could not resolve host" stderr; assert `NetworkFailure`.
7. **Fallback classification**: feed unrecognized stderr; assert
   plain `CanonicalCloneError` (not a subclass) and the message
   includes the raw stderr.
8. **Partial-clone cleanup on failure**: point `git_base` at a
   nonexistent local path so `git clone` actually fails. Assert
   `<entities_dir>/<name>` does NOT exist after the failure. (Use a
   real subprocess invocation so we exercise the cleanup path
   end-to-end.)
9. **Refuses to clobber existing non-git directory**: pre-create
   `<entities_dir>/<name>` as an empty plain directory. Call the
   helper, assert `CanonicalCloneError` is raised and the directory is
   left in place.
10. **Invalid entity name rejected**: pass `name="../escape"`, assert
    `ValueError` before any config load.
11. **`ConfigError` propagates unwrapped**: point at a missing config
    file path, call the helper, assert `ConfigError` is raised (NOT
    `CanonicalCloneError`).

All tests use `tmp_path` and explicit `config_path` — none touch the
operator's real `~/.ve-config.toml`.

### Step 5: Update GOAL.md frontmatter

Wave 1 handoff item #3 doesn't apply (this chunk doesn't list
`src/cli/main.py`), but the predicted `code_paths` listed
`src/entity/canonical_clone.py` which doesn't match the actual layout.
Fix code_paths to:

```yaml
code_paths:
  - src/cli/canonical_clone.py
  - tests/test_entity_canonical_clone.py
```

This happens during `/chunk-complete` automatically when populating
`code_references`; setting `code_paths` here is a planning courtesy.

## Dependencies

- `entity_config_toml` (chunk 0 of the narrative) — ACTIVE. Provides
  `load_config`, `ConfigError`, `VeConfig` from `cli.config`.

## Risks and Open Questions

- **Git stderr text varies by git version and locale.** Our matcher
  uses substrings observed across common git versions (2.30+) and
  English locale. A user running a non-English locale might see the
  fallback classification instead of a specific subclass. That's a
  graceful degradation — they still see git's raw stderr — but worth
  noting. We don't attempt locale-forcing here; that's a future
  refinement if it ever shows up in user reports.
- **TOCTOU on the dest existence check.** Between the `dest.exists()`
  probe and the `git clone` call, another process could create the
  directory. We accept this — entity work is single-operator;
  concurrent attach is out of scope.
- **No timeout on git clone.** A hanging clone would block the helper
  indefinitely. We accept this: `ve entity claude` is interactive, the
  user can Ctrl-C. Adding a timeout would surprise users on slow
  networks with legitimately large entity repos.

## Deviations

(Populated during implementation if reality diverges.)
