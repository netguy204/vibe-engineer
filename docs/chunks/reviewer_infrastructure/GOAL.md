---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - tests/test_models.py
  - docs/reviewers/baseline/METADATA.yaml
  - docs/reviewers/baseline/PROMPT.md
  - docs/reviewers/baseline/DECISION_LOG.md
code_references:
  - ref: src/models.py#TrustLevel
    implements: "Trust level enum for reviewer agent autonomy (observation/calibration/delegation/full)"
  - ref: src/models.py#LoopDetectionConfig
    implements: "Loop detection settings validation for reviewer escalation"
  - ref: src/models.py#ReviewerStats
    implements: "Review statistics tracking for trust calibration"
  - ref: src/models.py#ReviewerMetadata
    implements: "Pydantic schema for reviewer METADATA.yaml validation"
  - ref: tests/test_models.py#TestReviewerMetadata
    implements: "Unit tests for ReviewerMetadata schema validation"
  - ref: tests/test_models.py#TestLoopDetectionConfig
    implements: "Unit tests for loop detection config validation"
  - ref: tests/test_models.py#TestReviewerStats
    implements: "Unit tests for reviewer stats validation"
  - ref: tests/test_models.py#TestReviewerMetadataIntegration
    implements: "Integration test verifying baseline METADATA.yaml parses"
narrative: null
investigation: orchestrator_quality_assurance
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- explicit_deps_command_prompts
- chunk_list_flags
- progressive_disclosure_external
- progressive_disclosure_refactor
- progressive_disclosure_validate
---

# Chunk Goal

## Minor Goal

Create the `docs/reviewers/` directory structure with the baseline reviewer. This establishes the persistent reviewer entity model designed in the investigation, where reviewers are named entities with their own configuration, decision history, and emergent personality.

The baseline reviewer serves as the foundation from which domain-specific reviewers can be forked as usage patterns emerge.

## Success Criteria

1. **Directory structure exists**: `docs/reviewers/baseline/` contains METADATA.yaml, PROMPT.md, and DECISION_LOG.md

2. **METADATA.yaml schema validated**: Pydantic model for reviewer metadata exists in `src/models.py` with fields:
   - `name`: Reviewer identifier
   - `trust_level`: observation | calibration | delegation | full
   - `domain_scope`: List of glob patterns (empty = all)
   - `delegated_categories`: List of category strings
   - `loop_detection`: Object with max_iterations, escalation_threshold, same_issue_threshold
   - `forked_from`: Optional parent reviewer name
   - `stats`: Review statistics object

3. **Baseline content matches prototype**: Files copied from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/` with any necessary adjustments

4. **DECISION_LOG.md format documented**: Empty file with header comment explaining the expected entry format for decisions

5. **Tests verify schema**: Unit tests validate METADATA.yaml parsing and reject invalid configurations