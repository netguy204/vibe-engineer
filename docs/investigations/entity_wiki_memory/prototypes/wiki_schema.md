# Entity Wiki Schema

You are constructing a personal wiki for an AI entity based on a session transcript. This wiki represents the entity's accumulated knowledge and self-understanding.

## Directory Structure

```
wiki/
├── index.md          # Catalog of all pages with one-line summaries
├── identity.md       # Who I am, my role, my working style, my values
├── domain/           # Domain knowledge pages (one per major topic)
│   └── <topic>.md
├── projects/         # Per-project working notes
│   └── <project>.md
├── techniques/       # Approaches, patterns, tools I've learned to use well
│   └── <technique>.md
├── relationships/    # People, teams, other entities I work with
│   └── <person_or_team>.md
└── log.md            # Chronological session log
```

## Page Conventions

- Use wikilinks: `[[page_name]]` for cross-references
- Every page has YAML frontmatter with at minimum: `title`, `created`, `updated`
- Keep pages focused — one concept per page, split when a page exceeds ~500 words
- identity.md should capture: role, strengths, preferences, working style, values, hard-won lessons
- domain/ pages should capture: concepts, relationships between concepts, key facts, open questions
- techniques/ pages should capture: what the technique is, when to use it, pitfalls, examples from experience
- log.md entries use format: `## [YYYY-MM-DD] session | Brief summary`

## Instructions

Read the provided transcript carefully. Extract:

1. **Identity signals**: How does the entity describe itself? What does it care about? What's its working style?
2. **Domain knowledge**: What technical or domain concepts does it demonstrate understanding of?
3. **Project context**: What project is being worked on? What are the goals, constraints, current state?
4. **Techniques**: What approaches or patterns does the entity use effectively?
5. **Relationships**: Who does it interact with? What are the dynamics?
6. **Learnings**: What did the entity discover or change its mind about during this session?

Write the wiki pages. Be thorough but not verbose — capture the knowledge, not the conversation.
