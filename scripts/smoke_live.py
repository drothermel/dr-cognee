"""Live end-to-end smoke: harvest -> scrape -> distill -> ingest -> query.

Hits Firecrawl, Anthropic, and the hosted Cognee tenant for real. Prints SMOKE OK
on success. See TESTING.md.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import typer
from firecrawl import Firecrawl

from dr_cognee.cognee_client import CogneeClient
from dr_cognee.distill import AnthropicDistillClient, distill_pending
from dr_cognee.firecrawl_ops import harvest, scrape
from dr_cognee.ingest import ingest_workspace
from dr_cognee.models import HarvestSpec, QuerySpec, SourceStatus, TopicConfig
from dr_cognee.sources import SourceStore
from dr_cognee.workspace import Workspace

SMOKE_SLUG = "smoke-test"
SMOKE_QUERY = "knowledge graph memory for AI agents"
SEARCH_TYPE = "CHUNKS"

app = typer.Typer()


@app.command()
def main(root: Path = Path("research")) -> None:
    for var in ("FIRECRAWL_API_KEY", "COGNEE_BASE_URL", "COGNEE_API_KEY"):
        if not os.environ.get(var):
            raise typer.BadParameter(f"missing env var {var}")

    config = TopicConfig(
        topic="Smoke Test",
        slug=SMOKE_SLUG,
        question="What tools provide knowledge graph memory for AI agents?",
        facets=["tools"],
        dataset_name=SMOKE_SLUG,
        created=datetime.now(UTC).date().isoformat(),
    )
    ws = Workspace.init(root / SMOKE_SLUG, config)
    store = SourceStore(ws.sources_file)
    typer.echo(f"[1/6] workspace: {ws.root}")

    fc = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    result = harvest(store, HarvestSpec(queries=[QuerySpec(query=SMOKE_QUERY, limit=3)]), fc)
    typer.echo(f"[2/6] harvest new={result.new} seen={result.seen} errors={result.errors}")

    found = store.pending(SourceStatus.FOUND)
    if found:
        updated = scrape(store, ws, [found[0].id], fc)
        typer.echo(f"[3/6] scrape {updated[0].id}: {updated[0].status} {updated[0].error or ''}")
    else:
        typer.echo("[3/6] scrape skipped (no new found sources; resuming prior run)")

    distill_result = distill_pending(store, ws, AnthropicDistillClient(), limit=1)
    typer.echo(
        f"[4/6] distill distilled={distill_result.distilled} failed={distill_result.failed}"
    )
    already_distilled = store.counts()
    have_distilled = (
        distill_result.distilled
        + already_distilled[SourceStatus.DISTILLED]
        + already_distilled[SourceStatus.INGESTED]
    )
    if not have_distilled:
        typer.echo("SMOKE FAILED: no distilled sources (check ANTHROPIC_API_KEY)")
        raise typer.Exit(1)

    client = CogneeClient()
    ingest_result = ingest_workspace(ws, store, client)
    typer.echo(
        f"[5/6] ingest pushed={ingest_result.pushed} skipped={ingest_result.skipped} "
        f"cognify={ingest_result.cognify_status}"
    )

    dataset_id = client.ensure_dataset(config.dataset_name)
    hits = client.search(dataset_id, "knowledge graph memory", search_type=SEARCH_TYPE)
    typer.echo(f"[6/6] search hits={len(hits) if isinstance(hits, list) else 1}")
    if not hits:
        typer.echo("SMOKE FAILED: empty search result")
        raise typer.Exit(1)
    typer.echo(f"first hit: {str(hits[0])[:200] if isinstance(hits, list) else str(hits)[:200]}")
    typer.echo("SMOKE OK")


if __name__ == "__main__":
    app()
