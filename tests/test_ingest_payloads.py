from pathlib import Path

import pytest

from dr_cognee.cognee_client import CogneeCreditsError
from dr_cognee.ingest import build_payloads, ingest_workspace, render_distilled
from dr_cognee.models import (
    DistilledRecord,
    Relevance,
    SourceCategory,
    SourceRecord,
    SourceStatus,
    TopicConfig,
)
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.workspace import Workspace

DISTILLED = DistilledRecord(
    source_id="x",
    takeaways=["takeaway one"],
    entities=["Graphiti"],
    claims_of_use=["used at Zep"],
    relevance=Relevance.HIGH,
    depth_flag=True,
    depth_note="full docs",
    distilled_at="2026-07-07T00:00:00Z",
)


class StubCogneeClient:
    def __init__(self, out_of_credits: bool = False) -> None:
        self.added: list[tuple[str, list[str], list[str] | None]] = []
        self.cognified = 0
        self.out_of_credits = out_of_credits

    def ensure_dataset(self, name: str) -> str:
        return "ds-1"

    def add_text(self, dataset_id: str, texts: list[str], node_set=None) -> None:
        self.added.append((dataset_id, texts, node_set))

    def cognify(self, dataset_id: str, background: bool = True) -> dict:
        if self.out_of_credits:
            raise CogneeCreditsError("Only $6.45 of credits remain.")
        self.cognified += 1
        return {}

    def wait_for_cognify(self, dataset_id: str, timeout_s: float = 900.0, poll_s: float = 10.0) -> str:
        return "DATASET_PROCESSING_COMPLETED"


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    config = TopicConfig(
        topic="t", slug="t", question="q?", facets=["f"], dataset_name="t-ds",
        created="2026-07-07",
    )
    return Workspace.init(tmp_path / "t", config)


def add_distilled_source(
    workspace: Workspace,
    store: SourceStore,
    url: str,
    relevance: Relevance,
    depth_flag: bool,
    with_content: bool = True,
) -> SourceRecord:
    record = SourceRecord(
        id=source_id(url), url=url, title="T", category=SourceCategory.WEB, found_via="q [web]",
        status=SourceStatus.DISTILLED, relevance=relevance, depth_flag=depth_flag,
    )
    store.append_new([record])
    distilled = DISTILLED.model_copy(update={"source_id": record.id, "relevance": relevance})
    workspace.distilled_path(record.id).write_text(distilled.model_dump_json())
    if with_content:
        workspace.content_path(record.id).write_text("full page content")
    return record


def test_render_distilled_contains_key_fields() -> None:
    record = SourceRecord(
        id="x", url="https://a.com", title="A Tool", category=SourceCategory.WEB,
        found_via="q [web]",
    )
    text = render_distilled(record, DISTILLED)
    assert "https://a.com" in text
    assert "- takeaway one" in text
    assert "used at Zep" in text
    assert "full docs" in text


def test_build_payloads_full_content_only_for_high_depth(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    high = add_distilled_source(workspace, store, "https://a.com/high", Relevance.HIGH, True)
    add_distilled_source(workspace, store, "https://a.com/med", Relevance.MEDIUM, True)
    add_distilled_source(workspace, store, "https://a.com/flat", Relevance.HIGH, False)
    keys = [item.key for item in build_payloads(workspace, store)]
    assert f"content:{high.id}" in keys
    assert sum(k.startswith("content:") for k in keys) == 1
    assert sum(k.startswith("distilled:") for k in keys) == 3
    assert "log" in keys


def test_build_payloads_includes_synthesis_and_report(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    (workspace.synthesis_dir / "facet-a.md").write_text("synthesis notes")
    workspace.report_file.write_text("final report")
    keys = [item.key for item in build_payloads(workspace, store)]
    assert "synthesis:facet-a" in keys
    assert "report" in keys


def test_ingest_is_idempotent_via_manifest(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    add_distilled_source(workspace, store, "https://a.com/1", Relevance.HIGH, True)
    client = StubCogneeClient()

    first = ingest_workspace(workspace, store, client)
    assert first.pushed == 3  # distilled + content + log
    assert first.skipped == 0
    assert first.cognify_status == "DATASET_PROCESSING_COMPLETED"

    second = ingest_workspace(workspace, store, client)
    assert second.pushed == 0
    assert second.skipped == 3
    assert second.cognify_status == "no changes"
    assert client.cognified == 1


def test_ingest_credits_blocked_keeps_statuses(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    record = add_distilled_source(workspace, store, "https://a.com/1", Relevance.HIGH, True)
    result = ingest_workspace(workspace, store, StubCogneeClient(out_of_credits=True))
    assert result.pushed == 3
    assert result.cognify_status.startswith("blocked:")
    assert store.load()[record.id].status == SourceStatus.DISTILLED


def test_ingest_marks_sources_ingested(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    record = add_distilled_source(workspace, store, "https://a.com/1", Relevance.HIGH, True)
    ingest_workspace(workspace, store, StubCogneeClient())
    assert store.load()[record.id].status == SourceStatus.INGESTED
