"""Tests for corpus partitioning: `partition_chunks` and `ve chunk partition`.

# Chunk: docs/chunks/audit_corpus_health - Deterministic corpus partition consumed by the audit-corpus skill

The partition is the substrate the audit-corpus skill fans out over. Its
contract is that an unchanged corpus yields an unchanged assignment, so most of
what is asserted here is *stability* rather than any particular clustering.
"""

import json
import pathlib

import pytest

from ve import cli


def write_chunk(
    project_dir: pathlib.Path,
    name: str,
    status: str = "ACTIVE",
    code_paths: list[str] | None = None,
    code_references: list[str] | None = None,
    body: str = "Test chunk content.",
) -> pathlib.Path:
    """Create a chunk directory with GOAL.md carrying the given references."""
    chunk_dir = project_dir / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    if code_paths:
        paths_yaml = "code_paths:\n" + "\n".join(f"  - {p}" for p in code_paths)
    else:
        paths_yaml = "code_paths: []"

    if code_references:
        ref_lines = ["code_references:"]
        for ref in code_references:
            ref_lines.append(f'  - ref: "{ref}"')
            ref_lines.append('    implements: "test implementation"')
        refs_yaml = "\n".join(ref_lines)
    else:
        refs_yaml = "code_references: []"

    (chunk_dir / "GOAL.md").write_text(
        f"""---
status: {status}
ticket: null
parent_chunk: null
{paths_yaml}
{refs_yaml}
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: []
---

# Chunk Goal

## Minor Goal

{body}
"""
    )
    return chunk_dir


@pytest.fixture
def corpus(tmp_path):
    """A small corpus with a known overlap structure.

    - alpha and beta share src/shared.py (alpha via code_paths, beta via a
      symbolic code_reference) — they must land together.
    - gamma touches only src/lonely.py — it must land apart from alpha/beta.
    - orphan declares neither code_paths nor code_references — it participates
      in no code-overlap edge and must still be accounted for in the output.
    - retired is HISTORICAL — it exists so status filtering has something to
      exclude.
    """
    for sub in ("chunks", "narratives", "investigations", "subsystems"):
        (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

    write_chunk(
        tmp_path,
        "alpha",
        code_paths=["src/shared.py"],
        body="Alpha governs the shared writer path and its buffering rules.",
    )
    write_chunk(
        tmp_path,
        "beta",
        code_references=["src/shared.py#Writer"],
        body="Beta governs the shared writer path and its flush rules.",
    )
    write_chunk(
        tmp_path,
        "gamma",
        code_paths=["src/lonely.py"],
        body="Gamma owns terminal colour selection for progress output.",
    )
    write_chunk(tmp_path, "orphan", body="Orphan declares no code references at all.")
    write_chunk(
        tmp_path,
        "retired",
        status="HISTORICAL",
        code_paths=["src/shared.py"],
        body="Retired once governed the shared writer path.",
    )
    return tmp_path


def run_partition(runner, project_dir, *extra):
    """Invoke `ve chunk partition --json` and return the parsed payload."""
    result = runner.invoke(
        cli,
        ["chunk", "partition", "--json", "--project-dir", str(project_dir), *extra],
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def cluster_containing(clusters, name):
    """Return the member list of the cluster holding `name`, or None."""
    for cluster in clusters:
        if name in cluster["members"]:
            return cluster["members"]
    return None


class TestCodeOverlapRelation:
    """Chunks that touch the same code are grouped; chunks that don't, aren't."""

    def test_chunks_sharing_a_file_land_in_one_cluster(self, runner, corpus):
        payload = run_partition(runner, corpus)
        members = cluster_containing(payload["relations"]["code_overlap"], "alpha")

        assert members is not None, "alpha should belong to a code-overlap cluster"
        assert "beta" in members, (
            "alpha (code_paths: src/shared.py) and beta (code_references: "
            "src/shared.py#Writer) share a file and must cluster together"
        )

    def test_shared_file_is_reported_as_evidence(self, runner, corpus):
        """A finding is only actionable if it names why the chunks are related."""
        payload = run_partition(runner, corpus)
        cluster = next(
            c for c in payload["relations"]["code_overlap"] if "alpha" in c["members"]
        )

        assert "src/shared.py" in cluster["evidence"]

    def test_chunks_sharing_nothing_do_not_cluster(self, runner, corpus):
        payload = run_partition(runner, corpus)
        members = cluster_containing(payload["relations"]["code_overlap"], "alpha")

        assert members is not None
        assert "gamma" not in members, (
            "gamma touches only src/lonely.py and must not join the shared.py cluster"
        )

    def test_reference_less_chunk_is_reported_not_dropped(self, runner, corpus):
        """Silent omission would read as 'audited everything' when it wasn't."""
        payload = run_partition(runner, corpus)
        every_member = {
            name
            for relation in payload["relations"].values()
            for cluster in relation
            for name in cluster["members"]
        }

        assert "orphan" in every_member or "orphan" in payload["unclustered"], (
            "orphan participates in no code-overlap edge, so the partition must "
            "account for it explicitly rather than omitting it"
        )


class TestCoverNotComponents:
    """The overlap relation is a per-file cover, not connected components.

    Components chain transitively — A shares a file with B, B shares a different
    file with C — and on a real corpus that collapses nearly everything into one
    cluster, which is no grouping at all. Measured on this repository before the
    change: 423 of 454 chunks in a single component.
    """

    @pytest.fixture
    def chain(self, tmp_path):
        """A–B share one file; B–C share another; A and C share nothing."""
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        write_chunk(tmp_path, "a", code_paths=["src/one.py"], body="Alpha work here.")
        write_chunk(
            tmp_path, "b", code_paths=["src/one.py", "src/two.py"], body="Bravo work here."
        )
        write_chunk(tmp_path, "c", code_paths=["src/two.py"], body="Charlie work here.")
        return tmp_path

    def test_transitive_sharing_does_not_merge_clusters(self, runner, chain):
        payload = run_partition(runner, chain)

        for cluster in payload["relations"]["code_overlap"]:
            assert not {"a", "c"} <= set(cluster["members"]), (
                "a and c share no file; only a transitive merge through b could "
                "put them in one cluster, and that is what collapses real corpora"
            )

    def test_a_chunk_spanning_files_appears_in_every_cluster(self, runner, chain):
        payload = run_partition(runner, chain)
        holding_b = [
            c for c in payload["relations"]["code_overlap"] if "b" in c["members"]
        ]

        assert len(holding_b) == 2, (
            "b claims two files, so it belongs to both files' clusters — the "
            "overlap relation is an overlapping cover, not a strict partition"
        )
        assert {frozenset(c["members"]) for c in holding_b} == {
            frozenset({"a", "b"}),
            frozenset({"b", "c"}),
        }


class TestHubFileExclusion:
    """Files claimed by many chunks are hubs, not redundancy evidence."""

    @pytest.fixture
    def hub(self, tmp_path):
        """Six chunks all claim src/hub.py; two of them also share src/pair.py."""
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        for index in range(6):
            paths = ["src/hub.py"]
            if index < 2:
                paths.append("src/pair.py")
            write_chunk(
                tmp_path, f"h{index}", code_paths=paths, body=f"Distinct work item {index}."
            )
        return tmp_path

    def test_hub_file_above_the_ceiling_generates_no_cluster(self, runner, hub):
        payload = run_partition(runner, hub, "--fan-in-ceiling", "5")
        hub_clusters = [
            c for c in payload["relations"]["code_overlap"] if "src/hub.py" in c["evidence"]
        ]

        assert hub_clusters == [], (
            "src/hub.py is claimed by 6 chunks, above the ceiling of 5"
        )

    def test_the_skipped_hub_is_reported_not_silently_dropped(self, runner, hub):
        payload = run_partition(runner, hub, "--fan-in-ceiling", "5")

        assert {"path": "src/hub.py", "chunk_count": 6} in payload["high_fan_in_paths"]

    def test_narrower_sharing_survives_the_exclusion(self, runner, hub):
        """Excluding the hub must not cost the genuine two-chunk overlap."""
        payload = run_partition(runner, hub, "--fan-in-ceiling", "5")
        pair = [
            c for c in payload["relations"]["code_overlap"] if "src/pair.py" in c["evidence"]
        ]

        assert len(pair) == 1
        assert pair[0]["members"] == ["h0", "h1"]

    def test_a_generous_ceiling_admits_the_hub(self, runner, hub):
        payload = run_partition(runner, hub, "--fan-in-ceiling", "10")
        hub_clusters = [
            c for c in payload["relations"]["code_overlap"] if "src/hub.py" in c["evidence"]
        ]

        assert len(hub_clusters) == 1
        assert len(hub_clusters[0]["members"]) == 6
        assert payload["high_fan_in_paths"] == []


class TestCrossRepoReferences:
    """A path in another repository is not the local path of the same name."""

    def test_qualified_and_local_paths_do_not_cluster(self, runner, tmp_path):
        """Task and workspace contexts carry `org/repo::path` references, and
        treating those as the local `path` manufactures redundancy findings
        between chunks in different repositories."""
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        write_chunk(
            tmp_path, "here", code_references=["src/foo.py#Bar"], body="Local ownership."
        )
        write_chunk(
            tmp_path,
            "elsewhere",
            code_references=["org/repo::src/foo.py#Bar"],
            body="Ownership in another repository entirely.",
        )

        payload = run_partition(runner, tmp_path)

        for cluster in payload["relations"]["code_overlap"]:
            assert not {"here", "elsewhere"} <= set(cluster["members"]), (
                "src/foo.py and org/repo::src/foo.py are different files"
            )

    def test_two_chunks_in_the_same_foreign_repo_still_cluster(self, runner, tmp_path):
        """Qualifying must not break overlap detection within one repository."""
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        write_chunk(
            tmp_path, "far_a", code_references=["org/repo::src/foo.py#Bar"], body="A."
        )
        write_chunk(
            tmp_path, "far_b", code_references=["org/repo::src/foo.py#Baz"], body="B."
        )

        payload = run_partition(runner, tmp_path)
        members = cluster_containing(payload["relations"]["code_overlap"], "far_a")

        assert members is not None and "far_b" in members


class TestSymbolEvidence:
    """Sharing a symbol is a stronger signal than sharing a file."""

    def test_a_symbol_named_by_two_chunks_appears_in_evidence(self, runner, tmp_path):
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        write_chunk(
            tmp_path, "left", code_references=["src/w.py#Writer"], body="Left owns flushing."
        )
        write_chunk(
            tmp_path, "right", code_references=["src/w.py#Writer"], body="Right owns buffering."
        )

        payload = run_partition(runner, tmp_path)
        cluster = payload["relations"]["code_overlap"][0]

        assert "src/w.py" in cluster["evidence"]
        assert "src/w.py#Writer" in cluster["evidence"], (
            "both chunks name the same symbol, which is a much stronger "
            "redundancy signal than merely sharing the file"
        )


class TestDeterminism:
    """The same corpus must yield the same assignment, run to run."""

    def test_repeated_runs_produce_identical_output(self, runner, corpus):
        first = runner.invoke(
            cli, ["chunk", "partition", "--json", "--project-dir", str(corpus)]
        )
        second = runner.invoke(
            cli, ["chunk", "partition", "--json", "--project-dir", str(corpus)]
        )

        assert first.exit_code == 0 and second.exit_code == 0
        assert first.output == second.output

    def test_members_and_evidence_are_sorted(self, runner, corpus):
        """Sorting is what makes byte-identical output survive filesystem order."""
        payload = run_partition(runner, corpus)

        for relation in payload["relations"].values():
            for cluster in relation:
                assert cluster["members"] == sorted(cluster["members"])
                assert cluster.get("evidence", []) == sorted(cluster.get("evidence", []))
        assert payload["unclustered"] == sorted(payload["unclustered"])

    def test_directory_order_does_not_change_assignment(self, runner, corpus, tmp_path):
        """A corpus rebuilt in a different creation order partitions the same."""
        mirror = tmp_path / "mirror"
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (mirror / "docs" / sub).mkdir(parents=True, exist_ok=True)

        # Same five chunks, created in reverse order.
        write_chunk(
            mirror,
            "retired",
            status="HISTORICAL",
            code_paths=["src/shared.py"],
            body="Retired once governed the shared writer path.",
        )
        write_chunk(mirror, "orphan", body="Orphan declares no code references at all.")
        write_chunk(
            mirror,
            "gamma",
            code_paths=["src/lonely.py"],
            body="Gamma owns terminal colour selection for progress output.",
        )
        write_chunk(
            mirror,
            "beta",
            code_references=["src/shared.py#Writer"],
            body="Beta governs the shared writer path and its flush rules.",
        )
        write_chunk(
            mirror,
            "alpha",
            code_paths=["src/shared.py"],
            body="Alpha governs the shared writer path and its buffering rules.",
        )

        assert run_partition(runner, corpus) == run_partition(runner, mirror)


class TestStatusFiltering:
    """Scope selection matches `ve chunk list`, so operators can narrow a run."""

    def test_active_only_excludes_historical_chunks(self, runner, corpus):
        payload = run_partition(runner, corpus, "--active")
        every_name = {
            name
            for relation in payload["relations"].values()
            for cluster in relation
            for name in cluster["members"]
        } | set(payload["unclustered"])

        assert "retired" not in every_name
        assert "alpha" in every_name

    def test_historical_is_reachable_by_explicit_status(self, runner, corpus):
        payload = run_partition(runner, corpus, "--status", "HISTORICAL")
        every_name = {
            name
            for relation in payload["relations"].values()
            for cluster in relation
            for name in cluster["members"]
        } | set(payload["unclustered"])

        assert every_name == {"retired"}

    def test_invalid_status_is_rejected(self, runner, corpus):
        result = runner.invoke(
            cli,
            ["chunk", "partition", "--project-dir", str(corpus), "--status", "BOGUS"],
        )

        assert result.exit_code != 0


class TestContentSimilarityRelation:
    """The similarity half stays consistent with `ve chunk cluster`."""

    def test_min_similarity_defaults_to_the_cluster_command_default(self, runner):
        result = runner.invoke(cli, ["chunk", "partition", "--help"])

        assert result.exit_code == 0
        assert "0.3" in result.output, (
            "--min-similarity must document the same 0.3 default as `ve chunk cluster`"
        )

    def test_similarity_clusters_carry_a_score(self, runner, corpus):
        """A similarity finding without its score can't be triaged."""
        payload = run_partition(runner, corpus, "--min-similarity", "0.05")
        similarity = payload["relations"]["content_similarity"]

        if similarity:
            assert all("score" in cluster for cluster in similarity)


class TestEmptyCorpus:
    """Boundary: a project with no chunks partitions to nothing, not an error."""

    def test_empty_corpus_yields_empty_relations(self, runner, tmp_path):
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (tmp_path / "docs" / sub).mkdir(parents=True, exist_ok=True)

        payload = run_partition(runner, tmp_path)

        assert payload["relations"]["code_overlap"] == []
        assert payload["relations"]["content_similarity"] == []
        assert payload["unclustered"] == []
