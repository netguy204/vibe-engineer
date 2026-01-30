---
description: Continue work on an article in the current series.
---

## Article Workflow

Articles live in `docs/articles/{series_name}/{article_name}/ARTICLE.md`.

### Structure

```
docs/articles/
  articles.md                           # index of all series
  {series_name}/
    SERIES.md                           # series overview, themes ledger, article sequence
    {article_name}/
      ARTICLE.md                        # single file for entire article lifecycle
```

### Finding Context

1. **Series overview**: Read `SERIES.md` in the series directory for:
   - Series metadata (audience, thesis, tone)
   - **Themes Ledger** — framings to weave through articles
   - **Article Sequence** — outlines for all planned articles

2. **Current article**: The `ARTICLE.md` file contains:
   - Metadata (title, status: OUTLINING | DRAFTING | PUBLISHED)
   - Beat Outline with voice captures
   - Draft section
   - Parking Lot for cut ideas

### The Workflow Loop

The workflow is **iterative**, not linear. Expect to cycle:

```
beats → draft → beats → draft → ... → refine → publish
```

**When OUTLINING:**
- Human adds voice captures as blockquotes under beats
- Beats can be added, removed, or reordered as understanding evolves

**When DRAFTING:**
- Agent assembles voice captures into flowing prose
- Human edits draft directly for voice
- New insights may require returning to beats
- Mark uncertainties inline with [?]

**Collaboration rules:**
- Agent presents 2-3 options for structural decisions (reordering, cutting, merging)
- Human chooses; agent does not make unilateral structural changes
- Preserve human's word choices; add transitions, not arguments

### After Publishing

Run the series refinement workflow:

1. **Plan vs Outcome Diff** — Compare original outline against what got written
2. **Update Themes Ledger** — Add new framings discovered during writing
3. **Update Subsequent Outlines** — Revise planned articles based on learnings
4. **Migrate Parking Lot Items** — Move cut ideas to appropriate future articles

## Instructions

1. Ask which article to continue (or accept from $ARGUMENTS)

2. Read the series `SERIES.md` to understand:
   - The Themes Ledger (framings to weave in)
   - The article's outline in the Article Sequence

3. Read the article's `ARTICLE.md` to understand current state

4. Based on status:
   - **OUTLINING**: Help human develop beats, prompt for voice capture
   - **DRAFTING**: Assemble voice into prose, iterate with human
   - **PUBLISHED**: Trigger series refinement workflow

5. Continue the iterative workflow until human indicates completion
