# Vendored from dr-notion@4117b4e (src/dr_notion/llms_mirror.py) - keep edits upstream.
from __future__ import annotations

import re
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

ENCODING = "utf-8"
MARKDOWN_EXTENSION = ".md"
MANIFEST_FILENAME = "llms.txt"
MARKDOWN_LIST_LINK_PATTERN = re.compile(
    r"^\s*[-*+]\s+\[([^\]]+)\]\(([^)\s]+)(?:\s+[^)]*)?\)",
    re.MULTILINE,
)
REQUEST_USER_AGENT = "dr-notion-llms-mirror/0.1"
TEMP_FILE_PREFIX = ".download-"


class LinkSkipReason(StrEnum):
    NOT_MARKDOWN = "not_markdown"
    OFF_ORIGIN = "off_origin"
    UNSAFE_PATH = "unsafe_path"


class MirrorStatus(StrEnum):
    DOWNLOADED = "downloaded"
    DRY_RUN = "dry_run"
    FAILED = "failed"
    SKIPPED_EXISTING = "skipped_existing"


class MarkdownDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    url: str
    output_path: Path


class SkippedLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    url: str
    reason: LinkSkipReason


class DownloadResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    output_path: Path
    status: MirrorStatus
    message: str | None = None


class MirrorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_url: str
    output_root: Path
    manifest_result: DownloadResult
    documents: list[MarkdownDocument]
    skipped_links: list[SkippedLink]
    results: list[DownloadResult]

    def all_results(self) -> list[DownloadResult]:
        return [self.manifest_result, *self.results]

    def count_results(self, status: MirrorStatus) -> int:
        return sum(result.status == status for result in self.all_results())

    def count_skipped_links(self, reason: LinkSkipReason) -> int:
        return sum(skipped.reason == reason for skipped in self.skipped_links)


FetchText = Callable[[str, float], str]


def fetch_text(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": REQUEST_USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode(ENCODING)
    except HTTPError:
        raise
    except URLError as error:
        raise RuntimeError(f"Failed to fetch {url}: {error.reason}") from error


def collect_markdown_documents(
    manifest_url: str,
    manifest_text: str,
    output_root: Path,
    *,
    allow_off_origin: bool = False,
) -> tuple[list[MarkdownDocument], list[SkippedLink]]:
    manifest_origin = _url_origin(urlparse(manifest_url))
    documents: list[MarkdownDocument] = []
    skipped_links: list[SkippedLink] = []

    for title, raw_url in MARKDOWN_LIST_LINK_PATTERN.findall(manifest_text):
        resolved_url = _resolve_url(manifest_url, raw_url)
        parsed_url = urlparse(resolved_url)

        if not parsed_url.path.endswith(MARKDOWN_EXTENSION):
            skipped_links.append(
                SkippedLink(
                    title=title,
                    url=resolved_url,
                    reason=LinkSkipReason.NOT_MARKDOWN,
                )
            )
            continue

        if not allow_off_origin and _url_origin(parsed_url) != manifest_origin:
            skipped_links.append(
                SkippedLink(
                    title=title,
                    url=resolved_url,
                    reason=LinkSkipReason.OFF_ORIGIN,
                )
            )
            continue

        try:
            output_path = document_output_path(parsed_url, output_root)
        except ValueError:
            skipped_links.append(
                SkippedLink(
                    title=title,
                    url=resolved_url,
                    reason=LinkSkipReason.UNSAFE_PATH,
                )
            )
            continue

        documents.append(
            MarkdownDocument(
                title=title,
                url=resolved_url,
                output_path=output_path,
            )
        )

    return documents, skipped_links


def document_output_path(parsed_url: ParseResult, output_root: Path) -> Path:
    if not parsed_url.netloc:
        raise ValueError("Document URL must include a host")

    path_parts = [part for part in parsed_url.path.split("/") if part]
    if not path_parts:
        raise ValueError("Document URL must include a file path")

    unsafe_parts = {"", ".", ".."}
    if any(part in unsafe_parts for part in path_parts):
        raise ValueError(f"Document URL has an unsafe path: {parsed_url.path}")

    return output_root / parsed_url.netloc / Path(*path_parts)


def manifest_output_path(manifest_url: str, output_root: Path) -> Path:
    parsed_url = urlparse(manifest_url)
    if not parsed_url.netloc:
        raise ValueError("Manifest URL must include a host")

    file_name = Path(parsed_url.path).name
    if file_name != MANIFEST_FILENAME:
        raise ValueError(f"Manifest URL must end with {MANIFEST_FILENAME}")

    return output_root / parsed_url.netloc / MANIFEST_FILENAME


def mirror_manifest(
    manifest_url: str,
    output_root: Path,
    *,
    allow_off_origin: bool = False,
    dry_run: bool = False,
    force: bool = False,
    timeout: float = 20.0,
    fetch: FetchText = fetch_text,
) -> MirrorSummary:
    manifest_text = fetch(manifest_url, timeout)
    manifest_result = mirror_text(
        manifest_url,
        manifest_output_path(manifest_url, output_root),
        manifest_text,
        dry_run=dry_run,
        force=force,
    )
    documents, skipped_links = collect_markdown_documents(
        manifest_url,
        manifest_text,
        output_root,
        allow_off_origin=allow_off_origin,
    )

    results = [
        mirror_document(
            document,
            dry_run=dry_run,
            force=force,
            timeout=timeout,
            fetch=fetch,
        )
        for document in documents
    ]

    return MirrorSummary(
        manifest_url=manifest_url,
        output_root=output_root,
        manifest_result=manifest_result,
        documents=documents,
        skipped_links=skipped_links,
        results=results,
    )


def mirror_document(
    document: MarkdownDocument,
    *,
    dry_run: bool,
    force: bool,
    timeout: float,
    fetch: FetchText,
) -> DownloadResult:
    if dry_run:
        return DownloadResult(
            url=document.url,
            output_path=document.output_path,
            status=MirrorStatus.DRY_RUN,
        )

    if document.output_path.exists() and not force:
        return DownloadResult(
            url=document.url,
            output_path=document.output_path,
            status=MirrorStatus.SKIPPED_EXISTING,
        )

    try:
        content = fetch(document.url, timeout)
        write_text_atomically(document.output_path, content)
    except Exception as error:
        return DownloadResult(
            url=document.url,
            output_path=document.output_path,
            status=MirrorStatus.FAILED,
            message=str(error),
        )

    return DownloadResult(
        url=document.url,
        output_path=document.output_path,
        status=MirrorStatus.DOWNLOADED,
    )


def mirror_text(
    url: str,
    output_path: Path,
    content: str,
    *,
    dry_run: bool,
    force: bool,
) -> DownloadResult:
    if dry_run:
        return DownloadResult(
            url=url,
            output_path=output_path,
            status=MirrorStatus.DRY_RUN,
        )

    if output_path.exists() and not force:
        return DownloadResult(
            url=url,
            output_path=output_path,
            status=MirrorStatus.SKIPPED_EXISTING,
        )

    try:
        write_text_atomically(output_path, content)
    except Exception as error:
        return DownloadResult(
            url=url,
            output_path=output_path,
            status=MirrorStatus.FAILED,
            message=str(error),
        )

    return DownloadResult(
        url=url,
        output_path=output_path,
        status=MirrorStatus.DOWNLOADED,
    )


def write_text_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding=ENCODING,
        dir=path.parent,
        prefix=TEMP_FILE_PREFIX,
        delete=False,
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    temp_path.replace(path)


def _resolve_url(manifest_url: str, raw_url: str) -> str:
    return urldefrag(urljoin(manifest_url, raw_url.strip()))[0]


def _url_origin(parsed_url: ParseResult) -> tuple[str, str]:
    return parsed_url.scheme, parsed_url.netloc
