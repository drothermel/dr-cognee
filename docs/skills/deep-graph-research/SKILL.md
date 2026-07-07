---
name: deep-graph-research
description: Deep research on a topic that produces both a deep-research-grade report AND a queryable per-topic Cognee knowledge graph. Trigger when the user asks for deep/systematic research that should be captured as a knowledge graph, or mentions the drc pipeline. Uses the drc CLI (dr-cognee repo) for harvest/scrape/distill/ingest/query and Firecrawl for ad-hoc fetching.
---

# Deep Graph Research

Drive the `drc` toolbox (from `~/drotherm/repos/dr-cognee`, run as `uv run drc ...` from that repo or wherever it's installed) through a research topic. You supply the judgment: coverage strategy, pivots, synthesis, and the final report. `drc` supplies the plumbing: workspace records, Firecrawl fan-out, LLM distillation, Cognee ingest/cognify/query.

Requires env: `FIRECRAWL_API_KEY`, `COGNEE_BASE_URL`, `COGNEE_API_KEY`.

## The workspace contract

`drc init` creates `research/<slug>/` containing: `topic.yaml`, `log.md` (your free-form research log — append constantly), `sources.jsonl` (structured records), `content/`, `distilled/`, `synthesis/<facet>.md` (your rolling per-facet synthesis), `report.md`. All `drc` commands take `--workspace research/<slug>`.

## Phases

Run these as a loop with judgment, not a fixed script. Interleave synthesis with gathering.

### 1. Scope

- If the question is underspecified, sharpen it with the user first (budget/constraints/what "best" means).
- Decompose into 3-6 **facets** (e.g. for a tooling question: packaged solutions, component stacks, evaluation criteria, real-world usage, recent developments).
- `drc init "<topic>" -q "<question>" -f facet-1 -f facet-2 ...`
- Open `log.md` with your research plan.

### 2. Breadth sweep

Build a query matrix: for each facet, 2-4 phrasings × source mixes × recency tiers:

```bash
# what's established (no tbs) and what's hot (last 30 days)
drc harvest -q "open source knowledge graph memory for AI agents" --sources web --limit 10 -w research/<slug>
drc harvest -q "agent memory layer comparison" --sources web,news --tbs qdr:m -w research/<slug>
# GitHub / research / PDF coverage
drc harvest -q "temporal knowledge graph agent memory" --categories github,research --limit 10 -w research/<slug>
# Hacker News coverage
drc harvest -q "site:news.ycombinator.com agent knowledge graph memory" --limit 10 -w research/<slug>
```

Skim titles in `sources.jsonl`, log observations (what angles are hot, what names recur), and note surprises. `drc status` shows counts.

### 3. Distill-and-deepen loop

Repeat until dry:

1. Pick high-signal sources; `drc scrape <ids...>` (or `--all-found` when the found set is small).
2. `drc distill` — produces takeaways, entities, `claims_of_use`, relevance, and depth flags.
3. `drc status` — triage **open depth flags**: for each, decide fetch-more (crawl a project's docs with firecrawl skills then `drc add-source <url> --content-file <path>`), targeted `drc harvest` queries, or drop it (note why in the log).
4. **End every iteration by updating `synthesis/<facet>.md`** for the facets the new material touched. Synthesis is interleaved, not deferred.
5. Pivot: entities that recur across sources get their own targeted queries.

**Stop condition (loop-until-dry):** a sweep round is mostly `seen` rather than `new`, AND the critics (phase 4) return nothing material.

### 4. Feedback gate

Before finalizing, spawn critic subagents (Agent tool):

- **Coverage critic**: give it the facet list + entity list + report skeleton; ask "what categories, tools, or angles are missing? what would a domain expert expect to see?"
- **Claims skeptic**: give it the takeaways/claims_of_use; ask "which of these are marketing claims vs evidenced use? which need a second source?"

Feed material findings back into one more phase-3 loop.

### 5. Ingest + cognify

```bash
drc ingest -w research/<slug>        # pushes distilled + flagged full content + synthesis + log, runs cognify, waits
```

### 6. Graph-enriched report

1. Query the graph per facet for cross-source connections you may have missed:
   ```bash
   drc query "how do <entity A> and <entity B> relate?" --type GRAPH_COMPLETION -w research/<slug>
   drc query "<facet> summary" --type SUMMARIES -w research/<slug>
   ```
2. Write `report.md`: **ranked options per category**, each with justification, evidence of active use, trade-offs, and source pointers (`id → URL` from `sources.jsonl`). Lead with the recommendation.
3. `drc ingest` again so the graph contains the report itself.

## Report contract

- Ranked options per facet/category with explicit reasons for the ranking.
- Every claim traceable: cite source ids/URLs inline.
- "How it's actually used" evidence separated from vendor claims.
- An "open questions / thin coverage" section — honesty about gaps beats false completeness.
