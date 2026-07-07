from pathlib import Path

import pytest

from dr_cognee.distill import (
    DistillOutput,
    build_distill_prompt,
    distill_pending,
    to_distilled_record,
)
from dr_cognee.models import (
    Relevance,
    SourceCategory,
    SourceRecord,
    SourceStatus,
    TopicConfig,
)
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.workspace import Workspace

OUTPUT = DistillOutput(
    takeaways=["Graphiti supports incremental graph updates"],
    entities=["Graphiti", "Zep"],
    claims_of_use=["Used in Zep's production memory layer"],
    relevance=Relevance.HIGH,
    depth_flag=True,
    depth_note="Full docs cover temporal edges",
)


class StubDistillClient:
    def __init__(self, output: DistillOutput | None = OUTPUT) -> None:
        self.output = output
        self.calls = 0

    def distill(self, prompt: str) -> DistillOutput:
        self.calls += 1
        if self.output is None:
            raise ValueError("distill blew up")
        return self.output


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    config = TopicConfig(
        topic="t", slug="t", question="which tool?", facets=["f"], dataset_name="t",
        created="2026-07-07",
    )
    return Workspace.init(tmp_path / "t", config)


def scraped_record(workspace: Workspace, store: SourceStore, url: str) -> SourceRecord:
    record = SourceRecord(
        id=source_id(url), url=url, title="T", category=SourceCategory.WEB, found_via="q [web]",
        status=SourceStatus.SCRAPED,
    )
    store.append_new([record])
    workspace.content_path(record.id).write_text("some content")
    return record


def test_to_distilled_record_carries_fields() -> None:
    record = to_distilled_record("abc", OUTPUT, "2026-07-07T00:00:00Z")
    assert record.source_id == "abc"
    assert record.relevance == Relevance.HIGH
    assert record.claims_of_use == ["Used in Zep's production memory layer"]


def test_prompt_truncates_content() -> None:
    prompt = build_distill_prompt("q?", "T", "https://a.com", "x" * 100_000)
    assert len(prompt) < 70_000


def test_distill_pending_writes_record_and_updates_source(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    record = scraped_record(workspace, store, "https://a.com/1")
    result = distill_pending(store, workspace, StubDistillClient())
    assert result.distilled == 1
    assert workspace.distilled_path(record.id).exists()
    updated = store.load()[record.id]
    assert updated.status == SourceStatus.DISTILLED
    assert updated.relevance == Relevance.HIGH
    assert updated.depth_flag is True


def test_distill_failure_keeps_source_scraped(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    record = scraped_record(workspace, store, "https://a.com/1")
    result = distill_pending(store, workspace, StubDistillClient(output=None))
    assert result.distilled == 0
    assert len(result.failed) == 1
    assert store.load()[record.id].status == SourceStatus.SCRAPED


def test_distill_skips_missing_content(workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    record = scraped_record(workspace, store, "https://a.com/1")
    workspace.content_path(record.id).unlink()
    client = StubDistillClient()
    result = distill_pending(store, workspace, client)
    assert client.calls == 0
    assert result.failed == [f"{record.id}: missing content file"]
