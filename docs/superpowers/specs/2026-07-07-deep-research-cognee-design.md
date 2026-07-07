# Deep Research → Cognee Graph Pipeline — Design

Date: 2026-07-07
Status: Approved (design review complete)

## Goal

A repeatable topic-research pipeline: given a research question (e.g., "what should I
use to build a graph knowledge base shared across my AI agents?"), systematically fan
out Firecrawl searches across web, news, GitHub, Hacker News, and research/PDF sources
with recency filters; keep both a free-form research log and structured per-source
records (URL, takeaways, "more here worth getting" flags); ingest the distilled
knowledge into a fresh per-topic hosted-Cognee dataset and run cognify so it becomes a
queryable, synthesized graph.

Success for v1: a smart agent driving this pipeline on a real question produces
deep-research-grade output — broad coverage, documented sources, ranked options per
category with justifications and evidence of active use — and leaves behind a
queryable Cognee graph rather than just a one-shot report.

## Decisions made during design review

- **Form factor:** hybrid. Substantial, independently reusable Python chunks (some
  containing LLM calls) for reproducible machinery; a skill does the heavy lifting of
  guiding the agent's research judgment (coverage strategy, tool combination,
  interleaved synthesis, feedback before finalizing).
- **Cognee:** hosted tenant (`*.aws.cognee.ai`) via REST API. `COGNEE_BASE_URL` /
  `COGNEE_API_KEY` env vars already configured. Local cognee library is out of scope.
- **Graph input:** distilled artifacts always (distilled records, synthesis notes,
  log, report) plus full scraped content for sources flagged high-value. Raw scrapes
  of everything are not ingested.
- **Report provenance:** the agent writes the final report from its logs and records,
  but must query the cognified graph first and fold in cross-source connections.
- **Architecture:** Approach A, "Toolbox + Playbook" — chunky `drc` CLI commands over
  a per-topic workspace; the skill is the research playbook.

## Architecture

Three layers. A per-topic **workspace directory** is the shared contract; the **`drc`
CLI** (Typer, this repo) reads/writes it deterministically; the **skill** tells the
agent how to drive both.

### Workspace layout

Default root is `./research/` under the current working directory; every `drc`
command accepts `--workspace` to point elsewhere.

```
research/<topic-slug>/
  topic.yaml              # question, facets, categories, cognee dataset name
  log.md                  # free-form research log — agent-written, append-only
  sources.jsonl           # one SourceRecord per line (the structured layer)
  content/<id>.md         # scraped page content, one file per source
  distilled/<id>.json     # DistilledRecord per source
  synthesis/<facet>.md    # agent's rolling synthesis notes, one per facet
  report.md               # final deliverable
```

### Data model (Pydantic, `extra="forbid"`)

**SourceRecord**
- `id`: short hash of normalized URL
- `url`, `title`
- `category`: enum — web / news / github / research / pdf
- `found_via`: query + source that surfaced it
- `published`: date if known
- `status`: enum — found → scraped → distilled → ingested; or skipped
- post-distillation: `relevance` (high/medium/low), `depth_flag` (bool),
  `depth_note` (what more is there and why it matters)

**DistilledRecord**
- `source_id`
- `takeaways`: list of strings
- `entities`: tools/projects/concepts mentioned
- `claims_of_use`: evidence the thing is actively used (first-class field — "how is
  it currently being used" is a core research requirement)
- `depth_flag`, `depth_note`
- `distilled_at`

### Cognee mapping

One hosted dataset per topic, named from the slug. Ingested artifacts: every distilled
record (rendered as clean text), full `content/` for depth-flagged high-relevance
sources, all `synthesis/` notes, `log.md`, and finally `report.md`. Cognify runs after
ingest.

## The `drc` toolbox

| Command | Does | Contract |
|---|---|---|
| `drc init <topic>` | Create workspace, `topic.yaml`, create Cognee dataset | idempotent |
| `drc harvest` | Run a batch of Firecrawl searches (queries × sources × categories × tbs), dedupe against `sources.jsonl`, append new SourceRecords; `--scrape` fills `content/` | queries via args or JSON spec file; reports new-vs-seen counts |
| `drc scrape <ids...>` | Fetch full content for specific sources (follow-ups) | updates status |
| `drc add-source <url>` | Register a hand-fetched source into the pipeline | escape hatch for ad-hoc agent fetches |
| `drc distill` | For each `scraped` source: one LLM call → DistilledRecord (structured output), update status | batch, resumable, skips already-distilled |
| `drc ingest` | Push the Cognee payload, trigger cognify, poll to completion | idempotent per artifact |
| `drc query "<q>"` | Cognee search (`--type` chunks/insights/completion) against the topic dataset | prints results for the agent |
| `drc status` | Counts by status/relevance, open depth-flags, facets with thin coverage | the agent's dashboard |

Implementation notes:
- Harvest/scrape call the Firecrawl API via the Python SDK (typed responses), not the
  plugin CLI. Same `FIRECRAWL_API_KEY`.
- Distill uses the Anthropic API with structured output (consult the claude-api skill
  for model choice at implementation time; default to the latest capable model).
- The agent may still use firecrawl plugin skills ad hoc (e.g., crawling one project's
  docs site); anything fetched by hand enters the pipeline via `drc add-source`.

## The playbook skill

A new skill, `deep-graph-research`, in `~/.claude/skills/`. Phases, with explicit
license to loop, pivot, and interleave:

1. **Scope.** Sharpen the question with the user if underspecified; decompose into
   facets; write `topic.yaml`; `drc init`; open `log.md` with the research plan.
2. **Breadth sweep.** Query matrix: per facet, multiple phrasings × Firecrawl sources
   (web, news) × categories (github, research, pdf) × recency tiers (last 30 days for
   "what's hot", unbounded for "what's established"). HN via
   `site:news.ycombinator.com` queries plus news-source searches. `drc harvest`, skim,
   log observations.
3. **Distill-and-deepen loop.** Scrape high-signal sources, `drc distill`, triage
   depth flags (crawl flagged docs, pull GitHub activity, chase comparison threads).
   Each iteration ends with the agent updating the facet's `synthesis/` note —
   synthesis interleaved with gathering, not deferred. `drc status` decides where
   coverage is thin.
4. **Feedback gate.** Before finalizing, spawn critic subagents: a coverage critic
   ("what categories/tools/angles are missing?") and a claims skeptic ("which
   takeaways are marketing vs. evidenced use?"). Findings feed one more targeted loop.
5. **Ingest + cognify.** `drc ingest`.
6. **Graph-enriched report.** Query the graph per facet (`drc query --type insights`)
   for cross-source connections; write `report.md` — ranked options per category with
   justifications, active-usage evidence, and source pointers (id → URL). Ingest the
   report last so the graph contains its own synthesis.

**Stop condition:** coverage is done when a sweep round surfaces mostly already-seen
sources AND the critics come back with nothing material (loop-until-dry, not a fixed
count).

## Error handling

Resumability is the error model. Every step advances per-source `status`; any command
re-run picks up where it left off. Firecrawl failures mark the source and continue;
distill retries once then leaves the source `scraped`; cognify polls with a timeout
and can be re-triggered.

## Testing

- pytest unit tests for models, URL normalization/dedup, and payload construction,
  using recorded fixture JSON. No live-API tests in CI.
- One small live smoke script in `scripts/`.
- Acceptance: run the full flow on "graph knowledge base across all my AI agents" and
  judge the report against deep-research quality.

## Out of scope for v1

- Multi-topic cross-graph queries.
- Incremental re-research of an existing topic (the design leaves room: harvest dedup
  and idempotent ingest already point that way).
- Local cognee library backend.
