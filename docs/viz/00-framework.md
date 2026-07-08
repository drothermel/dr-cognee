# Visualization for drc — Brainstorm Framework

Date: 2026-07-07
Status: Working framework — written before research, updated as findings land.

## 1. Objective

Design visualization tooling for the `drc` pipeline covering two moments:

1. **Live observability** — watching a deep-research or tool-graph run as it happens:
   harvest fan-out, source status transitions, distillation output landing, synthesis
   evolving, ingest/cognify progress, the graph growing.
2. **Result exploration** — after (or between) runs: the Cognee graph's structure, the
   knowledge it carries (entities, claims, provenance), and the report produced from
   the research question.

End state of this brainstorm: 3 fully-designed use cases, each pitched in a standalone
HTML report, plus a process report and a reflection report.

## 2. Audience and context (fixed by user)

- **Audience:** one power user (Danielle), driving `drc` herself via an AI agent.
  Personal tooling — low build cost and zero maintenance beat polish.
- **Form factor bias:** local web app, read over the workspace files + Cognee REST API.
- **Display:** very wide, fairly tall monitor. Designs should use the full canvas —
  multi-panel layouts, horizontal scrolling/panning where it earns its keep.
- **Key context:** during a run the *agent* operates `drc`; the human's job is
  oversight, trust, and steering between iterations. Live viz is therefore about
  answering "is coverage good? is the pipeline advancing? what did it just learn?
  where should I redirect it?" — not about operating controls.

## 3. Data inventory (what a viz can actually consume)

See `01-data-inventory.md` for the full inventory. Summary of shapes:

| # | Data shape | Where it lives | Freshness |
|---|---|---|---|
| D1 | Source state machine (found→scraped→distilled→ingested / skipped), with category, relevance, depth flags, errors | `sources.jsonl` (append/rewrite) | updates per drc command |
| D2 | Free-form narrative event stream | `log.md` (agent-appended) | continuous during run |
| D3 | Document corpus | `content/<id>.md` | grows during run |
| D4 | Structured knowledge per source: takeaways, entities, claims_of_use | `distilled/<id>.json` | after distill |
| D5 | Entity co-occurrence network (derivable from D4 — a *pre-graph* before Cognee!) | derived | after distill |
| D6 | Rolling synthesis per facet | `synthesis/<facet>.md` | agent-edited |
| D7 | The Cognee knowledge graph (nodes/edges/node-sets/communities) | hosted tenant; **access surface = open research question** | after cognify |
| D8 | Query/answer interactions | `drc query` output (currently ephemeral) | on demand |
| D9 | Final report with source-id citations | `report.md` | end of run |
| D10 | Ingest manifest (what went into the graph) | `ingested.json` | after ingest |

Two structural observations that should shape all designs:

- **The workspace is watchable.** Everything except D7/D8 is plain files in one
  directory — a file-watcher + SSE local web app gets live updates nearly for free.
- **D5 is underexploited.** Entities across distilled records form a co-occurrence
  graph *before* Cognee ever runs — a local, instantly-available preview of the
  knowledge graph, with perfect provenance (entity → source ids).

## 4. Lifecycle moments (jobs to be done)

| Moment | Human's question | Candidate data |
|---|---|---|
| M1 During sweep/harvest | Is coverage broad? What's being found? Dupes vs new? | D1, D2 |
| M2 During distill | What is it learning? Which sources are high-value? | D1, D4, D5 |
| M3 Between iterations (triage) | Depth flags to chase? Facets thin? Where to steer? | D1, D4, D6 |
| M4 During ingest/cognify | Is it progressing? What went in? | D10, D7 status |
| M5 Graph exploration | What does the graph know? How do entities connect? | D7, D5 |
| M6 Report reading | Is each claim evidenced? Trace claim → source | D9, D4, D3 |
| M7 Retrospective / cross-run | How did the run unfold? What did it cost/find over time? | D1 history, D2 |

## 5. Method space (to be filled by research)

Candidate visualization method families, mapped to data shapes — research will
validate, extend, and attach best practices + exemplar tools to each:

- **Pipeline/flow state:** status boards (kanban), Sankey of status transitions,
  activity feeds, run timelines/traces (observability-tool style).
- **Graph:** force-directed at scale (GPU), clustered/LOD views, search-first
  exploration, ego networks, node-set filtered lenses, path finding.
- **Dynamic graph:** growth animation, snapshot diffing, timeline scrubbing.
- **Corpus/triage:** faceted tables, triage queues, small-multiple cards.
- **Provenance/report:** annotated documents, sidenotes, evidence panels,
  claim→source linking.
- **Text-over-time:** synthesis diffs, log narrative rendering.

## 6. Research plan (subagent fan-out, wave 1)

Eight parallel research agents, each producing a markdown doc for `research/`:

| Agent | Topic | Feeds moments |
|---|---|---|
| R1 | Live pipeline/agent-run observability tools — market scan (Langfuse, Dagster, etc.) + patterns worth stealing | M1, M2, M4, M7 |
| R2 | Graph visualization tools/libraries for KGs — capabilities, scale, embedding effort | M5 |
| R3 | Graph exploration UX best practices (overview+detail, LOD, communities, search-first) | M5 |
| R4 | Dynamic/streaming graph viz — growth animation, snapshot diffs, layout stability | M4, M5 |
| R5 | Provenance & citation UX in research reports (NotebookLM, Elicit, sidenotes…) | M6 |
| R6 | Corpus triage UX — screening/annotation/review tools, faceted status boards | M3 |
| R7 | Operationalization: local personal web-app stacks over files + remote API | all |
| R8 | Cognee API surface for viz — what graph data the hosted tenant can actually serve | M4, M5 |

Wave 2 (after synthesis): 3-5 deep case studies on the strongest exemplars, and
design-critique agents during the use-case design phase.

## 7. Selection rubric for the top 3 use cases

Score candidate use cases 1-5 on each; pick a portfolio, not just the 3 highest:

1. **Decision value** — does it change what the human does next during/after a run?
2. **Data availability** — consumes data we provably have (D1-D6, D9-D10 safe; D7
   depends on R8 findings).
3. **Build cost** — weekend-buildable by one person on the chosen stack.
4. **Maintenance drag** — survives pipeline evolution without constant care.
5. **Wide-canvas payoff** — genuinely benefits from the big monitor.
6. **Distinctness** — the 3 picks should cover different moments (at least one live,
   at least one exploration).

## 8. Design process template (per chosen use case)

Each use case gets a design doc in `usecases/` following exactly this sequence:

1. **Goal, audience, context** — the moment(s) served, the questions answered.
2. **Problems & constraints** — what's hard, what data limits apply, non-goals.
3. **UX flow** — entry point, primary loop, key interactions, exit; state diagram.
4. **UI design** — layout for the wide canvas, panel-by-panel spec, visual language,
   concrete ASCII/wireframe mockups.
5. **Operationalization** — stack, data plumbing, file watching, API calls, build
   phases (v0 → v1), effort estimate, risks.

## 9. Deliverables & file layout

```
docs/viz/
  00-framework.md          # this file
  01-data-inventory.md     # ground truth of visualizable data
  log.md                   # investigation log, append-only
  research/                # synthesized topic docs (from wave-1 agents + curation)
  case-studies/            # wave-2 deep dives on exemplars
  usecases/                # design docs for the chosen 3
  reports/                 # FINAL: 3 pitch HTMLs + process HTML + reflection HTML
```

Final HTML reports: designed for a very wide/tall monitor, full-canvas layouts,
multi-directional scroll where useful. Fira Code for all code text.
