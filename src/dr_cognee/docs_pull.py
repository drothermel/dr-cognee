"""Pull tool docs directly — llms.txt manifests and GitHub repo docs — into the workspace.

First-pass doc gathering that avoids the Firecrawl API: llms.txt manifests and git
sparse checkouts are parsed locally via the vendored dr-notion mirror modules.
"""

from pydantic import BaseModel, ConfigDict

from dr_cognee.models import SourceCategory, SourceRecord, SourceStatus
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.vendored.github_docs_mirror import mirror_github_docs
from dr_cognee.vendored.llms_mirror import MirrorStatus, mirror_manifest
from dr_cognee.workspace import Workspace

MIRROR_DIR = "mirror"
LLMS_MIRROR_SUBDIR = "llms"
GITHUB_MIRROR_SUBDIR = "github"
GITHUB_CHECKOUT_SUBDIR = "checkout"


class DocsPullResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new: int = 0
    seen: int = 0
    failed: list[str] = []


def _register_doc(
    store: SourceStore,
    workspace: Workspace,
    url: str,
    title: str,
    content: str,
    found_via: str,
    result: DocsPullResult,
) -> None:
    record = SourceRecord(
        id=source_id(url),
        url=url,
        title=title,
        category=SourceCategory.DOCS,
        found_via=found_via,
        status=SourceStatus.SCRAPED,
    )
    added = store.append_new([record])
    if not added:
        result.seen += 1
        return
    workspace.content_path(record.id).write_text(content)
    result.new += 1


def pull_llms_docs(
    store: SourceStore, workspace: Workspace, manifest_url: str
) -> DocsPullResult:
    result = DocsPullResult()
    mirror_root = workspace.root / MIRROR_DIR / LLMS_MIRROR_SUBDIR
    summary = mirror_manifest(manifest_url, mirror_root, force=True)
    downloaded_by_url = {
        r.url: r
        for r in summary.results
        if r.status in (MirrorStatus.DOWNLOADED, MirrorStatus.SKIPPED_EXISTING)
    }
    for document in summary.documents:
        download = downloaded_by_url.get(document.url)
        if download is None or not download.output_path.exists():
            result.failed.append(f"{document.url}: not downloaded")
            continue
        _register_doc(
            store,
            workspace,
            url=document.url,
            title=document.title,
            content=download.output_path.read_text(),
            found_via=f"llms.txt [{manifest_url}]",
            result=result,
        )
    for download in summary.results:
        if download.status == MirrorStatus.FAILED:
            result.failed.append(f"{download.url}: {download.message}")
    return result


def pull_github_docs(
    store: SourceStore, workspace: Workspace, tree_url: str
) -> DocsPullResult:
    result = DocsPullResult()
    mirror_root = workspace.root / MIRROR_DIR / GITHUB_MIRROR_SUBDIR
    checkout_root = workspace.root / MIRROR_DIR / GITHUB_CHECKOUT_SUBDIR
    summary = mirror_github_docs(tree_url, mirror_root, checkout_root, force=True)
    for page in summary.pages:
        _register_doc(
            store,
            workspace,
            url=page.source_url,
            title=page.title,
            content=page.content,
            found_via=f"github docs [{tree_url}]",
            result=result,
        )
    return result
