# Deep Research → Cognee Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `drc` Typer CLI toolbox (workspace, harvest, scrape, add-source, distill, ingest, query, status) plus the `deep-graph-research` playbook skill, per the approved spec at `docs/superpowers/specs/2026-07-07-deep-research-cognee-design.md`.

**Architecture:** A per-topic workspace directory is the shared contract. Pydantic models define `SourceRecord`/`DistilledRecord`; a JSONL store owns `sources.jsonl`; thin operation modules wrap Firecrawl (harvest/scrape), Anthropic (distill), and the hosted Cognee REST API (ingest/query). `cli.py` is a thin Typer adapter over those modules.

**Tech Stack:** Python 3.12, uv, Typer, Pydantic v2, firecrawl-py 4.x, anthropic SDK (`messages.parse` structured output, model `claude-opus-4-8`), httpx against the hosted Cognee tenant, pytest with recorded fixtures.

## Global Constraints

- Env contract: `FIRECRAWL_API_KEY`, `COGNEE_BASE_URL`, `COGNEE_API_KEY` (all already set in Danielle's environment). Cognee auth header: `X-Api-Key`.
- Workspace root defaults to `./research/`; every command accepts `--workspace` to point at a specific topic dir.
- All structured records: Pydantic `BaseModel`, `ConfigDict(extra="forbid")`, `StrEnum` for closed value sets, domain literals as `UPPER_SNAKE_CASE` constants.
- Resumability is the error model: every step advances per-source `status`; re-runs skip completed work.
- No live-API calls in pytest; recorded fixture JSON only. One live smoke script in `scripts/` + `TESTING.md`.
- Distill model default: `claude-opus-4-8` via `client.messages.parse(...)` with a Pydantic `output_format`.
- Cognee endpoints: `POST /api/v1/datasets/` (idempotent create), `POST /api/v1/add_text` (`textData`, `datasetId`, `nodeSet`), `POST /api/v1/cognify` (`datasetIds`, `runInBackground`), `GET /api/v1/datasets/status?dataset=<uuid>`, `POST /api/v1/search` (`searchType`, `datasetIds`, `query`).

## File Structure

```
src/dr_cognee/
  __init__.py        # version only
  models.py          # enums, TopicConfig, SourceRecord, DistilledRecord, HarvestSpec
  workspace.py       # Workspace: paths, init, topic.yaml load/save
  sources.py         # SourceStore: sources.jsonl load/append/update, URL normalize + id hash
  firecrawl_ops.py   # harvest_queries(), scrape_sources() over firecrawl SDK
  distill.py         # distill_pending() via anthropic messages.parse
  cognee_client.py   # CogneeClient: httpx wrapper for the hosted tenant
  ingest.py          # build_payloads() + ingest_workspace(): push artifacts, cognify, poll
  cli.py             # Typer app `drc` wiring all commands
tests/
  test_models.py test_sources.py test_firecrawl_parsing.py test_ingest_payloads.py
  fixtures/firecrawl_search.json fixtures/firecrawl_scrape.json
scripts/smoke_live.py   # tiny live end-to-end probe
TESTING.md
~/.claude/skills/deep-graph-research/SKILL.md   # the playbook skill
```

---

### Task 1: Models + workspace

**Files:** Create `src/dr_cognee/models.py`, `src/dr_cognee/workspace.py`; Test `tests/test_models.py`.

**Produces (later tasks rely on):**
- Enums: `SourceCategory(StrEnum)` = web/news/github/research/pdf; `SourceStatus(StrEnum)` = found/scraped/distilled/ingested/skipped; `Relevance(StrEnum)` = high/medium/low.
- `TopicConfig(BaseModel)`: `topic: str`, `slug: str`, `question: str`, `facets: list[str]`, `dataset_name: str`, `created: str` (ISO date).
- `SourceRecord(BaseModel)`: `id: str`, `url: str`, `title: str`, `category: SourceCategory`, `found_via: str`, `published: str | None = None`, `status: SourceStatus = found`, `relevance: Relevance | None = None`, `depth_flag: bool = False`, `depth_note: str | None = None`, `error: str | None = None`.
- `DistilledRecord(BaseModel)`: `source_id: str`, `takeaways: list[str]`, `entities: list[str]`, `claims_of_use: list[str]`, `relevance: Relevance`, `depth_flag: bool`, `depth_note: str | None`, `distilled_at: str`.
- `QuerySpec(BaseModel)`: `query: str`, `sources: list[str] = ["web"]`, `categories: list[SourceCategory] = []`, `tbs: str | None = None`, `limit: int = 10`. `HarvestSpec(BaseModel)`: `queries: list[QuerySpec]`.
- `Workspace` class: `root: Path`; properties `topic_file`, `log_file`, `sources_file`, `content_dir`, `distilled_dir`, `synthesis_dir`, `report_file`; `Workspace.init(root, config)` creates dirs + `topic.yaml` + seed `log.md` (idempotent); `Workspace.load(root)` -> Workspace with `.config: TopicConfig`; `content_path(source_id)`, `distilled_path(source_id)`.

**Steps:**
- [ ] Write tests: round-trip `TopicConfig` through `topic.yaml`; `Workspace.init` creates layout and is idempotent; `SourceRecord` rejects unknown fields (`extra="forbid"`).
- [ ] Implement models + workspace; run `uv run pytest tests/test_models.py -q` until green.
- [ ] Commit `feat: workspace and record models`.

### Task 2: SourceStore (sources.jsonl + dedup)

**Files:** Create `src/dr_cognee/sources.py`; Test `tests/test_sources.py`.

**Interfaces — Produces:**
- `normalize_url(url: str) -> str`: lowercase scheme+host, drop fragment, drop `utm_*`/`ref` query params, strip trailing slash.
- `source_id(url: str) -> str`: first 12 hex chars of sha256 of normalized URL.
- `SourceStore(path: Path)`: `.load() -> dict[str, SourceRecord]` (keyed by id), `.append_new(records) -> list[SourceRecord]` (skips ids already present, appends the rest as JSONL lines, returns the truly-new ones), `.update(record)` (rewrite file with replaced record), `.counts() -> dict[SourceStatus, int]`, `.pending(status) -> list[SourceRecord]`, `.open_depth_flags() -> list[SourceRecord]`.

**Steps:**
- [ ] Tests: normalization cases (`https://Example.com/x/?utm_source=hn#frag` == `https://example.com/x`), dedup on `append_new`, `update` persists status change, counts.
- [ ] Implement; `uv run pytest tests/test_sources.py -q` green.
- [ ] Commit `feat: source store with url dedup`.

### Task 3: Firecrawl harvest + scrape

**Files:** Create `src/dr_cognee/firecrawl_ops.py`; Test `tests/test_firecrawl_parsing.py` + `tests/fixtures/firecrawl_search.json`.

**Interfaces:**
- Consumes: `SourceStore`, `QuerySpec`, `SourceRecord`, `source_id`.
- Produces: `search_hits_to_records(hits: list[dict], query: QuerySpec) -> list[SourceRecord]` (pure, fixture-testable — maps Firecrawl web/news result dicts: `url`, `title`, `category` when present, news `date` -> `published`; `found_via=f"{query.query} [{source_kind}]"`). `harvest(store, spec, client) -> HarvestResult(BaseModel)` with `new: int`, `seen: int`, `errors: list[str]` — calls `client.search(q.query, sources=q.sources, categories=[c.value for c in q.categories] or None, tbs=q.tbs, limit=q.limit)`, converts `result.web` / `result.news` items via `.model_dump()`, appends via store; per-query failures append to `errors` and continue. `scrape(store, workspace, ids, client) -> list[SourceRecord]` — `client.scrape(url, formats=["markdown"], only_main_content=True)`, writes markdown to `content/<id>.md`, status -> `scraped`; failure records `error` and continues.
- Firecrawl client injected (`Firecrawl(api_key=...)` built in cli), so tests use fixture dicts and a stub.

**Steps:**
- [ ] Record fixture: run one real `firecrawl` search via a throwaway `uv run python` snippet, save trimmed JSON of `.model_dump()` output to `tests/fixtures/firecrawl_search.json`.
- [ ] Tests: fixture hits map to `SourceRecord`s with correct category/published; harvest dedups across two specs sharing a URL (stub client); scrape failure marks `error` and continues.
- [ ] Implement; pytest green. Commit `feat: firecrawl harvest and scrape ops`.

### Task 4: Distill (Anthropic structured output)

**Files:** Create `src/dr_cognee/distill.py`; extend `tests/test_models.py` only if needed.

**Interfaces:**
- `DISTILL_MODEL = "claude-opus-4-8"` constant; overridable via `--model`.
- `DistillOutput(BaseModel)`: `takeaways: list[str]`, `entities: list[str]`, `claims_of_use: list[str]`, `relevance: Relevance`, `depth_flag: bool`, `depth_note: str | None` (the LLM-facing schema; `distill.py` composes it into `DistilledRecord` with `source_id` + `distilled_at`).
- `distill_source(client, record, content, question) -> DistillOutput`: one `client.messages.parse(model=..., max_tokens=8000, system=DISTILL_SYSTEM_PROMPT, messages=[...], output_format=DistillOutput)` call; prompt includes the research question, source URL/title, and content truncated to `MAX_CONTENT_CHARS = 60_000`.
- `distill_pending(store, workspace, client, question, model) -> DistillBatchResult(BaseModel)` (`distilled: int`, `failed: list[str]`): iterates `store.pending(SCRAPED)`, one retry on `anthropic.APIStatusError >= 500` / `RateLimitError`, writes `distilled/<id>.json`, updates record with relevance/depth fields, status -> `distilled`. Continue-on-failure batch semantics; failed ids stay `scraped`.

**Steps:**
- [ ] Implement with the prompt inline (`DISTILL_SYSTEM_PROMPT` constant instructing: extract takeaways, named tools/projects/concepts, evidence-of-active-use claims, relevance to the question, and whether the source has more depth worth fetching + what).
- [ ] Unit-test the pure composition (`DistillOutput` -> `DistilledRecord`) with a stub client; no live calls.
- [ ] Commit `feat: llm distillation of scraped sources`.

### Task 5: Cognee client + ingest

**Files:** Create `src/dr_cognee/cognee_client.py`, `src/dr_cognee/ingest.py`; Test `tests/test_ingest_payloads.py`.

**Interfaces:**
- `CogneeClient(base_url, api_key)`: httpx.Client, `timeout=120`, header `X-Api-Key`. Methods: `ensure_dataset(name) -> str` (POST `/api/v1/datasets/` returns existing on name match; return `id`), `add_text(dataset_id, texts: list[str], node_set: list[str] | None)`, `cognify(dataset_id, background: bool = True) -> dict`, `dataset_status(dataset_id) -> str` (GET `/api/v1/datasets/status`), `wait_for_cognify(dataset_id, timeout_s=900, poll_s=10) -> str` (poll until status not in-progress; raise `CogneeTimeoutError` after timeout), `search(dataset_id, query, search_type="GRAPH_COMPLETION") -> list | str`.
- `render_distilled(record: SourceRecord, distilled: DistilledRecord) -> str` — clean text block: title, URL, relevance, takeaways bullets, entities, claims-of-use, depth note. Pure; fixture-tested.
- `build_payloads(workspace, store) -> list[IngestItem]` where `IngestItem(BaseModel)`: `key: str` (e.g. `distilled:<id>`, `content:<id>`, `synthesis:<facet>`, `log`, `report`), `text: str`, `node_set: list[str]`. Includes: every distilled record (rendered), full `content/<id>.md` for records with `depth_flag and relevance == high`, all `synthesis/*.md`, `log.md`, `report.md` if present.
- `ingest_workspace(workspace, store, client) -> IngestResult(BaseModel)` (`pushed: int`, `skipped: int`, `cognify_status: str`): manifest `ingested.json` in workspace maps `key -> sha256(text)`; unchanged keys are skipped (idempotent); after pushing, trigger cognify and wait; distilled sources' status -> `ingested`.

**Steps:**
- [ ] Tests: `render_distilled` output contains URL/takeaways; `build_payloads` selects full content only for high+depth-flagged sources; manifest skip logic (`pushed`/`skipped` split) with a stub client.
- [ ] Implement; pytest green. Commit `feat: cognee client and idempotent ingest`.

### Task 6: Typer CLI

**Files:** Create `src/dr_cognee/cli.py`; Modify `pyproject.toml` (add `[project.scripts] drc = "dr_cognee.cli:app"`).

**Commands (all take `--workspace PATH`; default resolution `./research/<slug>` where slug required or inferable):**
- `drc init TOPIC --question TEXT --facet NAME...` → Workspace.init + `CogneeClient.ensure_dataset(dataset_name)`, prints workspace path + dataset id.
- `drc harvest --spec spec.json | --query TEXT... [--sources web,news] [--categories github,research,pdf] [--tbs qdr:m] [--limit N] [--scrape]` → build `HarvestSpec`, run harvest, optionally scrape new high-priority hits; prints new/seen/errors.
- `drc scrape ID... | --all-found` → scrape listed (or all `found`) sources.
- `drc add-source URL --category CAT [--title T] [--content-file PATH]` → register hand-fetched source; if content file given, store as scraped.
- `drc distill [--model MODEL] [--limit N]` → distill pending scraped sources.
- `drc ingest [--no-wait]` → ingest + cognify (+ wait unless `--no-wait`).
- `drc query TEXT [--type GRAPH_COMPLETION|CHUNKS|SUMMARIES|...]` → search dataset, print results.
- `drc status` → counts by status/relevance, open depth flags with notes, facets lacking a synthesis file.

**Steps:**
- [ ] Implement CLI as thin adapters (build clients from env, call modules, print via typer.echo — human-readable, stable lines).
- [ ] Verify: `uv run drc --help` shows all commands; `uv run drc init`/`status` work against a temp dir without network (init needs Cognee — gate dataset creation behind reachable env or `--no-dataset` flag? No: keep it simple — init calls Cognee; that's the contract).
- [ ] Run full `uv run pytest -q`. Commit `feat: drc typer cli`.

### Task 7: Playbook skill

**Files:** Create `~/.claude/skills/deep-graph-research/SKILL.md`.

Content: the six-phase playbook from the spec (scope → breadth sweep → distill-and-deepen → critic feedback gate → ingest/cognify → graph-enriched report), with concrete `drc` command examples, query-matrix guidance (facets × phrasings × sources/categories × recency tiers incl. `site:news.ycombinator.com`), interleaved-synthesis rule, loop-until-dry stop condition, and the report contract (ranked options per category with justifications, usage evidence, `id → URL` pointers; ingest report last).

**Steps:**
- [ ] Write SKILL.md with frontmatter (`name: deep-graph-research`, description with trigger conditions).
- [ ] Commit a copy under `docs/skills/deep-graph-research/SKILL.md` in this repo so the skill is version-controlled with the code it drives.

### Task 8: Live smoke + TESTING.md

**Files:** Create `scripts/smoke_live.py`, `TESTING.md`.

- [ ] `smoke_live.py`: typer script — creates workspace `research/smoke-test`, harvests 1 query (limit 3), scrapes 1 source, distills it, ingests + cognifies (waits), runs one `CHUNKS` search, prints each step's evidence (counts, ids, dataset id, first search hit). Requires all three env vars.
- [ ] `TESTING.md`: `uv run pytest -q` for units; `uv run python scripts/smoke_live.py` for live; success criteria: pytest all green; smoke prints `SMOKE OK` after a non-empty search result.
- [ ] Run the smoke live; fix what breaks. Commit `feat: live smoke script and testing doc`.

### Task 9: Verify + acceptance prep

- [ ] Full `uv run pytest -q` green; `uv run drc --help` clean.
- [ ] Run danielle-diff-check pass over the branch diff before finalizing.
- [ ] (Acceptance run on the real topic happens as a follow-up driven by the skill, per spec.)

## Self-Review Notes

- Spec coverage: workspace contract (T1), records (T1), store/dedup (T2), harvest/scrape (T3), add-source (T6), distill w/ claims_of_use + depth flags (T4), ingest selection rule + idempotency + cognify (T5), query/status (T6), skill w/ critics + stop condition (T7), error model = per-source status + continue-on-failure (T3–T5), testing strategy (fixtures + smoke) (T3, T8). No gaps found.
- Type consistency: `SourceStore.pending(SourceStatus)` used by distill (SCRAPED) and scrape (FOUND); `IngestItem.key` format shared between build_payloads and manifest.
