# Tool-graph pilot notes (running log)

## Pydantic pilot (first tool)

**Setup:** llms.txt found at `https://docs.pydantic.dev/latest/llms.txt` (curated, 88 pages).
GitHub docs pull not needed — llms.txt coverage was complete (concepts, api, integrations,
examples, errors, internals).

**Iteration findings (fixed in code during pilot):**
1. `pull-docs --llms` initially registered 0 sources: the vendored llms mirror skips
   off-origin links by default, and pydantic's manifest lives on `docs.pydantic.dev` while
   every link targets `pydantic.dev`. Fix: `pull_llms_docs` passes `allow_off_origin=True`
   (we chose the manifest deliberately) and surfaces skipped links in the failure list.
2. `drc distill` would have run 88 pointless LLM calls over docs pages. Fix:
   `distill_pending` now skips `category=docs` sources — docs are ingested whole under the
   `docs` node set; distillation is only for web-gathered extras.

**Flow that worked:** init (5 facets) → pull-docs (88 docs) → 2 targeted gap-fill harvests
(12 found, 10 scraped, 10 distilled; 1 reddit scrape unsupported as usual) → synthesis
capability map per facet → ingest+cognify → verification queries → report.

**Open questions / watch items:**
- Cognify time for ~100-item ingests (measuring on this run).
- Whether `docs` node-set separation is visible/queryable usefully in Cognee results.

## llms.txt availability probe (for remaining tools)

| Tool | llms.txt | Fallback |
|---|---|---|
| polars | none (404 on docs.pola.rs, pola.rs) | GitHub docs tree + firecrawl |
| pydanticAI | https://ai.pydantic.dev/llms.txt (14KB) | — |
| cognee | https://docs.cognee.ai/llms.txt (1.9KB, small) | GitHub topoteretes/cognee docs |
| codex cli | https://developers.openai.com/codex/llms.txt (14KB) | — |
| claude code | https://code.claude.com/docs/llms.txt (36KB) | — |

## Cognee credits blocker (found during pydantic ingest)

- All 105 pydantic artifacts pushed fine; `cognify` returned HTTP 402:
  "Insufficient credits to run cognify. Only $6.45 of credits remain."
- Storage is a non-issue (2.7MB / 1GB). It's compute credits on the hosted tenant.
- Code hardening added: `CogneeCreditsError` (clean message instead of traceback),
  ingest reports `cognify: blocked: ...` and leaves statuses un-flipped, and a new
  standalone `drc cognify -w <ws>` re-triggers cognify without re-pushing (needed
  because `ingest` only cognifies when it pushed something new).
- Plan adaptation: all tool workspaces get built + pushed now; cognify + graph
  verification queries deferred until credits are added. Finish with
  `drc cognify -w research/<slug>` per workspace, then the verification queries.

## Polars pilot (github docs path)

- No llms.txt. GitHub pull of docs/source/user-guide initially collected 0 pages:
  the repo-root mkdocs.yml nav doesn't map onto the docs_path subtree, and the
  vendored collector only falls back to a tree walk when there is NO mkdocs config.
- Fix in our wrapper (vendored module untouched): if nav filtering yields zero pages,
  re-collect with mkdocs_config_path=None. Result: 71 user-guide pages registered.

## pydantic-ai run + credit economics

- 162 llms.txt docs + 20 distilled extras; 188 artifacts cognified; verification query
  correct (tools/output_type/deps/retries all match docs).
- Docs are far newer than most web tutorials (capabilities as primary extension point,
  A2A moved to fasta2a, harness/agent-spec layers) — the docs-first approach earns its keep.
- Credit economics discovery: after main cognify, a 2-item follow-up push was blocked at
  $12.36 remaining -> the credit gate estimates on TOTAL dataset size, not the incremental
  delta. Operational rule: get everything into the dataset BEFORE first cognify; treat
  re-cognify of big datasets as expensive.
- Recurring quirk: GRAPH_COMPLETION answers embellish "practitioner evidence" framing
  (LinkedIn/ServiceNow examples not in sources) across datasets — treat graph answers as
  organizers, verify claims against distilled records (same caveat as acceptance run).

## cognee run

- llms.txt is a manifest-of-manifests (5 shard indexes); vendored llms_mirror rejects
  manifest URLs not ending in `llms.txt` (`ValueError` at llms_mirror.py:178), so shard
  pages were registered via fetch + add-source (176 pages, 0 failures). Backlog: relax
  manifest naming upstream in dr-notion (accept llms-*.txt shards).
- Deliberately skipped the 122-page REST-endpoint-stub shard to stay under the credit
  gate; 216 artifacts cognified successfully, verification query PASS.
- Repo has no real docs tree — docs live on docs.cognee.ai only; README added manually.

## codex-cli run

- llms.txt at developers.openai.com/codex/llms.txt worked directly with pull-docs
  (95 pages; links were direct .md twins, no shard workaround needed). GitHub docs/
  tree is mostly redirect stubs (15 pages, low value). 135 artifacts staged+pushed.
- Cognify blocked at $7.24 remaining; recovery: `drc cognify -w research/codex-cli`.
- Note: repo's 600KB codex-manual.md pulled whole and will dominate that dataset's
  cognify cost — candidate for exclusion/split if credits stay tight.
- Synthesis quality high: two-axis sandbox×approval model, ~200-key config.toml
  inventory, MCP both directions, hooks/skills/plugins/subagents inventory.
