"""Harvest and scrape operations over the Firecrawl API."""

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from dr_cognee.models import HarvestSpec, QuerySpec, SourceCategory, SourceRecord, SourceStatus
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.workspace import Workspace

SCRAPE_FORMATS = ["markdown"]


class SearchClient(Protocol):
    def search(self, query: str, **kwargs: Any) -> Any: ...

    def scrape(self, url: str, **kwargs: Any) -> Any: ...


class HarvestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new: int = 0
    seen: int = 0
    errors: list[str] = []


def _hit_category(hit: dict[str, Any], kind: str) -> SourceCategory:
    raw = hit.get("category")
    if raw:
        try:
            return SourceCategory(raw)
        except ValueError:
            pass
    return SourceCategory.NEWS if kind == "news" else SourceCategory.WEB


def search_hits_to_records(
    hits: list[dict[str, Any]], kind: str, query: QuerySpec
) -> list[SourceRecord]:
    records = []
    for hit in hits:
        url = hit.get("url")
        if not url:
            continue
        records.append(
            SourceRecord(
                id=source_id(url),
                url=url,
                title=hit.get("title") or url,
                category=_hit_category(hit, kind),
                found_via=f"{query.query} [{kind}]",
                published=hit.get("date"),
            )
        )
    return records


def harvest(store: SourceStore, spec: HarvestSpec, client: SearchClient) -> HarvestResult:
    result = HarvestResult()
    for query in spec.queries:
        try:
            data = client.search(
                query.query,
                sources=query.sources,
                categories=[c.value for c in query.categories] or None,
                tbs=query.tbs,
                limit=query.limit,
            )
        except Exception as e:  # noqa: BLE001 - batch continues past per-query failures
            result.errors.append(f"{query.query}: {e}")
            continue
        for kind in ("web", "news"):
            items = getattr(data, kind, None) or []
            hits = [item.model_dump() for item in items]
            records = search_hits_to_records(hits, kind, query)
            new_records = store.append_new(records)
            result.new += len(new_records)
            result.seen += len(records) - len(new_records)
    return result


def scrape(
    store: SourceStore, workspace: Workspace, ids: list[str], client: SearchClient
) -> list[SourceRecord]:
    records = store.load()
    updated = []
    for sid in ids:
        record = records.get(sid)
        if record is None:
            continue
        try:
            document = client.scrape(record.url, formats=SCRAPE_FORMATS, only_main_content=True)
            markdown = document.markdown or ""
            if not markdown.strip():
                raise ValueError("empty markdown content")
            workspace.content_path(record.id).write_text(markdown)
            record.status = SourceStatus.SCRAPED
            record.error = None
        except Exception as e:  # noqa: BLE001 - batch continues past per-source failures
            record.error = f"scrape failed: {e}"
        store.update(record)
        updated.append(record)
    return updated
