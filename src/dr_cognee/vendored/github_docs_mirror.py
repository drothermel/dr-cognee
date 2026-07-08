# Vendored from dr-notion@4117b4e (src/dr_notion/github_docs_mirror.py) - keep edits upstream.
from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict

ENCODING = "utf-8"
GITHUB_HOST = "github.com"
MANIFEST_FILENAME = "llms.txt"
MARKDOWN_EXTENSION = ".md"
TEMP_FILE_PREFIX = ".download-"

API_REFERENCE_PATTERN = re.compile(r"^\s*:{3,4}\s+(?P<symbol>[A-Za-z_][\w.]+)\s*$")
HEADING_ANCHOR_PATTERN = re.compile(r"\s+\{\s*#[^}]+\s*\}\s*$")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\([^)]+\)")
INCLUDE_PATTERN = re.compile(
    r"^\s*\{(?P<marker>[*!])(?P<quote>>?)\s*(?P<spec>.*?)\s*(?P=marker)\}\s*$"
)
LINE_SELECTION_PATTERN = re.compile(r"\bln\[(?P<selection>[^\]]+)]")
LINK_PATTERN = re.compile(r"(?P<prefix>]\()(?P<target>[^)]+?)(?P<suffix>\))")
HTML_ABBR_PATTERN = re.compile(
    r"<abbr\s+title=\"(?P<title>[^\"]+)\">(?P<text>.*?)</abbr>"
)
HTML_TAG_PATTERN = re.compile(r"</?[^>]+>")


class GitDocsStatus(StrEnum):
    WRITTEN = "written"
    DRY_RUN = "dry_run"
    FAILED = "failed"
    SKIPPED_EXISTING = "skipped_existing"


class GitHubDocsSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: str
    repo: str
    ref: str
    docs_path: PurePosixPath

    @property
    def repository_url(self) -> str:
        return f"https://{GITHUB_HOST}/{self.owner}/{self.repo}.git"

    @property
    def tree_url(self) -> str:
        return f"https://{GITHUB_HOST}/{self.owner}/{self.repo}/tree/{self.ref}/{self.docs_path}"


class NavEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: PurePosixPath
    nav_path: list[str]
    title_hint: str | None = None


class MarkdownPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    source_path: PurePosixPath
    output_path: Path
    relative_output_path: PurePosixPath
    source_url: str
    nav_path: list[str]
    api_references: list[str]
    content: str


class WriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    status: GitDocsStatus
    message: str | None = None


class GitDocsMirrorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: GitHubDocsSource
    commit: str
    checkout_path: Path
    output_path: Path
    pages: list[MarkdownPage]
    manifest_result: WriteResult
    results: list[WriteResult]

    def all_results(self) -> list[WriteResult]:
        return [self.manifest_result, *self.results]

    def count_results(self, status: GitDocsStatus) -> int:
        return sum(result.status == status for result in self.all_results())


def parse_github_tree_url(url: str) -> GitHubDocsSource:
    parsed_url = urlparse(url)
    path_parts = [part for part in parsed_url.path.split("/") if part]

    if parsed_url.netloc != GITHUB_HOST or len(path_parts) < 5:
        raise ValueError("URL must be a GitHub tree URL with a docs path")

    owner, repo, tree_segment, ref, *docs_path_parts = path_parts
    if tree_segment != "tree" or not docs_path_parts:
        raise ValueError("URL must use /tree/<ref>/<docs-path>")

    return GitHubDocsSource(
        owner=owner,
        repo=repo,
        ref=ref,
        docs_path=PurePosixPath(*docs_path_parts),
    )


def mirror_github_docs(
    github_tree_url: str,
    output_root: Path,
    checkout_root: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    include_private: bool = False,
) -> GitDocsMirrorSummary:
    source = parse_github_tree_url(github_tree_url)
    checkout_path = ensure_checkout(source, checkout_root)
    mkdocs_config_path = find_mkdocs_config(checkout_path, source.docs_path)
    configure_sparse_checkout(
        checkout_path,
        source,
        collect_include_sparse_patterns(checkout_path, source.docs_path, mkdocs_config_path),
    )

    commit = run_git(checkout_path, "rev-parse", "--short", "HEAD").strip()
    output_path = docs_output_path(source, output_root)
    pages = collect_markdown_pages(
        source=source,
        repo_root=checkout_path,
        output_path=output_path,
        commit=commit,
        include_private=include_private,
        mkdocs_config_path=mkdocs_config_path,
    )
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest_content = render_manifest(
        source=source,
        commit=commit,
        docs_root=source.docs_path,
        generated_at=generated_at,
        pages=pages,
    )
    manifest_result = write_mirror_text(
        output_path / MANIFEST_FILENAME,
        manifest_content,
        dry_run=dry_run,
        force=force,
    )
    results = [
        write_mirror_text(page.output_path, page.content, dry_run=dry_run, force=force)
        for page in pages
    ]

    return GitDocsMirrorSummary(
        source=source,
        commit=commit,
        checkout_path=checkout_path,
        output_path=output_path,
        pages=pages,
        manifest_result=manifest_result,
        results=results,
    )


def ensure_checkout(source: GitHubDocsSource, checkout_root: Path) -> Path:
    checkout_path = checkout_root / source.repo
    if (checkout_path / ".git").exists():
        remote_url = run_git(checkout_path, "remote", "get-url", "origin").strip()
        if remote_url not in {source.repository_url, source.repository_url.removesuffix(".git")}:
            raise ValueError(f"Existing checkout has unexpected origin: {remote_url}")
        run_git(checkout_path, "fetch", "--depth", "1", "origin", source.ref)
        run_git(checkout_path, "checkout", "--detach", "FETCH_HEAD")
    else:
        checkout_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                source.repository_url,
                str(checkout_path),
            ],
            check=True,
            text=True,
        )
        run_git(checkout_path, "checkout", source.ref)

    configure_sparse_checkout(checkout_path, source, extra_patterns=[])
    return checkout_path


def configure_sparse_checkout(
    checkout_path: Path,
    source: GitHubDocsSource,
    extra_patterns: list[str],
) -> None:
    mkdocs_path = PurePosixPath(source.docs_path).parent / "mkdocs.yml"
    patterns = [
        f"/{source.docs_path}/",
        f"/{mkdocs_path}",
        "/mkdocs.yml",
        *extra_patterns,
    ]
    run_git(
        checkout_path,
        "sparse-checkout",
        "set",
        "--no-cone",
        *dedupe_preserve_order(patterns),
    )


def collect_include_sparse_patterns(
    repo_root: Path,
    docs_path: PurePosixPath,
    mkdocs_config_path: Path | None,
) -> list[str]:
    docs_root = repo_root / docs_path
    include_base = include_base_path(repo_root, docs_path, mkdocs_config_path)
    patterns: list[str] = []
    resolved_repo_root = repo_root.resolve()

    for markdown_path in sorted(docs_root.rglob(f"*{MARKDOWN_EXTENSION}")):
        for include in iter_include_specs(markdown_path.read_text(encoding=ENCODING)):
            include_path = resolve_include_path(repo_root, include_base, include.path)
            try:
                relative_path = include_path.relative_to(resolved_repo_root)
            except ValueError:
                continue
            first_part = relative_path.parts[0]
            if first_part != docs_path.parts[0]:
                patterns.append(f"/{first_part}/")

    return dedupe_preserve_order(patterns)


def collect_markdown_pages(
    *,
    source: GitHubDocsSource,
    repo_root: Path,
    output_path: Path,
    commit: str,
    include_private: bool,
    mkdocs_config_path: Path | None,
) -> list[MarkdownPage]:
    docs_root = repo_root / source.docs_path
    include_base = include_base_path(repo_root, source.docs_path, mkdocs_config_path)
    nav_entries = collect_nav_entries(docs_root, mkdocs_config_path, include_private)
    pages: list[MarkdownPage] = []

    for nav_entry in nav_entries:
        source_path = source.docs_path / nav_entry.path
        markdown_path = repo_root / source_path
        raw_content = markdown_path.read_text(encoding=ENCODING)
        title = nav_entry.title_hint or first_markdown_heading(raw_content) or nav_entry.path.stem
        normalized_body, api_references = normalize_markdown(
            raw_content,
            repo_root=repo_root,
            include_base=include_base,
            docs_path=source.docs_path,
        )
        nav_path = build_page_nav_path(nav_entry, title)
        page_metadata = {
            "title": title,
            "source_path": source_path.as_posix(),
            "source_url": source_blob_url(source, commit, source_path),
            "git_commit": commit,
            "nav_path": nav_path,
        }
        if api_references:
            page_metadata["api_references"] = api_references

        relative_output_path = nav_entry.path
        content = "\n".join(
            [
                "---",
                yaml.safe_dump(page_metadata, sort_keys=False, allow_unicode=True).strip(),
                "---",
                "",
                normalized_body.strip(),
                "",
            ]
        )
        pages.append(
            MarkdownPage(
                title=title,
                source_path=source_path,
                output_path=output_path / relative_output_path,
                relative_output_path=relative_output_path,
                source_url=page_metadata["source_url"],
                nav_path=nav_path,
                api_references=api_references,
                content=content,
            )
        )

    return pages


def collect_nav_entries(
    docs_root: Path,
    mkdocs_config_path: Path | None,
    include_private: bool,
) -> list[NavEntry]:
    if mkdocs_config_path and mkdocs_config_path.exists():
        config = yaml.load(mkdocs_config_path.read_text(encoding=ENCODING), Loader=yaml.BaseLoader)
        nav = config.get("nav") if isinstance(config, dict) else None
        if isinstance(nav, list):
            entries = flatten_mkdocs_nav(nav)
            return dedupe_nav_entries(
                [
                    entry
                    for entry in entries
                    if is_markdown_page(entry.path)
                    and (include_private or not is_private_markdown(entry.path))
                    and (docs_root / entry.path).exists()
                ]
            )

    return fallback_markdown_entries(docs_root, include_private)


def flatten_mkdocs_nav(nav_items: Sequence[object]) -> list[NavEntry]:
    return _flatten_mkdocs_nav(nav_items, parent_nav_path=[])


def _flatten_mkdocs_nav(
    nav_items: Sequence[object],
    parent_nav_path: list[str],
) -> list[NavEntry]:
    entries: list[NavEntry] = []
    for item in nav_items:
        if isinstance(item, str):
            entries.append(NavEntry(path=PurePosixPath(item), nav_path=parent_nav_path))
            continue

        if not isinstance(item, dict):
            continue

        for raw_label, value in item.items():
            label = str(raw_label).strip()
            next_nav_path = [*parent_nav_path, label] if label else parent_nav_path
            if isinstance(value, str):
                entries.append(
                    NavEntry(
                        path=PurePosixPath(value),
                        nav_path=next_nav_path,
                        title_hint=label or None,
                    )
                )
            elif isinstance(value, list):
                entries.extend(_flatten_mkdocs_nav(value, next_nav_path))

    return entries


def fallback_markdown_entries(docs_root: Path, include_private: bool) -> list[NavEntry]:
    entries: list[NavEntry] = []
    for markdown_path in sorted(docs_root.rglob(f"*{MARKDOWN_EXTENSION}"), key=fallback_sort_key):
        relative_path = PurePosixPath(markdown_path.relative_to(docs_root).as_posix())
        if include_private or not is_private_markdown(relative_path):
            entries.append(NavEntry(path=relative_path, nav_path=[]))
    return entries


def normalize_markdown(
    content: str,
    *,
    repo_root: Path,
    include_base: Path,
    docs_path: PurePosixPath,
) -> tuple[str, list[str]]:
    lines = content.splitlines()
    normalized_lines: list[str] = []
    api_references: list[str] = []
    in_code_fence = False
    skip_mkdocstrings_options = False

    for line in lines:
        if line.lstrip().startswith("```"):
            in_code_fence = not in_code_fence
            normalized_lines.append(line)
            continue

        if in_code_fence:
            include = parse_include_spec(line)
            if include:
                normalized_lines.extend(
                    read_include_lines(
                        repo_root=repo_root,
                        include_base=include_base,
                        include=include,
                    )
                )
                continue
            normalized_lines.append(line)
            continue

        if skip_mkdocstrings_options:
            if not line.strip() or line.startswith((" ", "\t")):
                continue
            skip_mkdocstrings_options = False

        include = parse_include_spec(line)
        if include:
            normalized_lines.extend(
                render_include(repo_root=repo_root, include_base=include_base, include=include)
            )
            continue

        api_reference_match = API_REFERENCE_PATTERN.match(line)
        if api_reference_match:
            symbol = api_reference_match.group("symbol")
            api_references.append(symbol)
            normalized_lines.extend(["", f"## API reference: `{symbol}`", ""])
            skip_mkdocstrings_options = True
            continue

        cleaned_line = clean_markdown_line(line, docs_path=docs_path)
        if cleaned_line is None:
            continue
        normalized_lines.append(cleaned_line)

    return collapse_blank_lines("\n".join(normalized_lines)), dedupe_preserve_order(api_references)


class IncludeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: PurePosixPath
    line_selection: list[int] | None = None


def iter_include_specs(content: str) -> list[IncludeSpec]:
    includes: list[IncludeSpec] = []
    for line in content.splitlines():
        include = parse_include_spec(line)
        if include:
            includes.append(include)
    return includes


def parse_include_spec(line: str) -> IncludeSpec | None:
    include_match = INCLUDE_PATTERN.match(line)
    if not include_match:
        return None

    spec = include_match.group("spec").strip()
    if not spec:
        return None

    path_token, *option_tokens = spec.split()
    option_text = " ".join(option_tokens)
    return IncludeSpec(
        path=PurePosixPath(path_token),
        line_selection=parse_line_selection(option_text),
    )


def parse_line_selection(option_text: str) -> list[int] | None:
    selection_match = LINE_SELECTION_PATTERN.search(option_text)
    if not selection_match:
        return None

    selected_lines: list[int] = []
    for raw_part in selection_match.group("selection").split(","):
        part = raw_part.strip()
        if not part:
            continue
        if ":" in part:
            start_text, end_text = part.split(":", maxsplit=1)
            selected_lines.extend(range(int(start_text), int(end_text) + 1))
        else:
            selected_lines.append(int(part))

    return selected_lines


def render_include(repo_root: Path, include_base: Path, include: IncludeSpec) -> list[str]:
    selected = read_include_lines(
        repo_root=repo_root,
        include_base=include_base,
        include=include,
    )
    language = language_for_path(resolve_include_path(repo_root, include_base, include.path))
    return ["", f"```{language}", *selected, "```", ""]


def read_include_lines(repo_root: Path, include_base: Path, include: IncludeSpec) -> list[str]:
    include_path = resolve_include_path(repo_root, include_base, include.path)
    include_text = include_path.read_text(encoding=ENCODING)
    include_lines = include_text.splitlines()

    if include.line_selection:
        return [
            include_lines[line_number - 1]
            for line_number in include.line_selection
            if 1 <= line_number <= len(include_lines)
        ]
    return include_lines


def clean_markdown_line(line: str, *, docs_path: PurePosixPath) -> str | None:
    stripped = line.strip()

    if not stripped:
        return ""

    if stripped.startswith(("![", "<img", "<iframe", "</iframe", "<video", "</video")):
        return None

    if stripped in {"///", "////"}:
        return None

    if stripped.startswith("//// tab"):
        return tab_heading(stripped)

    if stripped.startswith("/// "):
        return admonition_heading(stripped)

    if stripped.startswith("==="):
        return tab_heading(stripped)

    if stripped.startswith(("<div", "</div", "<section", "</section")):
        return None

    cleaned = IMAGE_PATTERN.sub("", line)
    cleaned = HEADING_ANCHOR_PATTERN.sub("", cleaned)
    cleaned = HTML_ABBR_PATTERN.sub(r"\g<text> (\g<title>)", cleaned)
    cleaned = HTML_TAG_PATTERN.sub("", cleaned)
    cleaned = normalize_local_markdown_links(cleaned, docs_path=docs_path)
    return cleaned.rstrip()


def admonition_heading(line: str) -> str:
    content = line.lstrip("/").strip()
    kind, _, title = content.partition("|")
    label = kind.strip().title()
    title = title.strip()
    if title:
        return f"> {label}: {title}"
    return f"> {label}:"


def tab_heading(line: str) -> str:
    content = line.lstrip("/").strip()
    _, _, title = content.partition("|")
    title = title.strip().strip('"')
    if title:
        return f"### Tab: {title}"
    return "### Tab"


def normalize_local_markdown_links(line: str, *, docs_path: PurePosixPath) -> str:
    def replace_link(match: re.Match[str]) -> str:
        target = match.group("target")
        if "://" in target or target.startswith("#"):
            return match.group(0)

        path_text, separator, fragment = target.partition("#")
        if not path_text.endswith(MARKDOWN_EXTENSION):
            return match.group(0)

        normalized_path = PurePosixPath(path_text)
        if normalized_path.is_absolute():
            normalized_path = PurePosixPath(*normalized_path.parts[1:])
            try:
                normalized_path = normalized_path.relative_to(docs_path)
            except ValueError:
                pass

        normalized_target = normalized_path.as_posix()
        if separator:
            normalized_target = f"{normalized_target}#{fragment}"
        return f"{match.group('prefix')}{normalized_target}{match.group('suffix')}"

    return LINK_PATTERN.sub(replace_link, line)


def render_manifest(
    *,
    source: GitHubDocsSource,
    commit: str,
    docs_root: PurePosixPath,
    generated_at: str,
    pages: list[MarkdownPage],
) -> str:
    lines = [
        f"# {source.owner}/{source.repo} Docs Mirror",
        "",
        f"Source: {source.tree_url}",
        f"Commit: {commit}",
        f"Docs root: {docs_root}",
        f"Generated: {generated_at}",
        "",
        "## Documents",
        "",
    ]

    for page in pages:
        description = " > ".join(page.nav_path)
        api_description = ", ".join(page.api_references)
        suffix_parts = [part for part in [description, api_description] if part]
        suffix = f": {'; '.join(suffix_parts)}" if suffix_parts else ""
        lines.append(f"- [{page.title}]({page.relative_output_path}){suffix}")

    return "\n".join(lines) + "\n"


def write_mirror_text(
    output_path: Path,
    content: str,
    *,
    dry_run: bool,
    force: bool,
) -> WriteResult:
    if dry_run:
        return WriteResult(output_path=output_path, status=GitDocsStatus.DRY_RUN)

    if output_path.exists() and not force:
        return WriteResult(output_path=output_path, status=GitDocsStatus.SKIPPED_EXISTING)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding=ENCODING,
            dir=output_path.parent,
            prefix=TEMP_FILE_PREFIX,
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(output_path)
    except Exception as error:
        return WriteResult(
            output_path=output_path,
            status=GitDocsStatus.FAILED,
            message=str(error),
        )

    return WriteResult(output_path=output_path, status=GitDocsStatus.WRITTEN)


def docs_output_path(source: GitHubDocsSource, output_root: Path) -> Path:
    return output_root / GITHUB_HOST / source.owner / source.repo / Path(source.docs_path)


def source_blob_url(
    source: GitHubDocsSource,
    commit: str,
    source_path: PurePosixPath,
) -> str:
    return f"https://{GITHUB_HOST}/{source.owner}/{source.repo}/blob/{commit}/{source_path}"


def find_mkdocs_config(repo_root: Path, docs_path: PurePosixPath) -> Path | None:
    candidates = [
        repo_root / docs_path.parent / "mkdocs.yml",
        repo_root / "mkdocs.yml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def include_base_path(
    repo_root: Path,
    docs_path: PurePosixPath,
    mkdocs_config_path: Path | None,
) -> Path:
    if mkdocs_config_path:
        return mkdocs_config_path.parent
    return repo_root / docs_path


def resolve_include_path(repo_root: Path, include_base: Path, include_path: PurePosixPath) -> Path:
    resolved_path = (include_base / Path(include_path)).resolve()
    repo_root_resolved = repo_root.resolve()
    if not resolved_path.is_relative_to(repo_root_resolved):
        raise ValueError(f"Include path escapes repository: {include_path}")
    return resolved_path


def first_markdown_heading(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return HEADING_ANCHOR_PATTERN.sub("", line[2:]).strip()
    return None


def build_page_nav_path(nav_entry: NavEntry, title: str) -> list[str]:
    if nav_entry.title_hint:
        return nav_entry.nav_path
    if nav_entry.nav_path and nav_entry.nav_path[-1] == title:
        return nav_entry.nav_path
    return [*nav_entry.nav_path, title]


def is_markdown_page(path: PurePosixPath) -> bool:
    return path.suffix == MARKDOWN_EXTENSION


def is_private_markdown(path: PurePosixPath) -> bool:
    return path.name.startswith("_")


def fallback_sort_key(path: Path) -> tuple[tuple[str, ...], str]:
    parts = path.parts
    file_name = path.name
    index_rank = "0" if file_name == "index.md" else "1"
    return parts[:-1], f"{index_rank}-{file_name}"


def language_for_path(path: Path) -> str:
    return {
        ".css": "css",
        ".html": "html",
        ".js": "javascript",
        ".json": "json",
        ".md": "markdown",
        ".py": "python",
        ".sh": "bash",
        ".toml": "toml",
        ".yml": "yaml",
        ".yaml": "yaml",
    }.get(path.suffix, "text")


def collapse_blank_lines(text: str) -> str:
    output_lines: list[str] = []
    blank_count = 0
    for line in text.splitlines():
        if line.strip():
            blank_count = 0
            output_lines.append(line.rstrip())
        else:
            blank_count += 1
            if blank_count <= 2:
                output_lines.append("")
    return "\n".join(output_lines).strip() + "\n"


def dedupe_nav_entries(entries: list[NavEntry]) -> list[NavEntry]:
    seen_paths: set[PurePosixPath] = set()
    deduped_entries: list[NavEntry] = []
    for entry in entries:
        if entry.path in seen_paths:
            continue
        seen_paths.add(entry.path)
        deduped_entries.append(entry)
    return deduped_entries


def dedupe_preserve_order[T](items: list[T]) -> list[T]:
    deduped_items: list[T] = []
    for item in items:
        if item not in deduped_items:
            deduped_items.append(item)
    return deduped_items


def run_git(checkout_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=checkout_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
