-- Prototype schema for referential integrity tracking
-- This models the VE artifact reference graph with FK constraints

PRAGMA foreign_keys = ON;

-- ============================================
-- ARTIFACT TABLES
-- ============================================

-- All artifacts have a canonical ID and type
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,  -- e.g., "chunks/auth_refactor", "narratives/login_flow"
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'chunk', 'narrative', 'investigation', 'subsystem', 'friction'
    )),
    status TEXT,  -- PLANNING, IMPLEMENTING, ACTIVE, etc.
    file_path TEXT NOT NULL,  -- Absolute path to GOAL.md/OVERVIEW.md
    file_hash TEXT,  -- SHA256 of file content for staleness detection
    last_synced_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Code files that contain backreferences
CREATE TABLE code_files (
    file_path TEXT PRIMARY KEY,
    file_hash TEXT,
    last_synced_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Friction entries (special: live inside FRICTION.md, not separate files)
CREATE TABLE friction_entries (
    entry_id TEXT PRIMARY KEY,  -- F001, F002, etc.
    theme TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'ADDRESSED', 'RESOLVED'))
);

-- ============================================
-- EDGE TABLES (with FK constraints)
-- ============================================

-- Chunk → Narrative (frontmatter: narrative: name)
CREATE TABLE chunk_narrative_refs (
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    narrative_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    PRIMARY KEY (chunk_id)  -- A chunk can only belong to one narrative
);

-- Chunk → Investigation (frontmatter: investigation: name)
CREATE TABLE chunk_investigation_refs (
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    investigation_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    PRIMARY KEY (chunk_id)  -- A chunk can only come from one investigation
);

-- Chunk → Subsystem (frontmatter: subsystems: [{id, relationship}])
CREATE TABLE chunk_subsystem_refs (
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    subsystem_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    relationship TEXT NOT NULL CHECK (relationship IN ('implements', 'uses', 'extends')),
    PRIMARY KEY (chunk_id, subsystem_id)
);

-- Chunk → Friction Entry (frontmatter: friction_entries: [{entry_id, scope}])
CREATE TABLE chunk_friction_refs (
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    entry_id TEXT NOT NULL REFERENCES friction_entries(entry_id) ON DELETE RESTRICT,
    scope TEXT NOT NULL CHECK (scope IN ('full', 'partial')),
    PRIMARY KEY (chunk_id, entry_id)
);

-- Chunk → Code (frontmatter: code_references: [{ref, implements}])
CREATE TABLE chunk_code_refs (
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,  -- Can't FK to code_files (might not exist yet)
    symbol_path TEXT,  -- Optional: function/class within file
    implements TEXT NOT NULL,
    PRIMARY KEY (chunk_id, file_path, symbol_path)
);

-- Code → Chunk backreference (code comment: # Chunk: docs/chunks/name)
CREATE TABLE code_chunk_backrefs (
    file_path TEXT NOT NULL REFERENCES code_files(file_path) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    line_number INTEGER NOT NULL,
    PRIMARY KEY (file_path, chunk_id, line_number)
);

-- Code → Subsystem backreference (code comment: # Subsystem: docs/subsystems/name)
CREATE TABLE code_subsystem_backrefs (
    file_path TEXT NOT NULL REFERENCES code_files(file_path) ON DELETE CASCADE,
    subsystem_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    line_number INTEGER NOT NULL,
    PRIMARY KEY (file_path, subsystem_id, line_number)
);

-- Narrative/Investigation → Chunk (proposed_chunks[].chunk_directory)
CREATE TABLE proposed_chunk_refs (
    parent_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    chunk_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL,  -- NULL if not yet created
    prompt TEXT NOT NULL,
    prompt_index INTEGER NOT NULL,  -- Position in proposed_chunks array
    PRIMARY KEY (parent_id, prompt_index)
);

-- Subsystem → Chunk (frontmatter: chunks: [name, ...])
CREATE TABLE subsystem_chunk_refs (
    subsystem_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    PRIMARY KEY (subsystem_id, chunk_id)
);

-- Artifact → Artifact ordering (frontmatter: created_after: [name, ...])
CREATE TABLE artifact_ordering (
    artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    after_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    PRIMARY KEY (artifact_id, after_id)
);

-- ============================================
-- VIEWS FOR INTEGRITY CHECKING
-- ============================================

-- Find code→chunk backrefs without corresponding chunk→code refs
CREATE VIEW orphaned_code_backrefs AS
SELECT
    cb.file_path,
    cb.chunk_id,
    cb.line_number,
    'Code references chunk but chunk does not reference code' as issue
FROM code_chunk_backrefs cb
LEFT JOIN chunk_code_refs cc
    ON cb.chunk_id = cc.chunk_id AND cb.file_path = cc.file_path
WHERE cc.chunk_id IS NULL;

-- Find chunk→code refs without corresponding code→chunk backrefs
CREATE VIEW missing_code_backrefs AS
SELECT
    cc.chunk_id,
    cc.file_path,
    cc.symbol_path,
    'Chunk references code but code has no backref to chunk' as issue
FROM chunk_code_refs cc
LEFT JOIN code_chunk_backrefs cb
    ON cc.chunk_id = cb.chunk_id AND cc.file_path = cb.file_path
WHERE cb.chunk_id IS NULL;

-- Find proposed chunks pointing to non-existent chunk directories
CREATE VIEW stale_proposed_chunks AS
SELECT
    pc.parent_id,
    pc.chunk_id,
    pc.prompt,
    'proposed_chunks references non-existent chunk' as issue
FROM proposed_chunk_refs pc
WHERE pc.chunk_id IS NOT NULL
AND pc.chunk_id NOT IN (SELECT id FROM artifacts WHERE artifact_type = 'chunk');

-- ============================================
-- SYNC COMPLEXITY NOTES
-- ============================================
--
-- The challenge with this approach is keeping the database in sync with files:
--
-- 1. WHEN TO SYNC:
--    - On every file save? (expensive, needs file watcher)
--    - On git commit? (via hook)
--    - On-demand via `ve validate`? (simplest)
--    - Lazy sync when validation requested?
--
-- 2. SYNC DIRECTION:
--    - Files are authoritative (database is derived)
--    - Never modify files based on database state
--    - Database is read-only cache + constraint checker
--
-- 3. STALENESS DETECTION:
--    - file_hash column enables incremental sync
--    - Only re-parse files whose hash changed
--    - Still need to scan all files to detect deletions
--
-- 4. PERFORMANCE:
--    - Initial full sync: O(files + artifacts)
--    - Incremental sync: O(changed files)
--    - Validation queries: O(1) with indexes
