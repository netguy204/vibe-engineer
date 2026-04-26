---
discovered_by: claude
discovered_at: 2026-04-26T01:56:42Z
severity: low
status: open
resolved_by: null
artifacts:
  - docs/chunks/invite_token_instant_expiry/GOAL.md
---

## Claim

`docs/chunks/invite_token_instant_expiry/GOAL.md` is ACTIVE and lists four success criteria:

- "`ve board invite create` followed by `curl <invite_url>` returns the instruction page (not 'Invalid or expired')"
- "Root cause identified and documented in the chunk"
- "End-to-end test added covering the create → fetch cycle"
- "Existing tests still pass"

The body of the goal still reads as an investigation in flight: a "Likely causes to investigate:" bullet list and a "The fix should include an end-to-end test" sentence. No success criterion is paired with `code_references` — that field is `[]`.

## Reality

The implementing code has shipped. `workers/leader-board/src/gateway-crypto.ts` carries `# Chunk: docs/chunks/invite_token_instant_expiry` backreferences on `hashToken()` (raw-byte SHA-256) and `deriveTokenKey()` (HKDF-SHA256, info `leader-board-invite-token`). `workers/leader-board/test/gateway-crypto.test.ts` and `workers/leader-board/test/invite-page.test.ts` carry matching backreferences for the cross-language vectors and end-to-end coverage.

So the criteria are satisfied in code, but:

1. The GOAL.md never names the actual root cause — the prose is still framed as "likely causes" rather than the cause that was found and fixed (raw-byte vs hex-string token hashing; HKDF symmetric-key derivation matching Python `derive_token_key`).
2. `code_references: []` does not anchor the criterion "Root cause identified and documented in the chunk" to any code sites, even though the implementing functions now carry backreferences pointing back at this chunk.

After filtering generic criteria ("Existing tests still pass"), three substantive criteria remain against zero `code_references` — a meaningful exceedance per the audit's over-claim heuristic.

## Workaround

None applied this audit pass — veto rule fired (over-claim suppresses tense rewrite).

## Fix paths

1. Populate `code_references` with the shipped sites (`gateway-crypto.ts#hashToken`, `gateway-crypto.ts#deriveTokenKey`, the cross-language test vectors in `gateway-crypto.test.ts`, and the end-to-end test in `invite-page.test.ts`) and rewrite the Minor Goal body to state the identified root cause in present tense rather than "likely causes to investigate."
2. If the chunk is judged to no longer own enduring intent (the protocol contract is now anchored by the backreferenced functions on their own), historicalize via Pattern A — but `bug_type: semantic` argues against this.
