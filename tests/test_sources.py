from pathlib import Path

import pytest

from dr_cognee.models import SourceCategory, SourceRecord, SourceStatus
from dr_cognee.sources import SourceStore, normalize_url, source_id


def make_record(url: str, title: str = "t") -> SourceRecord:
    return SourceRecord(
        id=source_id(url),
        url=url,
        title=title,
        category=SourceCategory.WEB,
        found_via="test query [web]",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://Example.com/x/?utm_source=hn#frag", "https://example.com/x"),
        ("https://example.com/x", "https://example.com/x"),
        ("https://example.com/x?ref=news&keep=1", "https://example.com/x?keep=1"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert normalize_url(raw) == expected


def test_source_id_stable_across_variants() -> None:
    assert source_id("https://Example.com/x/?utm_source=hn") == source_id(
        "https://example.com/x"
    )


def test_append_new_dedups(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")
    first = store.append_new([make_record("https://a.com/1"), make_record("https://a.com/2")])
    assert len(first) == 2
    second = store.append_new([make_record("https://a.com/1"), make_record("https://a.com/3")])
    assert [r.url for r in second] == ["https://a.com/3"]
    assert len(store.load()) == 3


def test_update_persists_status_change(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")
    record = make_record("https://a.com/1")
    store.append_new([record])
    record.status = SourceStatus.SCRAPED
    store.update(record)
    assert store.load()[record.id].status == SourceStatus.SCRAPED
    assert store.pending(SourceStatus.SCRAPED) == [record]


def test_update_unknown_id_raises(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")
    with pytest.raises(KeyError):
        store.update(make_record("https://a.com/1"))


def test_counts(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.jsonl")
    store.append_new([make_record("https://a.com/1"), make_record("https://a.com/2")])
    counts = store.counts()
    assert counts[SourceStatus.FOUND] == 2
    assert counts[SourceStatus.SCRAPED] == 0
