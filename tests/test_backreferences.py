"""Tests for backreference scanning and management.

# Chunk: docs/chunks/backref_language_agnostic - Tests for backreference filter bug fix
# Chunk: docs/chunks/federation_qualified_refs - Tests for qualified backreference grammar
"""

import pathlib
import subprocess

import pytest

from conftest import make_ve_initialized_git_repo
from models import ArtifactType
from backreferences import (
    BackreferenceInfo,
    QualifierKind,
    count_backreferences,
    parse_backreference,
    scan_backreferences,
    update_backreferences,
)


class TestCountBackreferencesFilterBugFix:
    """Tests for the filter bug fix where files with only subsystem/narrative refs were excluded."""

    def test_count_backreferences_includes_subsystem_only_files(self, temp_project):
        """File with only # Subsystem: comments is included in results."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only a subsystem backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "subsystem_only.py").write_text(
            '"""Module with only subsystem ref."""\n'
            "# Subsystem: docs/subsystems/test_subsystem - Test subsystem\n"
            "\n"
            "def foo():\n"
            "    pass\n"
        )

        # Add to git so it's discoverable
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only subsystem ref
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("subsystem_only.py")
        assert len(info.chunk_refs) == 0
        assert len(info.subsystem_refs) == 1
        assert info.subsystem_refs[0] == "test_subsystem"

    def test_count_backreferences_includes_narrative_only_files(self, temp_project):
        """File with only # Narrative: comments is included in results."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only a narrative backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "narrative_only.py").write_text(
            '"""Module with only narrative ref."""\n'
            "# Narrative: docs/narratives/test_narrative - Test narrative\n"
            "\n"
            "class Bar:\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only narrative ref
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("narrative_only.py")
        assert len(info.chunk_refs) == 0
        assert len(info.narrative_refs) == 1
        assert info.narrative_refs[0] == "test_narrative"

    def test_count_backreferences_includes_mixed_refs(self, temp_project):
        """File with subsystem and narrative refs (but no chunk refs) is included."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with subsystem and narrative refs but no chunk refs
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "mixed_no_chunk.py").write_text(
            '"""Module with subsystem and narrative refs but no chunk ref."""\n'
            "# Subsystem: docs/subsystems/auth_system - Auth system\n"
            "# Narrative: docs/narratives/login_flow - Login flow narrative\n"
            "\n"
            "def authenticate():\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with mixed refs
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("mixed_no_chunk.py")
        assert len(info.chunk_refs) == 0
        assert len(info.subsystem_refs) == 1
        assert len(info.narrative_refs) == 1

    def test_count_backreferences_still_includes_chunk_only_files(self, temp_project):
        """File with only # Chunk: comments is still included (regression test)."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only chunk refs
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "chunk_only.py").write_text(
            '"""Module with only chunk refs."""\n'
            "# Chunk: docs/chunks/test_chunk - Test chunk implementation\n"
            "\n"
            "def process():\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only chunk refs
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("chunk_only.py")
        assert len(info.chunk_refs) == 1
        assert info.chunk_refs[0] == "test_chunk"

    def test_count_backreferences_excludes_files_with_no_refs(self, temp_project):
        """File with no backreference comments is excluded."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with no backreferences
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "no_refs.py").write_text(
            '"""Module with no backreferences."""\n'
            "\n"
            "def helper():\n"
            "    return 42\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should not find any files
        assert len(results) == 0


class TestCountBackreferencesLanguageAgnostic:
    """Tests for language-agnostic source file scanning."""

    def test_count_backreferences_finds_js_files(self, temp_project):
        """Backreferences in JavaScript files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.js").write_text(
            "// Main application\n"
            "# Chunk: docs/chunks/js_feature - JavaScript feature\n"
            "\n"
            "function main() {\n"
            "    console.log('Hello');\n"
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].chunk_refs == ["js_feature"]

    def test_count_backreferences_finds_ts_files(self, temp_project):
        """Backreferences in TypeScript files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "utils.ts").write_text(
            "// TypeScript utilities\n"
            "# Subsystem: docs/subsystems/type_system - Type system\n"
            "\n"
            "export function helper(): string {\n"
            "    return 'test';\n"
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].subsystem_refs == ["type_system"]

    def test_count_backreferences_finds_go_files(self, temp_project):
        """Backreferences in Go files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "main.go").write_text(
            "package main\n"
            "\n"
            "# Chunk: docs/chunks/go_service - Go service implementation\n"
            "\n"
            "func main() {\n"
            '    fmt.Println("Hello")\n'
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].chunk_refs == ["go_service"]

    def test_count_backreferences_with_explicit_patterns_still_works(self, temp_project):
        """Explicit source_patterns argument still works for backward compatibility."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create files in different directories
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "included.py").write_text(
            "# Chunk: docs/chunks/included - Included\n"
        )

        lib_dir = temp_project / "lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "excluded.py").write_text(
            "# Chunk: docs/chunks/excluded - Excluded\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        # Use explicit pattern to only scan src/
        results = count_backreferences(temp_project, source_patterns=["src/**/*.py"])

        # Should only find the src file
        assert len(results) == 1
        assert results[0].chunk_refs == ["included"]


class TestBackreferenceInfoProperties:
    """Tests for BackreferenceInfo dataclass."""

    def test_unique_chunk_count(self):
        """unique_chunk_count property returns count of unique chunk refs."""
        info = BackreferenceInfo(
            file_path=pathlib.Path("/test/file.py"),
            chunk_refs=["chunk_a", "chunk_a", "chunk_b"],  # 2 unique
            narrative_refs=[],
            subsystem_refs=[],
        )

        assert info.unique_chunk_count == 2

    def test_total_chunk_count(self):
        """total_chunk_count property returns total count including duplicates."""
        info = BackreferenceInfo(
            file_path=pathlib.Path("/test/file.py"),
            chunk_refs=["chunk_a", "chunk_a", "chunk_b"],  # 3 total
            narrative_refs=[],
            subsystem_refs=[],
        )

        assert info.total_chunk_count == 3

    def test_sorting_by_unique_chunk_count(self, temp_project):
        """Results are sorted by unique chunk count descending."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)

        # File with many chunk refs
        (src_dir / "many_refs.py").write_text(
            "# Chunk: docs/chunks/a - A\n"
            "# Chunk: docs/chunks/b - B\n"
            "# Chunk: docs/chunks/c - C\n"
        )

        # File with one chunk ref
        (src_dir / "one_ref.py").write_text(
            "# Chunk: docs/chunks/single - Single\n"
        )

        # File with two chunk refs
        (src_dir / "two_refs.py").write_text(
            "# Chunk: docs/chunks/first - First\n"
            "# Chunk: docs/chunks/second - Second\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should be sorted: many_refs (3), two_refs (2), one_ref (1)
        assert len(results) == 3
        assert results[0].unique_chunk_count == 3
        assert results[1].unique_chunk_count == 2
        assert results[2].unique_chunk_count == 1


class TestQualifiedBackreferenceGrammar:
    """The grammar accepts bare, member-qualified, and org/repo-qualified refs.

    Success criterion: "Scanner matches all three forms and exposes
    (qualifier, artifact_id) per reference; bare refs have qualifier None."
    """

    def test_bare_chunk_ref_has_no_qualifier(self):
        """A bare ref parses with qualifier None and kind BARE."""
        parsed = parse_backreference("# Chunk: docs/chunks/taskdir_layout - Layout")

        assert parsed is not None
        assert parsed.artifact_type == ArtifactType.CHUNK
        assert parsed.artifact_id == "taskdir_layout"
        assert parsed.qualifier is None
        assert parsed.qualifier_kind == QualifierKind.BARE
        assert parsed.is_bare
        assert not parsed.is_qualified

    def test_member_qualified_chunk_ref(self):
        """`<member>::docs/chunks/<id>` yields a MEMBER qualifier."""
        parsed = parse_backreference(
            "# Chunk: pybusiness::docs/chunks/commitment_key - Commitment key"
        )

        assert parsed is not None
        assert parsed.qualifier == "pybusiness"
        assert parsed.qualifier_kind == QualifierKind.MEMBER
        assert parsed.artifact_id == "commitment_key"
        assert parsed.is_qualified
        assert not parsed.is_bare

    def test_repo_qualified_chunk_ref(self):
        """`<org>/<repo>::docs/chunks/<id>` yields a REPO qualifier."""
        parsed = parse_backreference(
            "# Chunk: acme/platform::docs/chunks/commitment_key - Commitment key"
        )

        assert parsed is not None
        assert parsed.qualifier == "acme/platform"
        assert parsed.qualifier_kind == QualifierKind.REPO
        assert parsed.artifact_id == "commitment_key"
        assert parsed.is_qualified

    def test_member_and_repo_qualifiers_are_disjoint_by_slash_count(self):
        """No slash means member; exactly one slash means org/repo."""
        member = parse_backreference("# Subsystem: architecture::docs/subsystems/commitment")
        repo = parse_backreference("# Subsystem: acme/architecture::docs/subsystems/commitment")

        assert member is not None and repo is not None
        assert member.qualifier_kind == QualifierKind.MEMBER
        assert repo.qualifier_kind == QualifierKind.REPO

    def test_qualified_narrative_ref(self):
        """Narrative refs accept qualifiers too."""
        parsed = parse_backreference(
            "# Narrative: pybusiness::docs/narratives/monorepo_federation - Federation"
        )

        assert parsed is not None
        assert parsed.artifact_type == ArtifactType.NARRATIVE
        assert parsed.qualifier == "pybusiness"
        assert parsed.artifact_id == "monorepo_federation"

    def test_qualified_subsystem_ref(self):
        """Subsystem refs accept qualifiers too."""
        parsed = parse_backreference(
            "# Subsystem: pybusiness::docs/subsystems/commitment_baseline - Baseline"
        )

        assert parsed is not None
        assert parsed.artifact_type == ArtifactType.SUBSYSTEM
        assert parsed.qualifier == "pybusiness"
        assert parsed.artifact_id == "commitment_baseline"

    def test_member_qualifier_allows_dots_hyphens_underscores(self):
        """Qualifier character shape follows identifier rules, not just [a-z]."""
        parsed = parse_backreference("# Chunk: py-business_v2.core::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MEMBER
        assert parsed.qualifier == "py-business_v2.core"

    def test_non_backreference_line_is_not_parsed(self):
        """Ordinary comments and code are not backreferences."""
        assert parse_backreference("# just a comment") is None
        assert parse_backreference("def foo():") is None
        assert parse_backreference("# Chunk: not/a/real/path") is None

    def test_reference_round_trips_written_text(self):
        """The parsed reference reconstructs exactly what was written."""
        for ref in (
            "docs/chunks/x",
            "pybusiness::docs/chunks/x",
            "acme/platform::docs/chunks/x",
            "architecture/docs/chunks/x",
        ):
            parsed = parse_backreference(f"# Chunk: {ref} - Description")
            assert parsed is not None, ref
            assert parsed.reference == ref


class TestLegacyPrefixQualifiers:
    """Legacy prefix-style refs are a distinct malformed-qualifier category.

    Success criterion: legacy `<something>/docs/chunks/<id>` refs are "not
    silently treated as bare, not silently accepted" so the workspace validator
    can emit a normalize fix-class for them.
    """

    def test_observed_legacy_prefix_ref_is_malformed(self):
        """The form observed in the wild is recognized and flagged."""
        parsed = parse_backreference(
            "# Chunk: architecture/docs/chunks/smsp_commitment_key - Commitment key"
        )

        assert parsed is not None, "legacy prefix refs must be visible, not invisible"
        assert parsed.qualifier_kind == QualifierKind.MALFORMED
        assert parsed.is_malformed
        assert not parsed.is_bare, "must not be silently treated as bare"
        assert not parsed.is_qualified, "must not be silently accepted as qualified"
        assert parsed.qualifier == "architecture"
        assert parsed.artifact_id == "smsp_commitment_key"
        assert parsed.malformed_reason

    def test_multi_segment_legacy_prefix_is_malformed(self):
        """A nested path prefix is flagged, with the whole prefix captured."""
        parsed = parse_backreference(
            "# Chunk: packages/libs/pybusiness/docs/chunks/realized - Realized"
        )

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED
        assert parsed.qualifier == "packages/libs/pybusiness"
        assert parsed.artifact_id == "realized"

    def test_empty_qualifier_is_malformed(self):
        """`::docs/chunks/x` has nothing before the separator."""
        parsed = parse_backreference("# Chunk: ::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED
        assert parsed.malformed_reason

    def test_too_many_slashes_in_qualifier_is_malformed(self):
        """A qualifier with two slashes is neither a member nor an org/repo."""
        parsed = parse_backreference("# Chunk: a/b/c::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED
        assert parsed.qualifier == "a/b/c"

    def test_empty_repo_part_is_malformed(self):
        """`acme/::docs/...` looks like org/repo but the repo part is empty."""
        parsed = parse_backreference("# Chunk: acme/::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED

    def test_invalid_characters_in_qualifier_are_malformed(self):
        """A qualifier that no identifier rule accepts is flagged."""
        parsed = parse_backreference("# Chunk: arch!tree::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED

    def test_multiple_separators_are_malformed(self):
        """A doubled `::` qualifier mirrors SymbolicReference's rejection."""
        parsed = parse_backreference("# Chunk: a::b::docs/chunks/x - X")

        assert parsed is not None
        assert parsed.qualifier_kind == QualifierKind.MALFORMED


class TestRepoQualifierParityWithFrontmatter:
    """Comment refs and frontmatter refs agree on what `org/repo::` means.

    The goal's point is that "comments can finally express what frontmatter
    already can", so the org/repo rule must be one rule, not two that drift.
    Parity is claimed only for slash-containing, whitespace-free qualifiers: a
    bare member name is valid in a comment and meaningless to
    SymbolicReference, and a qualifier containing whitespace is not a single
    comment token at all. Those are the two intended asymmetries.
    """

    @pytest.mark.parametrize(
        "qualifier",
        [
            "acme/platform",
            "acme-org/platform.py",
            "acme/",
            "/platform",
            "a/b/c",
        ],
    )
    def test_repo_qualifier_matches_symbolic_reference_acceptance(self, qualifier):
        """A slashed qualifier is REPO exactly when frontmatter would accept it."""
        from pydantic import ValidationError

        from models import SymbolicReference

        try:
            SymbolicReference(ref=f"{qualifier}::src/x.py", implements="probe")
            frontmatter_accepts = True
        except ValidationError:
            frontmatter_accepts = False

        parsed = parse_backreference(f"# Chunk: {qualifier}::docs/chunks/x - X")

        assert parsed is not None
        assert (parsed.qualifier_kind == QualifierKind.REPO) == frontmatter_accepts, (
            f"comment grammar and SymbolicReference disagree about '{qualifier}'"
        )

    def test_qualifier_containing_whitespace_is_not_a_reference(self):
        """A comment reference is one token, so whitespace ends it.

        Frontmatter can carry a quoted string with a space in it; a comment
        cannot, so such a line is not a backreference rather than a malformed
        one.
        """
        assert parse_backreference("# Chunk: acme/plat form::docs/chunks/x - X") is None


class TestScanBackreferences:
    """Scanning a whole file yields classified refs with line numbers."""

    def test_scan_reports_line_numbers(self):
        """Line numbers are 1-indexed so callers can report file:line."""
        content = (
            '"""Module."""\n'
            "# Chunk: docs/chunks/bare_one - Bare\n"
            "\n"
            "# Chunk: pybusiness::docs/chunks/qualified_one - Qualified\n"
        )

        refs = scan_backreferences(content)

        assert [(r.artifact_id, r.line_number) for r in refs] == [
            ("bare_one", 2),
            ("qualified_one", 4),
        ]

    def test_scan_mixed_file_classifies_every_form(self):
        """A file mixing all four forms is fully classified in order."""
        content = (
            "# Chunk: docs/chunks/bare - Bare\n"
            "# Chunk: pybusiness::docs/chunks/member - Member\n"
            "# Chunk: acme/platform::docs/chunks/repo - Repo\n"
            "# Chunk: architecture/docs/chunks/legacy - Legacy\n"
            "# Subsystem: pybusiness::docs/subsystems/baseline - Baseline\n"
        )

        refs = scan_backreferences(content)

        assert [(r.artifact_id, r.qualifier_kind) for r in refs] == [
            ("bare", QualifierKind.BARE),
            ("member", QualifierKind.MEMBER),
            ("repo", QualifierKind.REPO),
            ("legacy", QualifierKind.MALFORMED),
            ("baseline", QualifierKind.MEMBER),
        ]


class TestCountBackreferencesQualified:
    """Qualified refs are counted, and malformed ones are quarantined.

    Success criterion: qualified comments stop being invisible to ve commands,
    while legacy prefix-style refs are not silently treated as bare.
    """

    def _write(self, temp_project, name, content):
        make_ve_initialized_git_repo(temp_project)
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / name).write_text(content)
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

    def test_qualified_refs_are_counted(self, temp_project):
        """A file whose only refs are qualified is no longer invisible."""
        temp_project = temp_project.resolve()
        self._write(
            temp_project,
            "qualified.py",
            "# Chunk: pybusiness::docs/chunks/commitment_key - Key\n"
            "# Subsystem: acme/platform::docs/subsystems/baseline - Baseline\n",
        )

        results = count_backreferences(temp_project)

        assert len(results) == 1
        info = results[0]
        assert info.chunk_refs == ["commitment_key"]
        assert info.subsystem_refs == ["baseline"]
        assert info.total_chunk_count == 1

    def test_qualifier_is_carried_per_reference(self, temp_project):
        """BackreferenceInfo exposes the qualifier, not just the bare id."""
        temp_project = temp_project.resolve()
        self._write(
            temp_project,
            "mixed.py",
            "# Chunk: docs/chunks/local_one - Local\n"
            "# Chunk: pybusiness::docs/chunks/foreign_one - Foreign\n",
        )

        results = count_backreferences(temp_project)

        info = results[0]
        assert [(r.artifact_id, r.qualifier) for r in info.chunk_references] == [
            ("local_one", None),
            ("foreign_one", "pybusiness"),
        ]

    def test_malformed_refs_are_visible_but_not_treated_as_local_ids(self, temp_project):
        """A legacy prefix ref is reported without polluting the bare id list."""
        temp_project = temp_project.resolve()
        self._write(
            temp_project,
            "legacy.py",
            "# Chunk: architecture/docs/chunks/smsp_commitment_key - Key\n",
        )

        results = count_backreferences(temp_project)

        assert len(results) == 1, "the file must be reported at all"
        info = results[0]
        assert info.chunk_refs == [], "malformed refs are not local chunk ids"
        assert len(info.chunk_references) == 1
        assert info.chunk_references[0].qualifier_kind == QualifierKind.MALFORMED
        assert info.chunk_references[0].line_number == 1


class TestUpdateBackreferencesQualifiers:
    """Consolidation rewrites round-trip qualifiers.

    Success criterion: "update_backreferences round-trips qualified refs
    without dropping the qualifier".
    """

    def test_member_qualifier_is_preserved_in_narrative_ref(self, temp_project):
        """A member-qualified chunk ref becomes a member-qualified narrative ref."""
        src = temp_project / "mod.py"
        src.write_text(
            '"""Module."""\n'
            "# Chunk: pybusiness::docs/chunks/chunk_a - Chunk A\n"
            "\n"
            "def foo():\n"
            "    pass\n"
        )

        count = update_backreferences(
            temp_project,
            file_path=src,
            chunk_ids_to_replace=["chunk_a"],
            narrative_id="fed",
            narrative_description="Federation",
        )

        assert count == 1
        content = src.read_text()
        assert "# Narrative: pybusiness::docs/narratives/fed - Federation" in content
        assert "docs/chunks/chunk_a" not in content

    def test_repo_qualifier_is_preserved_in_narrative_ref(self, temp_project):
        """An org/repo-qualified ref keeps its org/repo qualifier."""
        src = temp_project / "mod.py"
        src.write_text("# Chunk: acme/platform::docs/chunks/chunk_a - Chunk A\n")

        update_backreferences(
            temp_project,
            file_path=src,
            chunk_ids_to_replace=["chunk_a"],
            narrative_id="fed",
            narrative_description="Federation",
        )

        assert "# Narrative: acme/platform::docs/narratives/fed - Federation" in src.read_text()

    def test_distinct_qualifiers_get_distinct_narrative_lines(self, temp_project):
        """Refs under different qualifiers cannot collapse into one line."""
        src = temp_project / "mod.py"
        src.write_text(
            "# Chunk: docs/chunks/chunk_a - Chunk A\n"
            "# Chunk: pybusiness::docs/chunks/chunk_b - Chunk B\n"
            "# Chunk: pybusiness::docs/chunks/chunk_a - Chunk A elsewhere\n"
        )

        count = update_backreferences(
            temp_project,
            file_path=src,
            chunk_ids_to_replace=["chunk_a", "chunk_b"],
            narrative_id="fed",
            narrative_description="Federation",
        )

        assert count == 3
        narrative_lines = [
            line for line in src.read_text().split("\n") if line.startswith("# Narrative:")
        ]
        assert narrative_lines == [
            "# Narrative: docs/narratives/fed - Federation",
            "# Narrative: pybusiness::docs/narratives/fed - Federation",
        ]

    def test_malformed_refs_are_left_untouched(self, temp_project):
        """A legacy prefix ref is not rewritten - normalization comes first."""
        src = temp_project / "mod.py"
        original = "# Chunk: architecture/docs/chunks/chunk_a - Chunk A\n"
        src.write_text(original)

        count = update_backreferences(
            temp_project,
            file_path=src,
            chunk_ids_to_replace=["chunk_a"],
            narrative_id="fed",
            narrative_description="Federation",
        )

        assert count == 0
        assert src.read_text() == original


# Chunk: docs/chunks/backref_indented_comments - Grammar and rewrite at depth
class TestIndentedBackreferences:
    """Indentation is free; everything else about the grammar stays strict."""

    @pytest.mark.parametrize(
        "indent",
        ["", "    ", "\t", "\t\t", " " * 16],
        ids=["column0", "spaces4", "tab", "tabs2", "deep"],
    )
    def test_reference_parses_at_any_indentation(self, indent):
        parsed = parse_backreference(f"{indent}# Chunk: docs/chunks/widget")

        assert parsed is not None
        assert parsed.artifact_id == "widget"
        assert parsed.indent == indent

    def test_indentation_does_not_leak_into_the_reference(self):
        parsed = parse_backreference("    # Chunk: pybusiness::docs/chunks/widget")

        assert parsed is not None
        assert parsed.reference == "pybusiness::docs/chunks/widget"
        assert parsed.qualifier == "pybusiness"

    @pytest.mark.parametrize(
        "line",
        [
            "#Chunk: docs/chunks/widget",
            "# Chunk:docs/chunks/widget",
            "x = 1  # Chunk: docs/chunks/widget",
        ],
        ids=["no_space_after_hash", "no_space_after_colon", "trailing_after_code"],
    )
    def test_strictness_survives_the_widening(self, line):
        """Widening indentation must not widen anything else."""
        assert parse_backreference(line) is None

    def test_reference_may_not_span_lines(self):
        """`[ \\t]` rather than `\\s`: a reference is exactly one line."""
        assert scan_backreferences("#\nChunk: docs/chunks/widget") == []
        assert scan_backreferences("# Chunk:\ndocs/chunks/widget") == []

    def test_scan_reports_the_line_the_reference_is_on(self):
        refs = scan_backreferences(
            "class Widget:\n    # Chunk: docs/chunks/widget\n    pass\n"
        )

        assert [r.line_number for r in refs] == [2]
        assert refs[0].indent == "    "


# Chunk: docs/chunks/backref_indented_comments - Rewrites preserve indentation
class TestRewritePreservesIndentation:
    def test_interior_reference_is_rewritten_in_place(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class Widget:\n"
            "    # Chunk: docs/chunks/alpha - inside\n"
            "    def method(self):\n"
            "        # Chunk: docs/chunks/alpha - deeper\n"
            "        return 1\n"
        )

        count = update_backreferences(
            tmp_path,
            file_path=src,
            chunk_ids_to_replace=["alpha"],
            narrative_id="story",
            narrative_description="Story",
        )

        assert count == 2
        assert src.read_text() == (
            "class Widget:\n"
            "    # Narrative: docs/narratives/story - Story\n"
            "    def method(self):\n"
            "        # Narrative: docs/narratives/story - Story\n"
            "        return 1\n"
        )

    def test_same_column_references_still_collapse(self, tmp_path):
        """Clutter reduction survives: one line per (qualifier, column)."""
        src = tmp_path / "mod.py"
        src.write_text(
            "    # Chunk: docs/chunks/alpha - one\n"
            "    # Chunk: docs/chunks/beta - two\n"
        )

        count = update_backreferences(
            tmp_path,
            file_path=src,
            chunk_ids_to_replace=["alpha", "beta"],
            narrative_id="story",
            narrative_description="Story",
        )

        assert count == 2
        assert src.read_text() == "    # Narrative: docs/narratives/story - Story\n"
