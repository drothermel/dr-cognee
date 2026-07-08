---
name: tool-graph
description: Build a per-tool Cognee knowledge graph from a tool/library's official docs, open-source repo, and web notes. Trigger when the user asks to "build a tool graph", graph a library's docs/features/controls, or create a per-tool knowledge base (e.g. pydantic, polars, a CLI's available controls). Uses drc (dr-cognee repo) with direct doc parsing (llms.txt, GitHub docs) before Firecrawl.
---

# Tool Graph

Build a dedicated Cognee knowledge graph for ONE tool/library — its capabilities, controls, features, extension points, and usage patterns — from primary sources. One workspace + one Cognee dataset per tool, exactly like deep research topics.

Run `drc` as `uv run drc ...` from `~/drotherm/repos/dr-cognee`. Requires `COGNEE_BASE_URL`, `COGNEE_API_KEY`, `OPENAI_API_KEY`; `FIRECRAWL_API_KEY` only for the gap-fill phase.

**Source priority: direct parsing first, Firecrawl last.** Docs pulled via `drc pull-docs` are ingested whole (no distillation) under the `docs` node set; only web-gathered extras go through scrape→distill.

## Phases

### 1. Init

```bash
uv run drc init "<tool>" -q "What are <tool>'s capabilities, controls, features, extension points, and common usage patterns?" \
  -f overview -f core-features -f configuration-and-controls -f extensions -f ecosystem-and-usage
```

Adapt facets to the tool (a CLI gets `commands`, `configuration-and-controls`, `extensions/plugins`; a library gets `api-surface`, `integrations`).

### 2. Direct doc pull (no Firecrawl)

1. **Probe for llms.txt** — check the obvious candidates with `curl -sI`:
   `https://docs.<tool>.dev/llms.txt`, `https://<tool>.dev/llms.txt`, `https://docs.<tool>.dev/latest/llms.txt`, the docs site root you find via a quick search. Prefer the curated `llms.txt` over `llms-full.txt`.
2. **Locate the GitHub repo** and its docs tree (usually `docs/` on the default branch).
3. Pull:
   ```bash
   uv run drc pull-docs -w research/<slug> \
     --llms https://docs.pydantic.dev/latest/llms.txt \
     --github https://github.com/pydantic/pydantic/tree/main/docs
   ```
   Use either or both; dedup is automatic (same URL → same source id). Add the README and CHANGELOG via `drc add-source <raw-url> --content-file <fetched>` if not covered.
4. **Scale check:** if the pull registered more than ~150 pages, that's fine for ingest but check `drc status` and note it in the log — cognify time scales with volume. If it registered near-zero, the tool has no llms.txt/docs dir; fall back to Firecrawl crawl of the docs site in phase 3.

### 3. Gap fill (Firecrawl, targeted)

Small, targeted harvests for what official docs don't say:

```bash
uv run drc harvest -q "<tool> plugins extensions ecosystem" --limit 8 -w research/<slug>
uv run drc harvest -q "<tool> in production lessons" --tbs qdr:y --limit 8 -w research/<slug>
uv run drc harvest -q "site:news.ycombinator.com <tool>" --limit 5 -w research/<slug>
```

Scrape the useful hits, `uv run drc distill` them (docs pages are skipped automatically — distill only touches scraped non-docs sources... it touches all scraped sources, so scrape web extras only when worth distilling).

### 4. Synthesis: the capability map

Write `synthesis/<facet>.md` per facet — this is the "notes" layer:
- **core-features**: what the tool does, organized by capability, with doc pointers
- **configuration-and-controls**: every knob — flags, env vars, config files, settings — as a scannable list
- **extensions**: plugin/extension mechanisms and the notable ecosystem entries
- **ecosystem-and-usage**: how people actually use it, gotchas, comparisons

### 5. Ingest + verify

```bash
uv run drc ingest -w research/<slug>
uv run drc query "what extension points does <tool> expose?" -w research/<slug>
uv run drc query "list the main configuration controls" --type GRAPH_COMPLETION -w research/<slug>
```

Sanity-check that graph answers match the docs. Then write `report.md`: a concise capability overview (per facet, with source pointers) — this is the human entry point to the graph. `uv run drc ingest` once more to include it.

## Quality bar

- Every facet has a synthesis file; every synthesis claim is traceable to a doc page or distilled source.
- The graph can answer "what can I configure?", "how do I extend it?", "what's it commonly paired with?" for the tool.
- Log honest gaps (undocumented features, stale docs) in report.md.
