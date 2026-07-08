# Data Inventory — what exists for a viz to consume

Ground truth from the code on branch `07-07-tool-graph` (models.py, workspace.py,
cognee_client.py, cli.py). Any design that needs data not listed here must say how
it gets created.

## Workspace files (all local, all watchable)

### `topic.yaml` — TopicConfig
`topic`, `slug`, `question`, `facets: list[str]`, `dataset_name`, `created`.
Static per run. Gives a viz its title, question, and the facet dimension.

### `sources.jsonl` — one SourceRecord per line
The structured backbone. Fields per record:

- `id` (short URL hash), `url`, `title`
- `category`: web | news | github | research | pdf | docs
- `found_via`: free text — "query [source]" for harvest, "llms.txt [manifest]" /
  "github docs [tree]" for pull-docs. **Parseable provenance of discovery.**
- `published`: str | None
- `status`: found → scraped → distilled → ingested; or skipped
- `relevance`: high | medium | low | None (set post-distill)
- `depth_flag`: bool, `depth_note`: str | None — the triage queue
- `error`: str | None — per-source failure record

Rewritten by SourceStore on updates (not purely appended). A watcher sees whole-file
changes; diffing against last-seen state yields *transition events* (X moved
scraped→distilled) — the raw material for any live activity feed or Sankey.

### `log.md`
Agent-written free-form narrative, append-heavy. Markdown. The "what was I thinking"
layer. Renderable as a narrative timeline next to structured events.

### `content/<id>.md`
Full scraped/pulled page content per source. Joinable to sources.jsonl by id.

### `distilled/<id>.json` — DistilledRecord
- `source_id`
- `takeaways: list[str]`
- `entities: list[str]`  ← **cross-source entity co-occurrence network, locally derivable**
- `claims_of_use: list[str]`
- `relevance`, `depth_flag`, `depth_note`
- `distilled_at` (timestamp — gives distill-phase timing for free)

### `synthesis/<facet>.md`
Agent-edited rolling synthesis per facet. Git-diffable / snapshot-diffable to show
"what changed in understanding this iteration".

### `report.md`
Final deliverable. Cites source ids/URLs inline per the skill contract
(`id → URL` pointers). Claim→evidence linking = parse ids out of the report text,
join to sources.jsonl + distilled/ + content/.

### `ingested.json`
Manifest of artifacts pushed to Cognee (idempotency record) — tells a viz exactly
what the graph was built from.

## Timing/history caveat

SourceRecord has **no timestamps** (only DistilledRecord.distilled_at). True run
timelines need either (a) a watcher that logs observed transitions as they happen, or
(b) an event log added to drc. Both are viable; designs must pick one and say so.
The mirror/ dir (tool-graph runs) also exists but is raw material, not viz-relevant.

## Hosted Cognee API (as wrapped by cognee_client.py today)

- `POST /api/v1/datasets/` — ensure dataset → id
- `POST /api/v1/add_text` — texts + optional `nodeSet` tags
- `POST /api/v1/cognify` — background run; 402 = credits error
- `GET /api/v1/datasets/status` — coarse pipeline status (poll; in-progress vs done)
- `POST /api/v1/search` — searchType: GRAPH_COMPLETION (default) | CHUNKS | SUMMARIES
  | INSIGHTS (per design doc; exact set of useful types = research question R8)

**Not wired in cognee_client.py today, but VERIFIED LIVE on the hosted tenant**
(research/cognee-api-surface.md, R8, 2026-07-07):

- `GET /api/v1/datasets/{id}/graph` → full nodes+edges JSON (3,033 nodes / 13,189
  edges for a mid-size dataset; node types Entity/EntityType/DocumentChunk/
  TextSummary/TextDocument/NodeSet; `properties.belongs_to_set` on members).
- `GET /api/v1/visualize?dataset_id=…` → self-contained d3 HTML.
- `GET /api/v1/schema/inventory?dataset_id=…` → per-type counts + relationship
  distributions.
- `POST /api/v1/search` with `verbose: true` → retrieved triplet objects
  (query-scoped subgraphs). Note: the INSIGHTS search type no longer exists.

So "visualize the graph itself" is fully feasible over HTTP. The local entity
co-occurrence graph from distilled/ remains valuable as the *pre-cognify* live
preview and as a zero-API fallback layer, not as the primary plan. Caveat: the
hosted API is unversioned — viz code should shape-check responses against recorded
fixtures and degrade visibly on drift.

## Node sets in the graph

Ingest tags artifacts with node sets (e.g. `docs` for pulled docs in tool-graph runs;
distilled/synthesis/log/report artifacts per design doc). If node-set filtering is
retrievable at query/export time (R8), it's a natural "lens" dimension for graph views.
