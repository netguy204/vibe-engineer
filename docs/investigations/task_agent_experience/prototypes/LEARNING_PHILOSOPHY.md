# The Vibe Engineering Learning Journey

Vibe engineering is designed to meet operators where they are and grow with their needs. Each artifact type exists because operators naturally discover they need it.

## The Progression

### Stage 1: The Chunk Loop (Single Project)

**Entry point**: An operator has a project and wants to make changes.

**What they learn**:
- Chunks define discrete units of work
- The create → plan → implement → complete cycle
- GOAL.md captures intent, PLAN.md captures approach
- Code references tie documentation to implementation

**The loop feels like**:
1. "I want to do X" → `/chunk-create`
2. "How should I do it?" → `/chunk-plan`
3. "Let me do it" → `/chunk-implement`
4. "Done, let me record that" → `/chunk-complete`

**What makes this fun**: Immediate gratification. Small, complete cycles. Clear progress.

### Stage 2: Larger Artifacts (Still Single Project)

Operators don't need to be taught these—they discover them when chunks aren't enough.

**Graduation trigger → Narratives**: "This is too big for one chunk"
- The work decomposes naturally into multiple chunks
- They want to track progress across related chunks
- `/narrative-create` groups chunks under a shared goal

**Graduation trigger → Subsystems**: "I keep touching the same patterns"
- They notice architectural patterns emerging
- The same code gets modified by multiple chunks
- `/subsystem-discover` documents the pattern for consistency

**Graduation trigger → Investigations**: "I need to understand before I act"
- The problem isn't clear yet
- Multiple hypotheses exist
- `/investigation-create` provides structured exploration

**What makes this fun**: The artifacts emerge from real needs, not imposed process. Operators feel clever when they discover them.

### Stage 3: Multi-Project Tasks

**Graduation trigger**: "My work spans multiple repositories"

This is the biggest leap because it introduces new concepts:
- **Task directory**: A workspace containing multiple projects
- **External artifact repo**: Where cross-cutting docs live
- **External references**: How projects point to shared docs

**What makes this manageable**:
- Chunks are still chunks
- Narratives are still narratives
- The create/plan/implement/complete cycle is unchanged
- Only the WHERE changes, not the WHAT

**The key insight**: You're not learning a new system. You're learning that the same system works at a larger scale:
- Task root for cross-cutting work
- Project directories for implementation
- Same commands, same artifacts, bigger scope

## Design Principles

### 1. Documents Are the Teaching Mechanism

All documentation is equally consumable by agents and operators. This creates pull-based learning:

```
Code → backreference → chunk/subsystem doc → understanding
```

An agent reading code sees:
```python
# Chunk: docs/chunks/0012-symbolic_code_refs
# Subsystem: docs/subsystems/template_system
```

And follows those references to understand why code exists. An operator does exactly the same thing.

You discover artifacts when you need them. The code itself teaches you what documentation matters. No curriculum required—curiosity and need drive discovery.

### 2. No Forced Curricula

Operators should never be told "you're not ready for narratives yet." They discover each artifact type when they need it. The documentation explains what's available; the need makes it relevant.

### 3. Same Concepts, Different Scale

A chunk in a task context is still a chunk. It has a GOAL.md and a PLAN.md. It goes through the same lifecycle. The only difference is that it lives in the external repo and creates references in participating projects.

### 4. Context is Physical

You know what context you're in by where you are:
- In the task root → you're thinking cross-project
- In a project directory → you're implementing in that project

This matches how developers already think about multi-repo work.

### 5. Mistakes are Recoverable

If someone makes an error (wrong project, wrong artifact), the system should provide clear messages guiding them to the right action. Commands work from task root for cross-project work, or from individual projects for project-specific work.

### 6. Documentation Grows with Need

- First chunk: Just needs CLAUDE.md's chunk section
- First narrative: Discovers the narratives section
- First task: Discovers task CLAUDE.md's multi-project guidance

The documentation is always there, but operators only read what they need.

## Anti-Patterns to Avoid

**Don't**: Require operators to understand all concepts before starting
**Do**: Let them start with chunks and discover the rest

**Don't**: Make task context feel like a different tool
**Do**: Make it feel like the same tool at a bigger scale

**Don't**: Hide complexity that will surprise them later
**Do**: Make the structure transparent (external.yaml shows where things point)

**Don't**: Require explicit mode switching
**Do**: Let directory context determine mode naturally

## Success Metrics

The learning journey is working when:
1. Operators can start making changes within minutes of first use
2. They naturally discover larger artifacts when they need them
3. Multi-project tasks feel like a logical extension, not a new tool
4. Mistakes lead to clear error messages, not mysterious failures
5. Operators feel increasingly capable over time, not increasingly burdened
