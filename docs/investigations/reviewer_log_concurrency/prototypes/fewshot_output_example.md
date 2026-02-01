# Example output of: ve reviewer decisions --recent 5

## docs/reviewers/baseline/decisions/selective_artifact_friction_1.md

- **Decision**: APPROVE
- **Summary**: Implementation correctly adds --projects flag with task-aware friction logging across all entry points.
- **Operator review**: good

## docs/reviewers/baseline/decisions/orch_broadcast_invariant_1.md

- **Decision**: APPROVE
- **Summary**: All WebSocket broadcasts now fire correctly; invariant documented in class docstring.
- **Operator review**: good

## docs/reviewers/baseline/decisions/api_validation_refactor_1.md

- **Decision**: FEEDBACK
- **Summary**: Missing validation for edge case in batch endpoint.
- **Operator review**:
  - feedback: Should have been APPROVE - the edge case is handled by the middleware layer. Read the subsystem docs more carefully.

## docs/reviewers/baseline/decisions/template_escaping_1.md

- **Decision**: ESCALATE
- **Summary**: Unclear whether raw HTML should be escaped in markdown contexts.
- **Operator review**:
  - feedback: Good escalation - this was genuinely ambiguous and I needed to clarify the intent.

## docs/reviewers/baseline/decisions/chunk_naming_cleanup_2.md

- **Decision**: APPROVE
- **Summary**: Second iteration addressed all feedback; naming now consistent with conventions.
- **Operator review**:
  - feedback: Fine, but first iteration feedback was too picky about naming details.
