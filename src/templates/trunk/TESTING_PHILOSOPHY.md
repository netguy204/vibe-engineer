# Testing Philosophy

<!--
This document establishes how we think about verification in this project.
It informs every chunk's testing strategy but doesn't prescribe specific tests.

The goal is to answer: "Given a piece of functionality, how should we
approach testing it?" This creates consistency across chunks and helps
agents understand what kind of tests to write.
-->

## Testing Principles

<!--
What beliefs guide your testing approach? These should be specific enough
to resolve debates about whether a given test is worth writing.

Examples:
- "Test behavior, not implementation. Tests should pass if the contract
  is satisfied, regardless of how it's satisfied."
- "Prefer integration tests over unit tests when the interesting behavior
  involves multiple components interacting."
- "Every bug that reaches production should result in a test that would
  have caught it."
-->

## Test Categories

<!--
Define the categories of tests you use and what each is responsible for.
This creates shared vocabulary for chunk TESTS.md documents.
-->

### Unit Tests

<!--
What do unit tests cover in this project?
What's the boundary of a "unit"?
How do you handle dependencies—mocking, faking, or real implementations?

Example:
Unit tests verify individual functions and structs in isolation.
Dependencies on I/O are injected as traits and faked in tests.
Unit tests must run without filesystem or network access.
-->

### Integration Tests

<!--
What do integration tests cover?
What components are allowed to be "real" vs simulated?

Example:
Integration tests verify interactions between components.
Filesystem access is real (using temp directories).
Time may be simulated to test expiration logic.
-->

### System Tests

<!--
End-to-end tests that exercise the system as a user would.
What environment do they require?
How are they isolated from each other?
-->

### Property Tests

<!--
If you use property-based testing (fuzzing, QuickCheck-style):
What properties are amenable to this approach?
How do you balance coverage vs execution time?
-->

### Performance Tests

<!--
How do you verify performance requirements from SPEC.md?
Are these run in CI or manually?
What hardware/environment assumptions do they make?
-->

## Hard-to-Test Properties

<!--
Some properties are difficult to test automatically. Document your approach
for each. Common examples:

- Durability/crash safety: How do you test that data survives crashes?
- Concurrency: How do you test for race conditions?
- Resource limits: How do you test behavior at boundaries (disk full, etc.)?
- Performance degradation: How do you catch performance regressions?
-->

## What We Don't Test

<!--
Explicitly list what's out of scope for automated testing and why.

Example:
- Actual hardware failure (disk corruption): Tested manually during
  initial development, not practical to automate
- Multi-machine scenarios: Out of scope for this single-node implementation
-->

## Test Organization

<!--
Where do tests live? How are they named? How do they map to source files?

Example:
- Unit tests: Same file as implementation, in #[cfg(test)] module
- Integration tests: tests/ directory, one file per major feature
- Property tests: tests/proptests/, require --features proptest to run
-->

## CI Requirements

<!--
What must pass before code is merged?
How long should the test suite take?
Are there tests that run nightly vs on every PR?
-->