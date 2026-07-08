# Viz brainstorm — investigation log

Append-only. Newest at bottom.

## 2026-07-07

- **Setup.** User confirmed scope: viz for live drc runs + result exploration (graph,
  knowledge, report). Audience: Danielle, personal tooling. Form factor bias: local
  web app. Research depth: substantial (~8-15 subagents). Deliverables: 3 use-case
  pitch HTMLs + process HTML + reflection HTML, designed for a very wide/tall monitor.
- **Grounding.** Read models.py / workspace.py / cognee_client.py. Key findings:
  workspace is fully file-based (watchable for free); SourceRecord has no timestamps
  (live timelines need a watcher-derived event log or a drc change); hosted Cognee
  client wraps only add_text/cognify/status/search — no graph export wired; entities
  in distilled/*.json form a locally-derivable co-occurrence graph before Cognee runs.
- **Framework written** (00-framework.md): data shapes D1-D10, moments M1-M7, method
  space, 8-agent research plan (R1-R8), selection rubric, design template.
- **Wave 1 launched.** 8 parallel research agents: R1 live observability, R2 graph
  viz tools, R3 graph exploration UX, R4 dynamic graph viz, R5 provenance/citation UX,
  R6 corpus triage UX, R7 local web-app operationalization, R8 Cognee API surface.
- **Wave 1 complete** (~5-8 min each, all 8 saved to research/). Headline findings:
  - **R8 (decisive):** hosted Cognee serves full graph export — verified LIVE:
    `GET /datasets/{id}/graph` → 3,033 nodes / 13,189 edges JSON; also `/visualize`
    (self-contained d3 HTML), `/schema/inventory`, and `verbose:true` search returning
    triplet objects. INSIGHTS search type no longer exists. Graph explorer unblocked.
  - **R1+R7 converge on architecture:** local FastAPI + watchfiles → SSE → htmx
    panels, zero storage, CDN ES-module graph libs, Cognee proxied server-side.
    Key plumbing rule: never tail rewritten JSONL — diff keyed snapshots into events.
  - **R3:** search-first (not overview-first), ego views, community meta-nodes,
    provenance-on-click; global hairballs empirically fail past ~200 nodes.
  - **R4:** for change comprehension, static diffs beat animation (controlled
    studies); animation only for "what just appeared" live monitoring.
  - **R5:** passage-anchored citations are THE fast/painful divider; hover cards,
    tri-panel, valence badges, gap markers.
  - **R6:** triage = keyboard verbs + auto-advance + zero-target queues; human
    output should be *directives to the agent*, not statuses.
  - **R2:** sigma.js + graphology (MIT, Louvain+FA2+persistable layout) primary pick;
    cosmograph for max wow (CC-BY-NC fine for personal use).
- **Synthesis written** (03-synthesis.md): S1-S7, incl. the ranked pipeline upgrades
  (event log, citation spans, directives queue, graph snapshot on ingest).
- **Selection done** (04-selection.md): portfolio = **drc mission** (Run Cockpit),
  **drc atlas** (Graph & Knowledge Explorer), **drc dossier** (Report & Evidence
  Studio) — one shared FastAPI chassis, three surfaces. Cut: standalone replay,
  ambient pulse, standalone synthesis diff.
- **Wave 2 launched:** 3 case-study agents (oversight cockpits: Airflow/Temporal/
  GH Actions; graph explorers: Bloom/InfraNodus/Cognee-visualize; evidence readers:
  NotebookLM/Elicit/gwern).
- **Wave 2 complete**, all saved to case-studies/. Notable: CS2 verified Cognee's
  actual visualize template source (classic d3 SVG: pan/zoom/drag + JSON.stringify
  tooltip only — no search/filter/inspect; newer main-branch canvas template adds
  search/label budgets/Story layout but still renders everything-at-once). The
  built-in baseline is precisely characterized; scene-model explorer is the clear
  differentiator.
- **Design docs written** (usecases/): drc-mission.md, drc-atlas.md, drc-dossier.md —
  each following the full template (goal/audience → problems & constraints → UX flow
  → UI wireframe → operationalization with v0/v1/v1.5 phases, risks, estimates).
  Shared chassis: one `drc dash` FastAPI app, watcher-minted events.jsonl,
  localhost surfaces per workspace.
- **Critique pass launched:** two adversarial reviewers — a UX/product critic
  (flows, canvas use, complexity-vs-brief, cross-surface coherence, strongest
  skeptic objection) and a feasibility skeptic (design-vs-code contradictions
  against models/workspace/ingest/sources.py, effort realism, failure modes,
  riskiest bets + cheapest spikes). Designs will be revised before the HTML pitches
  are built.
- **Critiques landed** (saved verbatim to critique/). Highlights: UX critic's most
  severe atlas finding traced to MY stale 01-data-inventory.md (predated R8's live
  verification — fixed, lesson logged); feasibility skeptic checked the real
  workspaces and found genuine design-breakers: `SourceStore.update` is non-atomic
  truncate-then-write (torn reads); docs sources are born `scraped` and never
  distilled (71/88 in polars); tool-graph reports cite `[synthesis/*.md]` with ~5 id
  citations vs 263 in the deep-research report; ingest manifest is hashes-only (no
  data-id), breaking the naive provenance join.
- **Decision pass written** (05-critique-response.md): every finding adjudicated;
  nearly all accepted; key changes — directives.jsonl pulled to mission v1,
  per-category grid lanes, "pushed" derived from manifest, atomic-write pipeline
  fix accepted, atlas gains the D5 pre-cognify layer + scenes-as-queries +
  scene-scoped diffs, dossier parses synthesis-pointer citations + docs-source
  cards + valence ladder (Admiralty grades CUT), shared keymap + one provenance
  service + viz/ file contract. Consolidated pre-build spike list (~1 day) gates
  everything. §6 Revisions appended to all three design docs.
- **Deliverable build:** 5 HTML agents launched, each reading the docs off disk and
  writing its file directly (lesson from wave-1 token relay applied). Shared design
  language: dark, Fira Code / Space Grotesk / Source Serif 4, ~3400-3700px wide-
  canvas grids, horizontal filmstrip strips, per-report accent colors. dossier
  (1,275 lines) landed first.
- **Reflection written** (06-reflection.md): 6 keepers, 5 failures-with-fixes,
  5 alternative approaches (data-first: would adopt; prototype-first: consider;
  structured outputs: partial; fewer-deeper: no; checkpoints: situational), and
  the closing thesis: build the shared-chassis v0 week, let usage pick the v1.
- **DONE.** All 5 HTML deliverables landed in reports/ and verified (well-formed,
  wide-canvas): drc-mission.html (1,443 lines), drc-dossier.html (1,275),
  drc-atlas.html (1,248), research-process.html (1,430), reflection.html (1,130).
  Final tally: 29 artifacts in docs/viz/, 16 subagents (8 research + 3 case-study
  + 2 critics + 5 builders... minus the coordinator's own docs). Recommended build
  order: mission → dossier → atlas, gated by the ~1-day spike list in
  05-critique-response.md.
