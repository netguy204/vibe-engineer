# Wiki Bootstrap Workflow

A workflow for analyzing a codebase and generating wiki pages that document its cohesive concepts.

## Overview

**Input**: A codebase with no existing documentation artifacts (no chunks, subsystems, etc.)
**Output**: A set of proposed wiki pages with intent, scope, code_references, and suggested backreferences

## Phase 1: Structural Analysis

**Goal**: Understand the physical structure of the codebase.

**Prompt for agent**:
```
Analyze the structure of this codebase:

1. List all source directories and their apparent purpose (based on naming)
2. Identify the main entry points (CLI, API, main modules)
3. Map the major files in each directory
4. Note any configuration files, test directories, or non-code assets

Output a structured summary:
- Directory tree with annotations
- Entry points identified
- File counts by directory
```

## Phase 2: Dependency Mapping

**Goal**: Understand how code relates to other code.

**Prompt for agent**:
```
Analyze the import/dependency relationships in this codebase:

1. For each major source file, list what it imports from within the project
2. Identify "hub" files - files that are imported by many others
3. Identify "leaf" files - files that import others but aren't imported themselves
4. Find clusters of files that import each other heavily

Output:
- Hub files (imported by 5+ other files)
- Dependency clusters (groups of files with high internal imports)
- Isolated modules (files with few connections)
```

## Phase 3: Concept Discovery

**Goal**: Identify cohesive concepts that could become wiki pages.

**Prompt for agent**:
```
Based on the structural analysis and dependency mapping, identify cohesive concepts in this codebase.

A concept is a coherent idea that:
- Has a clear purpose/intent
- Is implemented across one or more files
- Could be explained as a "topic" to a new developer

For each concept, provide:
1. **Name**: A short, descriptive name (e.g., "Authentication", "Data Validation", "CLI Commands")
2. **Intent**: One sentence explaining what this concept accomplishes
3. **Key files**: The primary files that implement this concept
4. **Related files**: Files that use or interact with this concept
5. **Boundaries**: What's clearly in-scope vs out-of-scope

Look for concepts at multiple levels:
- Infrastructure (logging, configuration, database access)
- Domain (business logic, core algorithms)
- Interface (CLI, API, UI components)
- Cross-cutting (error handling, validation patterns)
```

## Phase 4: Page Boundary Refinement

**Goal**: Finalize which concepts become wiki pages and resolve overlaps.

**Prompt for agent**:
```
Review the discovered concepts and propose final wiki page boundaries.

For each proposed wiki page:

1. **Page name**: The wiki page identifier
2. **Intent**: What this page documents (2-3 sentences)
3. **Scope**:
   - In scope: What topics this page covers
   - Out of scope: What belongs elsewhere
4. **Code references**: List of files/symbols this page governs
   - Format: `path/to/file.py#SymbolName`
5. **Invariants**: Rules that should always hold for this concept (if apparent)
6. **Relationships**: How this page relates to other pages
   - Uses: concepts this depends on
   - Used by: concepts that depend on this

Resolve any overlaps:
- If two concepts share significant code, decide which page owns it
- If a concept is too small, consider merging with another
- If a concept is too large, consider splitting

Target: 10-30 wiki pages for a medium-sized codebase
```

## Phase 5: Backreference Planning

**Goal**: Plan how code will reference wiki pages.

**Prompt for agent**:
```
For each source file in the codebase, determine which wiki page(s) it should reference.

Output a mapping:
- File path → Primary wiki page (the main concept this file implements)
- File path → Secondary wiki pages (concepts this file uses but doesn't own)

Propose backreference comment format:
```python
# Concept: docs/wiki/page_name - Brief description of relationship
```

For files that implement a concept, the comment goes at the top.
For specific functions/classes that relate to a concept, the comment goes above that symbol.
```

## Output Format

The final output should be a structured report:

```markdown
# Wiki Bootstrap Report

## Summary
- Total files analyzed: N
- Proposed wiki pages: M
- Coverage: X% of source files mapped to concepts

## Proposed Wiki Pages

### 1. [Page Name]

**Intent**: [What this concept accomplishes]

**Scope**:
- In: [Topics covered]
- Out: [Topics belonging elsewhere]

**Code References**:
- `path/to/file.py#Symbol` - [What it implements]
- `path/to/other.py` - [Entire file belongs to this concept]

**Invariants**:
- [Rule that must hold]

**Relationships**:
- Uses: [Other pages this depends on]
- Used by: [Pages that depend on this]

### 2. [Next Page Name]
...

## Backreference Plan

| File | Primary Concept | Secondary Concepts |
|------|-----------------|-------------------|
| path/to/file.py | Page Name | Other Page, Another |
| ... | ... | ... |

## Observations

[Notes about the codebase structure, potential issues, suggested improvements]
```
