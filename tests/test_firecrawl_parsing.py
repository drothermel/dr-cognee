from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import TypeAdapter

from dr_cognee.firecrawl_ops import harvest, scrape, search_hits_to_records
from dr_cognee.models import (
    HarvestSpec,
    QuerySpec,
    SourceCategory,
    SourceStatus,
    TopicConfig,
)
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.workspace import Workspace

FIXTURE = TypeAdapter(dict[str, Any]).validate_json(
    (Path(__file__).parent / "fixtures" / "firecrawl_search.json").read_text()
)
QUERY = QuerySpec(query="knowledge graph memory for AI agents", sources=["web", "news"])


class StubItem:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class StubSearchClient:
    def __init__(self, fixture: dict[str, Any], scrape_markdown: str | None = "# Content") -> None:
        self.fixture = fixture
        self.scrape_markdown = scrape_markdown

    def search(self, query: str, **kwargs: Any) -> Any:
        return SimpleNamespace(
            web=[StubItem(h) for h in self.fixture.get("web") or []],
            news=[StubItem(h) for h in self.fixture.get("news") or []],
        )

    def scrape(self, url: str, **kwargs: Any) -> Any:
        if self.scrape_markdown is None:
            raise RuntimeError("scrape blew up")
        return SimpleNamespace(markdown=self.scrape_markdown)


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    config = TopicConfig(
        topic="t", slug="t", question="q?", facets=["f"], dataset_name="t", created="2026-07-07"
    )
    return Workspace.init(tmp_path / "t", config)


def test_web_hits_map_to_records() -> None:
    records = search_hits_to_records(FIXTURE["web"], "web", QUERY)
    assert len(records) == 3
    assert records[0].category == SourceCategory.WEB
    assert records[0].found_via == "knowledge graph memory for AI agents [web]"
    assert records[0].published is None


def test_news_hits_carry_published_date() -> None:
    records = search_hits_to_records(FIXTURE["news"], "news", QUERY)
    assert all(r.category == SourceCategory.NEWS for r in records)
    assert records[0].published == "1 month ago"


def test_harvest_dedups_across_queries(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")
    spec = HarvestSpec(queries=[QUERY, QUERY])
    result = harvest(store, spec, StubSearchClient(FIXTURE))
    assert result.new == 6
    assert result.seen == 6
    assert not result.errors


def test_harvest_continues_past_query_failure(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")

    class FailingClient(StubSearchClient):
        def search(self, query: str, **kwargs: Any) -> Any:
            if query == "boom":
                raise RuntimeError("api down")
            return super().search(query, **kwargs)

    spec = HarvestSpec(queries=[QuerySpec(query="boom"), QUERY])
    result = harvest(store, spec, FailingClient(FIXTURE))
    assert result.new == 6
    assert len(result.errors) == 1


def test_scrape_writes_content_and_updates_status(tmp_path: Path, workspace: Workspace) -> None:
    store = SourceStore(workspace.sources_file)
    records = store.append_new(search_hits_to_records(FIXTURE["web"], "web", QUERY))
    updated = scrape(store, workspace, [records[0].id], StubSearchClient(FIXTURE))
    assert updated[0].status == SourceStatus.SCRAPED
    assert workspace.content_path(records[0].id).read_text() == "# Content"


def test_scrape_failure_records_error_and_continues(
    tmp_path: Path, workspace: Workspace
) -> None:
    store = SourceStore(workspace.sources_file)
    records = store.append_new(search_hits_to_records(FIXTURE["web"], "web", QUERY))
    ids = [records[0].id, records[1].id]
    updated = scrape(store, workspace, ids, StubSearchClient(FIXTURE, scrape_markdown=None))
    assert len(updated) == 2
    assert all(r.status == SourceStatus.FOUND for r in updated)
    assert all(r.error and "scrape failed" in r.error for r in updated)


def test_source_id_matches_between_fixture_and_store() -> None:
    url = FIXTURE["web"][0]["url"]
    records = search_hits_to_records(FIXTURE["web"], "web", QUERY)
    assert records[0].id == source_id(url)
