# Research Synthesis — cross-cutting conclusions

Date: 2026-07-07. Distilled from the eight wave-1 research docs in `research/`.
This is my synthesis, not a summary — it states the conclusions the designs will build on,
each traceable to a research doc.

## S1. The feasibility question is settled: the graph is fully reachable

R8's live verification changes the whole design space. `GET /api/v1/datasets/{id}/graph`
returns the complete graph (nodes with type, description, `belongs_to_set`,
importance/topological weights; labeled edges) in one call at drc scale. Additionally:
`/schema/inventory` gives per-type counts + relationship distributions (a free overview
layer), `/visualize` gives Cognee's own d3 HTML (the baseline to beat), and
`POST /search` with `verbose: true` returns the retrieved triplet objects (query-scoped
subgraphs). INSIGHTS is gone from the API — nothing should be designed against it.
**Consequence:** the Graph Explorer use case is unblocked and can be designed against
real, verified payload shapes. The local entity co-occurrence graph (from distilled/)
demotes from "primary fallback" to "pre-cognify live preview."

## S2. One architecture serves everything: watcher → event log → SSE → panels

R1 (Dozzle/Phoenix architecture) and R7 (stack comparison) independently converge:
a single local FastAPI process, zero storage, reading the workspace and pushing
SSE-driven fragment updates (htmx), with graph libs as CDN ES modules and the server
proxying Cognee (hiding the API key). R7 supplies the load-bearing plumbing rule:
**never tail a rewritten file** — reparse `sources.jsonl` on change, diff keyed
snapshots (id → hash), and emit semantic transition events; byte-offset-tail only
append-only `log.md`.

This resolves the timestamp gap flagged in `01-data-inventory.md`: the watcher itself
mints the event log (`events.jsonl` beside the workspace or in a viz cache dir):
`{ts, kind, source_id, from, to, detail}`. That one derived artifact powers the live
feed (R1 pattern 5), the "new since last looked" badges (R1 pattern 12), the run
timeline (R1 pattern 3), the coverage saturation curve (R6 pattern 10), and — later —
graph replay (R4). **The event log is the single highest-leverage piece of
infrastructure in the whole program; every live design assumes it.**

## S3. Live oversight: the human is a steerer, not an operator

R1 and R6 agree on the frame: during a run the agent does the work; the human's
outputs are *directives*. Design conclusions:

- **Layout:** the converged wide-monitor shape is facet rail | dense master
  table/grid | detail pane, with a top strip: Now panel ("agent is scraping X, 8s"),
  counts-by-state funnel (never percent bars — denominator grows), hoisted errors.
- **The Airflow grid transposed** (sources × stages, colored cells) is the single
  glance answering "where is the run" — R1's top steal, and R6's funnel-strip is its
  compact cousin.
- **Triage is keyboard verbs + auto-advance + zero-target queues** (Depth flags (7) ·
  Errors (12) · …) ordered by expected payoff. Verbs append structured directives to
  a queue the agent consumes — this is the one genuinely novel mechanism (nothing on
  the market does human→agent steering directives well).
- **"New since last looked" is the highest-leverage bespoke feature** — underserved
  commercially, nearly free given the event log + localStorage.
- **Saturation made visible**: new-vs-seen per harvest round is literally the
  skill's loop-until-dry stop condition rendered as a curve (R6/ASReview wave plot).

## S4. Graph exploration: search-first, communities as overview, provenance as trust

R3's evidence is unambiguous: global hairballs fail past ~200 nodes (Obsidian), and
the field replaced overview-first with **"search, show context, expand on demand."**
Design conclusions for a few-thousand-node Cognee graph:

- Land on **search + community meta-node overview** (EntityType/community collapse;
  `/schema/inventory` can seed this before any layout runs), never the full graph.
- **Ego view is the workhorse**: DOI-bounded ~30-50 node neighborhoods, ranked
  expansion, structured (radial/layered) layout — not free physics.
- **Provenance-on-click is the highest-value feature**: node/edge → evidence panel →
  DocumentChunk → TextDocument → back to the drc source record and content file.
  Trust in LLM-built graphs hinges on this (R3's 2025 study), and drc uniquely has
  the full provenance chain on disk.
- **Node sets are the lens dimension** (docs/distilled/synthesis/report as filter
  chips) — verified present in the export payload.
- **Text stays the primary answer channel**; graph views verify and broaden. So the
  explorer should embed the query workbench (drc search types side by side), with
  "ask about selection" as the graph→LLM handoff.
- **Library choice:** sigma.js + graphology (MIT; Louvain + FA2 + persistable
  positions in one stack — R2's primary pick), with cosmograph as the max-wow
  alternative. Persist layout positions so the graph looks the same across sessions.
- **Change comprehension is diffs, not animation** (R4's empirical verdict):
  two-snapshot union diff with synchronized positions + "most rewired entities" list
  beats growth animation for analysis; animation is legitimate only for live
  "what just appeared" monitoring and replay theater.

## S5. Report reading: passage anchors, hover cards, valence badges

R5's single biggest divider between fast and painful verification: **passage-anchored
citations** (source_id + span), not document-level ones. Design conclusions:

- **Detail ladder**: citation chip → hover card (quote + badges; target 80% of
  verifications end here) → distilled record → full content, each level optional.
- **Tri-panel** report | evidence | source with sacred scroll position; sidenotes in
  the wide-monitor margin by default (gwern's requirement: visible without clicks).
- **Valence badges** operationalize drc's core quality rule: classify citations
  USE / VENDOR / SECONDHAND (claims_of_use already separates these at distill time);
  roll-up strips (`USE:3 VENDOR:1`) make thin sourcing visible; render un-cited
  claims with an explicit gap marker.
- **Claim-table inversion** (Elicit/Casefleet): rows = claims, evidence attributes as
  columns — the "audit the report" mode next to the "read the report" mode.
- **Pipeline implication** (must be declared in the design): today's distilled records
  and report citations lack char spans. Options: (a) fuzzy-match takeaway text against
  content files at render time (no pipeline change), or (b) upgrade distill to emit
  quote spans (small prompt/schema change). Designs should ship (a) and recommend (b).

## S6. Small pipeline upgrades that unlock outsized viz value

Ranked by value/cost, each optional (viz must degrade gracefully without them):

1. **Watcher-minted event log** — no pipeline change at all; the dashboard creates it.
2. **Citation spans in distill output** — one schema field + prompt line; upgrades
   report verification from fuzzy-match to exact highlight.
3. **Directives queue** (`directives.jsonl` the agent reads between iterations) — one
   skill-instruction line + a tiny file contract; turns the triage desk from
   read-only into actual steering.
4. **Graph snapshot on ingest** — `drc ingest` saves the `/graph` export to the
   workspace; enables cognify diffs with zero extra API design.

## S7. What this implies for selection

The three bundles hypothesized in `02-usecase-candidates.md` survive research intact,
and every one is data-feasible today:

- **Run Cockpit** (C1+C2+C7): validated by R1+R6 pattern convergence; blocked on
  nothing; the event log is its only new artifact.
- **Graph & Knowledge Explorer** (C4+C3+C10): unblocked by R8's verified export;
  design guardrails from R3 (search-first, ego, provenance) and R4 (diff not
  animation); stack from R2.
- **Report & Evidence Studio** (C5+C11+C10-shared): fully specified by R5; the only
  soft spot is span anchoring, with a graceful fuzzy-match fallback.

Distinctness holds (live / graph / report = moments M1-M4 / M5 / M6-M7), the stack is
shared (one FastAPI app, three surfaces), and each is independently weekend-scale.
Formal scoring in `04-selection.md`.
