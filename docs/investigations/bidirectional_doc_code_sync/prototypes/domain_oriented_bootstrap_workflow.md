# Domain-Oriented Bootstrap Workflow

A workflow for analyzing a codebase and generating subsystem documentation that prioritizes **business domains** over infrastructure patterns.

## Overview

**Input**: A codebase (with or without existing documentation)

**Phases**:
1. Business Capability Discovery
2. Entity & Lifecycle Mapping
3. Business Rule Extraction
4. Domain Boundary Refinement
5. Infrastructure Annotation
6. Backreference Planning

**Output**:
- 6 intermediate analysis artifacts (saved for review at each phase)
- Final subsystem proposals with clear boundaries
- Backreference plan mapping files to subsystems

**Key Principle**: Subsystems document **atomic parts of a software project that hang together and change together**. They are the wiki pages that help engineers understand the system.

## Why This Workflow Exists

A common mistake when bootstrapping wiki pages is to over-index on infrastructure patterns:
- "Middleware Pipeline"
- "Error Handling"
- "Instrumentation"
- "Data Access Layer"

These are real patterns, but they're **not the most valuable documentation**. Engineers working on the codebase need to understand:
- What business problems does this system solve?
- What are the core domain entities and their lifecycles?
- What business rules must always hold?

Infrastructure patterns support the domains - they shouldn't be the main theme.

## The Anti-Pattern: Infrastructure-First Analysis

```
❌ WRONG: Start with technical layers
   → "I see middleware, let me document the middleware pipeline"
   → "There's Redis usage, let me document the caching subsystem"
   → "OpenTelemetry is everywhere, let me document instrumentation"

Result: 12 subsystems, all infrastructure, none answering "what does this system DO?"
```

## The Correct Approach: Domain-First Analysis

```
✓ RIGHT: Start with business questions
   → "What business problem does each service solve?"
   → "What are the core entities users care about?"
   → "What workflows do users go through?"
   → "What business rules must never be violated?"

Result: 8 subsystems mapping to business capabilities, with infrastructure as supporting notes
```

---

## Phase 1: Business Capability Discovery

**Goal**: Identify what the system DOES for users, not how it's built.

**Prompt for agent**:
```
Analyze this codebase from a BUSINESS perspective, not a technical one.

1. What business problems does this system solve? Who are the users?

2. For each major service/module, answer:
   - What business capability does it provide?
   - What would a product manager call this feature?
   - What user workflow does it support?

3. Identify the core business entities:
   - What "things" do users create, manage, or interact with?
   - What are the lifecycle states of each entity?
   - What business events happen to these entities?

DO NOT focus on:
- Technical patterns (middleware, caching, etc.)
- Infrastructure concerns (logging, auth middleware)
- Code organization (packages, modules)

Output: A list of business capabilities with plain-language descriptions.
```

**Example output**:
```
Business Capabilities:
1. Commitment Management - Users review, approve, and purchase cloud commitments
2. Cost Exploration - Users analyze historical cloud costs by various dimensions
3. Cost Forecasting - Users project future costs and model optimization initiatives
4. Billing - The system generates bills and manages payment collection
```

**Intermediate output**: Save as `phase1_business_capabilities.md`

---

## Phase 2: Entity & Lifecycle Mapping

**Goal**: Understand the core domain entities and their state machines.

**Prompt for agent**:
```
For each business capability identified, map the domain entities:

1. What are the primary entities? (Things with identity that persist)
   - Example: "Commitment Batch", "Cost Layer", "Forecast", "Bill"

2. What states can each entity be in?
   - Draw the state machine if there's a lifecycle
   - Example: Bill: DRAFT → READY_TO_INVOICE → INVOICED

3. What relationships exist between entities?
   - One-to-many, many-to-many relationships
   - Which entities "own" others?

4. What external systems do entities interact with?
   - Payment providers, cloud APIs, notification services

Look at:
- Database schemas (Supabase types, Prisma schemas, migrations)
- Type definitions (especially enums for states)
- API endpoints (what resources are exposed?)

Output: Entity relationship diagram and state machines for key entities.
```

**Intermediate output**: Save as `phase2_entity_lifecycle_mapping.md`

---

## Phase 3: Business Rule Extraction

**Goal**: Identify the invariants that must always hold.

**Prompt for agent**:
```
For each domain, identify the business rules that must NEVER be violated:

1. What constraints exist on entity states?
   - "A bill cannot be invoiced without line items"
   - "Commitments require batch approval before purchase"

2. What validation rules exist?
   - Required fields, valid transitions, consistency checks

3. What are the authorization rules?
   - Who can perform which actions?
   - Organization-level isolation requirements

4. What are the calculation rules?
   - How are costs computed? Savings calculated?
   - What formulas must be consistent?

Look for these in:
- Validation logic in services
- State transition guards
- Database constraints
- Comments mentioning "must", "always", "never"

Output: Numbered list of business rules per domain.
```

**Intermediate output**: Save as `phase3_business_rules.md`

---

## Phase 4: Domain Boundary Refinement

**Goal**: Finalize subsystem boundaries based on business cohesion.

**Prompt for agent**:
```
Review the discovered domains and refine boundaries:

1. Should any domains be merged?
   - Do they share most entities?
   - Do they always change together?
   - Would splitting them create artificial boundaries?

2. Should any domains be split?
   - Does one domain have multiple distinct user workflows?
   - Are there clear sub-domains with different rules?

3. What are the dependencies between domains?
   - Which domain feeds data to others?
   - Which domains trigger actions in others?

4. Name each domain using business language:
   - ✓ "commitment_fulfillment" (what it does)
   - ✗ "consolidation_service" (technical name)
   - ✓ "cost_hierarchy" (business concept)
   - ✗ "tree_management" (implementation detail)

Output: Final list of domain subsystems with clear boundaries.
```

**Intermediate output**: Save as `phase4_domain_boundaries.md`

---

## Phase 5: Infrastructure Annotation

**Goal**: Document infrastructure patterns as SUPPORTING material, not primary subsystems.

**Prompt for agent**:
```
NOW (and only now) identify infrastructure patterns:

1. What cross-cutting concerns exist?
   - Authentication, authorization, logging, caching, error handling

2. For each infrastructure pattern:
   - Which domains use it?
   - Is it consistent across domains or fragmented?
   - Are there known deviations?

3. Should any infrastructure be a subsystem?
   Only if ALL of these are true:
   - It has complex business rules (not just technical patterns)
   - Engineers frequently need to understand it to do their work
   - It has known deviations that need tracking

   Usually, infrastructure belongs in a "Supporting Patterns" section,
   not as top-level subsystems.

Output:
- List of infrastructure patterns with brief descriptions
- Recommendation: subsystem or supporting pattern?
```

**Intermediate output**: Save as `phase5_infrastructure_patterns.md`

---

## Phase 6: Backreference Planning

**Goal**: Create a concrete plan for adding code→documentation links.

**Prompt for agent**:
```
For each proposed subsystem, plan the backreferences:

1. Identify the code locations that should reference this subsystem:
   - Entry points (API routes, CLI commands, event handlers)
   - Core logic (services, domain models, business rules)
   - NOT: utilities, helpers, or infrastructure that serves many subsystems

2. Determine the appropriate granularity for each location:
   - MODULE level: When the entire file belongs to one subsystem
     → Comment at top of file: `# Subsystem: subsystem_name`
   - CLASS level: When a class implements subsystem logic but file has multiple concerns
     → Comment above class definition
   - FUNCTION level: When only specific functions belong to the subsystem
     → Comment above function definition

3. Handle shared code appropriately:
   - Code used by 3+ subsystems → NO backreference (it's infrastructure)
   - Code used by 2 subsystems → Reference the PRIMARY owner
   - Code used by 1 subsystem → Reference that subsystem

4. Validate coverage:
   - Each subsystem should have at least 3 code references
   - No file should have more than 2 subsystem references
   - If a file needs 3+ references, it may need refactoring

Output: Table mapping files/classes/functions to subsystem references.
```

**Example output**:
```markdown
| Location | Level | Subsystem | Rationale |
|----------|-------|-----------|-----------|
| `routes/commitments.py` | MODULE | commitment_fulfillment | All routes serve this domain |
| `services/billing/invoice.py` | MODULE | financial_billing | Core billing logic |
| `services/forecast/projector.py::Projector` | CLASS | cost_forecasting | Main projection engine |
| `utils/cost_calc.py` | NONE | Used by 4 subsystems | Infrastructure |
```

**Intermediate output**: Save as `phase6_backreference_plan.md`

---

## Output Format

The final output should prioritize domains:

```markdown
# Wiki Bootstrap Report

## Summary
- Business domains identified: N
- Supporting infrastructure patterns: M
- Coverage: X% of business logic mapped

## Domain Subsystems (Primary Documentation)

### 1. [Domain Name]

**Business Intent**: [What problem does this solve for users?]

**Core Entities**:
- [Entity] - [What it represents]
- [Entity] - [What it represents]

**Lifecycle**: [State machine if applicable]
- STATE_A → STATE_B → STATE_C

**Key Business Rules**:
1. [Rule that must never be violated]
2. [Another invariant]

**Code Locations**:
- `path/to/service/` - [What aspect it implements]

**Relationships**:
- Uses: [Other domains this depends on]
- Used by: [Domains that depend on this]

### 2. [Next Domain]
...

## Supporting Infrastructure (Secondary)

These patterns support the domains but are not primary documentation targets:

| Pattern | Purpose | Status |
|---------|---------|--------|
| Authentication | JWT validation, session management | Stable |
| Caching | Redis-based query caching | Consistent |
| Error Handling | Standardized API errors | Minor deviations |

Only elevate infrastructure to a full subsystem if it has complex rules
that engineers frequently misunderstand.

## Domain Relationship Diagram

[ASCII or description of how domains relate]
```

---

## Common Pitfalls to Avoid

### Pitfall 1: Technical Names
```
❌ "data_access_layer"     → ✓ "cost_analytics"
❌ "middleware_pipeline"   → ✓ (just a supporting pattern)
❌ "service_template"      → ✓ (just a supporting pattern)
```

### Pitfall 2: Code Organization as Domains
```
❌ "backend-api-lib subsystem" (that's a package, not a domain)
❌ "services layer" (that's code organization)
✓ "commitment_fulfillment" (that's a business capability)
```

### Pitfall 3: Every Pattern is a Subsystem
```
❌ 12 subsystems including "Error Handling", "Logging", "Caching"
✓ 8 domain subsystems + "Supporting Infrastructure" section
```

### Pitfall 4: Missing the "Why"
```
❌ "This subsystem manages the forecast_entities table"
✓ "This subsystem lets users project future costs and model savings initiatives"
```

---

## Validation Checklist

Before finalizing the bootstrap report, verify:

- [ ] Each subsystem answers "what does this do for users?"
- [ ] Subsystem names use business language, not technical jargon
- [ ] Core entities are things users care about, not implementation details
- [ ] Business rules are constraints users would understand
- [ ] Infrastructure is documented but not the primary focus
- [ ] A product manager could read this and understand the system

If infrastructure subsystems outnumber domain subsystems, **start over**.

---

## System Boundary Identification

How do you know when you've found the right boundaries? Use these heuristics:

### Signs of a Well-Bounded Subsystem

1. **Single business owner**: One person/team could be accountable for this domain
2. **Cohesive vocabulary**: The entities and operations share terminology
3. **Independent lifecycle**: Changes to this domain rarely require changes to others
4. **Clear data ownership**: Entities belong to this subsystem, not shared across many

### Signs Boundaries Are Wrong

| Symptom | Likely Problem | Solution |
|---------|----------------|----------|
| Two subsystems always change together | Artificial split | Merge them |
| One subsystem has 15+ entities | Too broad | Split by user workflow |
| Subsystem has no clear "owner" | Technical, not business | Demote to infrastructure |
| Same entity appears in 3+ subsystems | Missing core domain | Create entity-owning subsystem |
| Subsystem name is a verb ("Processing") | Action, not domain | Rename to noun (what it manages) |

### The "Could You Explain It?" Test

For each proposed subsystem, ask: **Could you explain what this does to a new engineer in 2 minutes?**

- ✓ "commitment_fulfillment manages the lifecycle of cloud commitments - from recommendation through purchase to expiration tracking"
- ✗ "middleware_pipeline handles request processing" (too vague, what requests? what processing?)

### Cross-Repository Boundaries (Task Context)

When working in a task context with multiple repositories:

1. **Subsystems can span repositories**: A business domain may have implementations across frontend/backend/infrastructure repos
2. **Ownership follows the domain, not the repo**: The subsystem lives in the artifacts repo, references code in all relevant repos
3. **Code references use repo prefixes**: `platform:apps/backend-api-billing/` not just `apps/backend-api-billing/`

Example cross-repo subsystem:
```markdown
**Code References**:
- `platform:apps/backend-api-billing/` - Backend billing logic
- `platform-web:src/features/billing/` - Billing UI components
- `infrastructure:terraform/stripe/` - Stripe configuration
```

---

## Intermediate Output Summary

Each phase produces a saved artifact for transparency and review:

| Phase | Output File | Purpose |
|-------|-------------|---------|
| 1 | `phase1_business_capabilities.md` | Raw business capability discovery |
| 2 | `phase2_entity_lifecycle_mapping.md` | Entity relationships and state machines |
| 3 | `phase3_business_rules.md` | Invariants per domain |
| 4 | `phase4_domain_boundaries.md` | Refined subsystem boundaries |
| 5 | `phase5_infrastructure_patterns.md` | Cross-cutting concerns |
| 6 | `phase6_backreference_plan.md` | Code→doc link plan |
| Final | `wiki_bootstrap_report.md` | Complete bootstrap report |

**Why save intermediates?**

1. **Review checkpoints**: Operator can validate direction at each phase before continuing
2. **Debugging**: When final output seems wrong, intermediates show where analysis diverged
3. **Iteration**: Can re-run later phases without repeating earlier analysis
4. **Learning**: Comparing intermediates across codebases reveals patterns

**Storage location**: Save in a dedicated directory like `docs/wiki_bootstrap/` or alongside the investigation that triggered the bootstrap
