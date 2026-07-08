"""drc: deep-research toolbox CLI over a per-topic workspace."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import typer
from firecrawl import Firecrawl
from pydantic import TypeAdapter

from dr_cognee.cognee_client import DEFAULT_SEARCH_TYPE, CogneeClient
from dr_cognee.distill import (
    DEFAULT_PROVIDER,
    DistillProvider,
    distill_pending,
    make_distill_client,
)
from dr_cognee.docs_pull import pull_github_docs, pull_llms_docs
from dr_cognee.firecrawl_ops import harvest, scrape
from dr_cognee.ingest import ingest_workspace
from dr_cognee.models import (
    HarvestSpec,
    QuerySpec,
    SourceCategory,
    SourceRecord,
    SourceStatus,
    TopicConfig,
)
from dr_cognee.sources import SourceStore, source_id
from dr_cognee.workspace import Workspace

DEFAULT_WORKSPACE_ROOT = Path("research")

app = typer.Typer(no_args_is_help=True, help="Deep research -> Cognee graph toolbox.")

WorkspaceOption = typer.Option(None, "--workspace", "-w", help="Topic workspace directory.")


def slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug or "topic"


def resolve_workspace(workspace: Path | None) -> Workspace:
    if workspace is not None:
        return Workspace.load(workspace)
    if DEFAULT_WORKSPACE_ROOT.is_dir():
        topics = [p for p in DEFAULT_WORKSPACE_ROOT.iterdir() if (p / "topic.yaml").exists()]
        if len(topics) == 1:
            return Workspace.load(topics[0])
        if len(topics) > 1:
            raise typer.BadParameter(
                f"Multiple workspaces under {DEFAULT_WORKSPACE_ROOT}/; pass --workspace"
            )
    raise typer.BadParameter("No workspace found; run `drc init` or pass --workspace")


def firecrawl_client() -> Firecrawl:
    return Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])


@app.command()
def init(
    topic: str,
    question: str = typer.Option(..., "--question", "-q", help="The research question."),
    facet: list[str] = typer.Option([], "--facet", "-f", help="Facet name (repeatable)."),
    root: Path = typer.Option(DEFAULT_WORKSPACE_ROOT, "--root", help="Workspace root dir."),
) -> None:
    """Create a topic workspace and its Cognee dataset."""
    slug = slugify(topic)
    config = TopicConfig(
        topic=topic,
        slug=slug,
        question=question,
        facets=facet or ["general"],
        dataset_name=slug,
        created=datetime.now(UTC).date().isoformat(),
    )
    ws = Workspace.init(root / slug, config)
    dataset_id = CogneeClient().ensure_dataset(config.dataset_name)
    typer.echo(f"workspace: {ws.root}")
    typer.echo(f"dataset: {config.dataset_name} ({dataset_id})")


@app.command(name="harvest")
def harvest_cmd(
    query: list[str] = typer.Option([], "--query", "-q", help="Search query (repeatable)."),
    spec: Path | None = typer.Option(None, "--spec", help="HarvestSpec JSON file."),
    sources: str = typer.Option("web", "--sources", help="Comma list: web,news."),
    categories: str = typer.Option("", "--categories", help="Comma list: github,research,pdf."),
    tbs: str | None = typer.Option(None, "--tbs", help="Recency filter, e.g. qdr:m."),
    limit: int = typer.Option(10, "--limit"),
    do_scrape: bool = typer.Option(False, "--scrape", help="Also scrape new sources."),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Run a batch of Firecrawl searches into sources.jsonl."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    if spec is not None:
        harvest_spec = HarvestSpec.model_validate_json(spec.read_text())
    elif query:
        category_list = [SourceCategory(c) for c in categories.split(",") if c]
        harvest_spec = HarvestSpec(
            queries=[
                QuerySpec(
                    query=q,
                    sources=sources.split(","),
                    categories=category_list,
                    tbs=tbs,
                    limit=limit,
                )
                for q in query
            ]
        )
    else:
        raise typer.BadParameter("Pass --query or --spec")
    client = firecrawl_client()
    before_found = {r.id for r in store.pending(SourceStatus.FOUND)}
    result = harvest(store, harvest_spec, client)
    typer.echo(f"new: {result.new}  seen: {result.seen}  errors: {len(result.errors)}")
    for error in result.errors:
        typer.echo(f"  error: {error}")
    if do_scrape:
        new_ids = [r.id for r in store.pending(SourceStatus.FOUND) if r.id not in before_found]
        updated = scrape(store, ws, new_ids, client)
        ok = sum(r.status == SourceStatus.SCRAPED for r in updated)
        typer.echo(f"scraped: {ok}/{len(updated)}")


@app.command(name="scrape")
def scrape_cmd(
    ids: list[str] = typer.Argument(None, help="Source ids to scrape."),
    all_found: bool = typer.Option(False, "--all-found", help="Scrape every `found` source."),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Fetch full content for sources into content/<id>.md."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    target_ids = list(ids or [])
    if all_found:
        target_ids += [r.id for r in store.pending(SourceStatus.FOUND)]
    if not target_ids:
        raise typer.BadParameter("Pass ids or --all-found")
    known = store.load()
    for unknown in [i for i in target_ids if i not in known]:
        typer.echo(f"{unknown}  UNKNOWN (not in sources.jsonl)")
    updated = scrape(store, ws, target_ids, firecrawl_client())
    for record in updated:
        marker = "ok" if record.status == SourceStatus.SCRAPED else f"FAIL ({record.error})"
        typer.echo(f"{record.id}  {marker}  {record.url}")


@app.command()
def pull_docs(
    llms: list[str] = typer.Option([], "--llms", help="llms.txt manifest URL (repeatable)."),
    github: list[str] = typer.Option(
        [], "--github", help="GitHub tree URL for a docs dir (repeatable)."
    ),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Pull docs directly (no Firecrawl): llms.txt manifests and GitHub repo docs."""
    if not llms and not github:
        raise typer.BadParameter("Pass --llms and/or --github")
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    for manifest_url in llms:
        result = pull_llms_docs(store, ws, manifest_url)
        typer.echo(
            f"llms {manifest_url}: new={result.new} seen={result.seen} "
            f"failed={len(result.failed)}"
        )
        for failure in result.failed:
            typer.echo(f"  failed: {failure}")
    for tree_url in github:
        result = pull_github_docs(store, ws, tree_url)
        typer.echo(
            f"github {tree_url}: new={result.new} seen={result.seen} "
            f"failed={len(result.failed)}"
        )
        for failure in result.failed:
            typer.echo(f"  failed: {failure}")


@app.command()
def add_source(
    url: str,
    category: SourceCategory = typer.Option(SourceCategory.WEB, "--category"),
    title: str | None = typer.Option(None, "--title"),
    content_file: Path | None = typer.Option(
        None, "--content-file", help="Already-fetched content; stored as scraped."
    ),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Register a hand-fetched source into the pipeline."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    record = SourceRecord(
        id=source_id(url),
        url=url,
        title=title or url,
        category=category,
        found_via="manual [add-source]",
    )
    if content_file is not None:
        ws.content_path(record.id).write_text(content_file.read_text())
        record.status = SourceStatus.SCRAPED
    added = store.append_new([record])
    typer.echo(f"{record.id}  {'added' if added else 'already present'}  {record.url}")


@app.command()
def distill(
    provider: DistillProvider = typer.Option(DEFAULT_PROVIDER, "--provider"),
    model: str | None = typer.Option(None, "--model", help="Defaults per provider."),
    limit: int | None = typer.Option(None, "--limit"),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Distill scraped sources into structured takeaway records."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    client = make_distill_client(provider=provider, model=model)
    result = distill_pending(store, ws, client, limit=limit)
    typer.echo(f"distilled: {result.distilled}  failed: {len(result.failed)}")
    for failure in result.failed:
        typer.echo(f"  failed: {failure}")


@app.command()
def ingest(
    wait: bool = typer.Option(True, "--wait/--no-wait"),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Push distilled knowledge to Cognee and run cognify."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    result = ingest_workspace(ws, store, CogneeClient(), wait=wait)
    typer.echo(
        f"pushed: {result.pushed}  skipped: {result.skipped}  cognify: {result.cognify_status}"
    )


@app.command()
def query(
    text: str,
    search_type: str = typer.Option(DEFAULT_SEARCH_TYPE, "--type"),
    workspace: Path | None = WorkspaceOption,
) -> None:
    """Search the topic's Cognee graph."""
    ws = resolve_workspace(workspace)
    client = CogneeClient()
    dataset_id = client.ensure_dataset(ws.config.dataset_name)
    results = client.search(dataset_id, text, search_type=search_type)
    if isinstance(results, str):
        typer.echo(results)
    else:
        typer.echo(TypeAdapter(object).dump_json(results, indent=1).decode())


@app.command()
def status(workspace: Path | None = WorkspaceOption) -> None:
    """Workspace dashboard: counts, depth flags, facet coverage."""
    ws = resolve_workspace(workspace)
    store = SourceStore(ws.sources_file)
    typer.echo(f"topic: {ws.config.topic}")
    typer.echo(f"question: {ws.config.question}")
    counts = store.counts()
    typer.echo(
        "sources: "
        + "  ".join(f"{status.value}={count}" for status, count in counts.items() if count)
    )
    flags = store.open_depth_flags()
    if flags:
        typer.echo("open depth flags:")
        for record in flags:
            typer.echo(f"  {record.id}  {record.title}: {record.depth_note}")
    synthesized = {p.stem for p in ws.synthesis_dir.glob("*.md")}
    thin = [f for f in ws.config.facets if f not in synthesized]
    if thin:
        typer.echo(f"facets without synthesis: {', '.join(thin)}")


def main() -> None:
    app()
