from pathlib import Path

import pytest

import dr_cognee.docs_pull as docs_pull
from dr_cognee.docs_pull import pull_github_docs, pull_llms_docs
from dr_cognee.models import SourceCategory, SourceStatus, TopicConfig
from dr_cognee.sources import SourceStore
from dr_cognee.vendored.github_docs_mirror import (
    GitDocsMirrorSummary,
    GitHubDocsSource,
    MarkdownPage,
    WriteResult,
)
from dr_cognee.vendored.llms_mirror import (
    DownloadResult,
    MarkdownDocument,
    MirrorStatus,
    MirrorSummary,
)


@pytest.fixture
def workspace(tmp_path: Path):
    from dr_cognee.workspace import Workspace

    config = TopicConfig(
        topic="pydantic", slug="pydantic", question="what can pydantic do?",
        facets=["docs"], dataset_name="pydantic", created="2026-07-07",
    )
    return Workspace.init(tmp_path / "pydantic", config)


def llms_summary(tmp_path: Path, fail_second: bool = False) -> MirrorSummary:
    doc_a = tmp_path / "a.md"
    doc_a.write_text("# Doc A")
    results = [
        DownloadResult(
            url="https://docs.example.dev/a.md", output_path=doc_a,
            status=MirrorStatus.DOWNLOADED,
        ),
        DownloadResult(
            url="https://docs.example.dev/b.md", output_path=tmp_path / "b.md",
            status=MirrorStatus.FAILED if fail_second else MirrorStatus.DOWNLOADED,
            message="404" if fail_second else None,
        ),
    ]
    if not fail_second:
        (tmp_path / "b.md").write_text("# Doc B")
    return MirrorSummary(
        manifest_url="https://docs.example.dev/llms.txt",
        output_root=tmp_path,
        manifest_result=DownloadResult(
            url="https://docs.example.dev/llms.txt", output_path=tmp_path / "llms.txt",
            status=MirrorStatus.DOWNLOADED,
        ),
        documents=[
            MarkdownDocument(title="Doc A", url="https://docs.example.dev/a.md", output_path=doc_a),
            MarkdownDocument(
                title="Doc B", url="https://docs.example.dev/b.md", output_path=tmp_path / "b.md"
            ),
        ],
        skipped_links=[],
        results=results,
    )


def test_pull_llms_docs_registers_scraped_docs(
    workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        docs_pull, "mirror_manifest", lambda url, root, **kw: llms_summary(tmp_path)
    )
    store = SourceStore(workspace.sources_file)
    result = pull_llms_docs(store, workspace, "https://docs.example.dev/llms.txt")
    assert result.new == 2
    assert not result.failed
    records = list(store.load().values())
    assert all(r.category == SourceCategory.DOCS for r in records)
    assert all(r.status == SourceStatus.SCRAPED for r in records)
    assert workspace.content_path(records[0].id).read_text() == "# Doc A"


def test_pull_llms_docs_reports_failures_and_dedups(
    workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        docs_pull,
        "mirror_manifest",
        lambda url, root, **kw: llms_summary(tmp_path, fail_second=True),
    )
    store = SourceStore(workspace.sources_file)
    result = pull_llms_docs(store, workspace, "https://docs.example.dev/llms.txt")
    assert result.new == 1
    assert len(result.failed) == 2  # not-downloaded doc + failed download entry
    again = pull_llms_docs(store, workspace, "https://docs.example.dev/llms.txt")
    assert again.new == 0
    assert again.seen == 1


def github_summary(tmp_path: Path) -> GitDocsMirrorSummary:
    return GitDocsMirrorSummary(
        source=GitHubDocsSource(owner="o", repo="r", ref="main", docs_path="docs"),
        commit="abc123",
        checkout_path=tmp_path / "checkout",
        output_path=tmp_path / "out",
        pages=[
            MarkdownPage(
                title="Usage",
                source_path="docs/usage.md",
                output_path=tmp_path / "out" / "usage.md",
                relative_output_path="usage.md",
                source_url="https://github.com/o/r/blob/main/docs/usage.md",
                nav_path=["Usage"],
                api_references=[],
                content="# Usage docs",
            )
        ],
        manifest_result=WriteResult(
            output_path=tmp_path / "out" / "manifest.json", status="written"
        ),
        results=[],
    )


def test_pull_github_docs_registers_pages(
    workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        docs_pull, "mirror_github_docs", lambda url, root, co, **kw: github_summary(tmp_path)
    )
    store = SourceStore(workspace.sources_file)
    result = pull_github_docs(store, workspace, "https://github.com/o/r/tree/main/docs")
    assert result.new == 1
    record = next(iter(store.load().values()))
    assert record.category == SourceCategory.DOCS
    assert record.found_via.startswith("github docs")
    assert workspace.content_path(record.id).read_text() == "# Usage docs"
