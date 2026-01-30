# Article Workflow Template

Template for creating new articles.

## Directory Structure

```
docs/articles/
  articles.md                           # index of all series
  {series_name}/
    SERIES.md                           # series overview, themes, article sequence
    {article_name}/
      ARTICLE.md                        # single file for entire article lifecycle
```

## Creating a New Article

1. Create the article directory: `docs/articles/{series_name}/{article_name}/`
2. Create ARTICLE.md with the sections below
3. Fill in metadata
4. Work through the stages: outlining, drafting, published

## After Publishing

Run the series refinement workflow:

1. **Plan vs Outcome Diff** - Compare original outline against what got written
2. **Update Themes Ledger** - Add new framings to SERIES.md
3. **Update Subsequent Outlines** - Revise planned articles based on learnings
4. **Migrate Parking Lot Items** - Move cut ideas to appropriate future articles

---

## ARTICLE.md Sections

### Metadata (YAML frontmatter)

- title: Working title
- status: OUTLINING | DRAFTING | PUBLISHED

### Beat Outline

Agent creates beats based on series outline. Human adds voice capture as blockquotes directly under each beat. Mark beats as done when incorporated into draft.

### Draft

Agent assembles voice captures into prose. Human edits directly. Continuous iteration until published. No separate "final" section.

### Parking Lot

Ideas cut for flow. Note where they might fit (other articles, future series).

---

## Collaboration Pattern

- Agent presents 2-3 options for structural decisions (reordering, cutting, merging)
- Human chooses; agent does not make unilateral structural changes
- Human edits draft directly for voice
- Uncertainties marked inline with [?]
