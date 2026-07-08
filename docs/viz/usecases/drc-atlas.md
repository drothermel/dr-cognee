# Design: drc atlas — the Graph & Knowledge Explorer

Use case 2 of 3. Design process per `00-framework.md` §8. Evidence base: research/
cognee-api-surface.md (live-verified), graph-exploration-ux.md, graph-viz-tools.md,
dynamic-graph-viz.md; case-studies/graph-explorers.md; synthesis §S1, §S4.

---

## 1. Goal, audience, context

**Goal.** Make a cognified topic graph *interrogable*: what does it know, how do
entities connect, what's the evidence behind any node, what changed since the last
cognify, and what's missing. Text answers stay primary (drc query); the atlas is the
verification, orientation, and serendipity layer around them.

**Audience & context.** Same single power user, wide monitor. Two workspace flavors
with different question profiles: deep-research topics ("how do Zep and Letta
relate?", "what supports this ranking?") and tool graphs ("what does the graph know
about custom validators?", "which controls exist?"). Used after cognify and across
the life of a topic (tool graphs especially are long-lived reference artifacts).

**Questions ranked:**
1. What does this graph know about X? (search → local structure + evidence)
2. What's the evidence behind this node/edge? (provenance)
3. What are the major themes, and what's thin/missing? (overview + gaps)
4. How do X and Y connect? (paths)
5. What did the last cognify change? (diff)

**Non-goals.** Not a Cypher IDE; not a graph editor (read-only over Cognee); not a
beautiful global render — the hairball is an explicit anti-goal (R3); no 3D.

## 2. Problems & constraints

**P1 — Scale vs legibility.** ~3k nodes / 13k edges verified for a mid-size dataset;
global hairballs fail past ~200 nodes. *Resolution:* Bloom's scene model — the canvas
holds only what was searched/expanded; overview is EntityType/community meta-nodes,
never raw nodes.

**P2 — Plumbing nodes pollute.** DocumentChunk/TextSummary/TextDocument are ~40% of
nodes but are provenance plumbing, not knowledge. *Resolution:* hidden from the
canvas by default; surfaced as the inspector's Sources breadcrumb (CS2 mapping).

**P3 — Graph↔workspace identity gap.** Cognee entities don't carry drc source ids;
the provenance chain ends at TextDocument. *Resolution:* join server-side —
TextDocument content ↔ `ingested.json` manifest ↔ source ids (the manifest records
exactly what text went in). Fuzzy title/hash match; degrade to "ingested artifact"
label when a join fails, never guess silently.

**P4 — Layout instability.** Force layouts differ per load; spatial memory dies.
*Resolution:* sigma.js/graphology with FA2 run once server-side per graph snapshot,
positions persisted in the snapshot JSON (R2's key differentiator).

**P5 — Freshness & cost.** Full export per page load is wasteful; hosted credits
matter for search. *Resolution:* `drc ingest` (or the dash server on demand) saves
`viz/graph-<n>.json` snapshots; atlas reads snapshots, with a "refresh from Cognee"
button. Query workbench calls are explicit user actions, never automatic polling.

**P6 — Trust in LLM-extracted structure.** Edges may be wrong. *Resolution:*
provenance-on-click everywhere; single-source edges visually thinner; "evidence"
is one click from any claim the graph makes.

## 3. UX flow

**Entry.** From the Topic Shelf or `/w/<slug>/atlas`. Landing state: **omnibox +
overview canvas** (EntityType/community meta-nodes sized by member count, colored by
dominant node set) + analytics rail. Never the full graph.

**Core loop — search, show context, expand on demand (R3):**
1. Type in omnibox → typeahead over labels + descriptions.
2. Enter → scene materializes: hit + ranked 1-hop context (~30-50 nodes, DOI-capped),
   focus node pinned center, radial layout.
3. Right-click frontier node → expand all / by edge label / entities-only.
4. Click node/edge → inspector: description, weights, node sets, edges grouped by
   label, **Sources breadcrumb** (Entity → chunks → document → drc source record →
   content file, each hop clickable; content opens in a slide-over with the chunk
   highlighted).
5. `Esc` clears back to overview. Scene state (node ids + camera) serialized to the
   URL hash — every view is a bookmarkable, pasteable artifact.

**Canned queries (Bloom search phrases), as chips under the omnibox:**
`evidence for <entity>` · `connect <a> ↔ <b>` (path mode: straight left-to-right
strand, 1-hop ghost context) · `what's in <community>` · `from source <id>` ·
`orphans & gaps`.

**Lens switching:** node-set chips (docs / distilled / synthesis / report) restyle
the scene — report lens dims docs-set plumbing to show "what survived into the
report" (CS2 walkthrough moment).

**Query workbench (docked bottom drawer, `q`):** a drc-query console — question box,
search-type tabs (GRAPH_COMPLETION / CHUNKS / SUMMARIES side by side), history list.
With `verbose: true` the retrieved triplets render as a **ghost overlay on the
scene** — the answer's subgraph, visually distinguished. "Ask about selection" on
any node pre-scopes the question (NotebookLM handoff pattern). This is the
text-primary / graph-verifies division of labor from R3.

**Diff mode (`d`):** pick two snapshots → union overlay, positions synchronized to
the newer snapshot (DyNet trick): green added / red ghost removed / amber changed /
gray unchanged, plus a "most rewired entities" ranked side list. Static, no
animation (R4's verdict).

**Gap/health panel (analytics rail, always visible):** orphan entities,
single-source claims, weakly-connected community pairs — each gap a card with a
"draft harvest query" copy button. The graph tells you where to research next.

## 4. UI design

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⌕ omnibox: "custom validators…"        chips: [evidence for…][connect…][community…][orphans&gaps] │
│ lenses: (docs)(distilled)(synthesis)(report)   snapshot: #4 2026-07-07 ▾  [diff d] [refresh ⟳]    │
├───────────────┬──────────────────────────────────────────────────────────┬────────────────────────┤
│ ANALYTICS     │  SCENE CANVAS (sigma.js, WebGL)                          │ INSPECTOR              │
│               │                                                          │                        │
│ communities   │        model_validator ──runs_before── field_validator   │ field_validator        │
│  validation 34│              │                             ╱   ╲         │ Entity · validation    │
│  serializ.  28│         configures                    applied_to  is_a   │ sets: docs, synthesis  │
│  config     21│              │                            │        │     │ weight .87 · rank 12   │
│  …            │        mode="before"              BaseModel   Decorator  │ ── edges by label ──   │
│ top brokers   │                                                          │ applied_to (3) ▸       │
│  BaseModel ▓▓▓│   (focus pinned · radial ego · frontier nodes hollow)    │ runs_before (1) ▸      │
│  validator ▓▓ │                                                          │ ── sources ──          │
│ gaps ⚠        │                                                          │ chunk#12 → validators. │
│  validation × │                                                          │ md (docs) → src_ab12   │
│  serializ. —  │                                                          │ [open content ▸]       │
│  [draft query]│                                                          │ raw json ▸             │
├───────────────┴──────────────────────────────────────────────────────────┴────────────────────────┤
│ QUERY WORKBENCH (q) — "how do validators interact with serialization?"                             │
│ [GRAPH_COMPLETION] [CHUNKS] [SUMMARIES]   answer text …        [overlay triplets on scene ◉]      │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Canvas:** sigma.js + graphology. Type palette inherited from Cognee's convention
  (Entity orange-family, EntityType purple-family) so the built-in visualize remains
  a legible fallback; community coloring as the alternate mode. Entity labels always
  on in scenes (≤50 nodes); meta-node labels in overview. Edge thickness = supporting
  chunk count (P6).
- **Overview:** EntityType meta-nodes (from `/schema/inventory` counts — available
  even before a full export) + Louvain communities on the Entity-Entity projection.
  Double-click a meta-node → expand members in place.
- **Inspector:** the provenance breadcrumb is the star; raw JSON disclosure at the
  bottom for debugging.
- **Path mode:** straight horizontal strand rendering, hop labels on edges, ghosted
  1-hop context; multiple alternative paths stacked vertically.
- **Diff mode:** union overlay + rewired list; side-by-side toggle available (wide
  monitor makes it free).

## 5. Operationalization

**Stack.** Same `drc dash` FastAPI chassis. Atlas page = one Jinja template + one
~600-line ES module (sigma, graphology, graphology-layout-forceatlas2,
graphology-communities-louvain from CDN). Server does: snapshot fetch/cache, FA2
positions (Python-side via graphology in node? no — run FA2 in a web worker
client-side on first load of a snapshot, then persist positions back via
`POST /w/{slug}/atlas/positions`), provenance joins, Cognee search proxy.

**Data plumbing.**
- `GET /w/{slug}/atlas/graph?snapshot=n` → snapshot JSON (nodes/edges + positions
  once computed + community assignments computed server-side with python-louvain
  or client-side graphology — pick client-side to keep Python deps zero).
- Snapshots: `viz/graph-<n>.json` written by "refresh" (server calls Cognee
  `/datasets/{id}/graph`) and optionally by `drc ingest` (S6.4, one small addition:
  a `--snapshot` flag).
- Provenance join table built server-side from `ingested.json` + sources.jsonl +
  content file hashes; served as `/w/{slug}/atlas/provenance/{node_id}`.
- Query workbench → existing `CogneeClient.search` + `verbose` param (small client
  addition: pass-through of `verbose`, `nodeName`, `topK`).
- Diff computed server-side: keyed by node label+type (ids are not stable across
  cognify runs — verify; fall back to label matching with a warning).

**Build phases.**
- **v0 (a weekend):** snapshot fetch + scene model (omnibox, materialize, expand,
  inspector with edges-by-label) + node-set lenses. No communities, no workbench.
- **v1 (+2-3 days):** overview meta-nodes + Louvain + analytics rail + provenance
  breadcrumb joins + query workbench + canned chips + URL scenes.
- **v1.5:** diff mode + gap cards + "ask about selection" + positions persistence.

**Risks.**
- *Node-id instability across cognify runs* would weaken diffs → mitigate with
  label+type matching; call out match confidence in the diff UI.
- *Provenance join failures* (manifest text vs TextDocument mismatch) → show the
  chain as far as it resolves; log join misses to a debug panel rather than hiding.
- *Hosted API drift* (endpoints verified today, unversioned) → pin expectations in
  one `cognee_client` test that validates response shapes against recorded fixtures;
  a failed shape check shows a clear banner in the atlas instead of breaking silently.

**Effort estimate.** v0 ≈ 2 days; v1 ≈ +3 days; v1.5 ≈ +2 days. New code isolated in
`dr_cognee/dash/atlas*` + one `--snapshot` flag on ingest + `verbose` pass-through
in cognee_client.

## 6. Revisions (post-critique — supersedes §1-5 where they conflict)

Full decisions in `../05-critique-response.md`. Design-changing items:

- **D5 layer added.** The local entity co-occurrence graph (distilled/*.json) is the
  pre-cognify layer and the empty state — same scene UI, "local preview" banner.
  Cognee snapshots are the enhanced mode.
- **Layout resolved.** FA2 runs client-side in a web worker on first snapshot load;
  positions persist back into the snapshot; overview + diff consume them; ego scenes
  use radial layout seeded from stored positions.
- **Scenes are queries, not id lists.** URL hash serializes {search, expansion steps
  by label+type+edge, lenses, camera}; re-resolved on load; survives re-cognify.
- **Diff is scene-scoped.** Global entry = the "most rewired entities" list; the
  canvas diff renders only the scoped neighborhood. No full-graph union overlay.
- **Provenance plan reordered.** 2-hour spike first: check `source_content_hash`
  against ingested.json digests (may collapse the join to a dict lookup). Else: v1
  joins stable keys (docs/distilled/content) by re-hash; synthesis/log/report show
  "revision unknown"; orphan TextDocuments labeled "superseded revision" and
  excluded from counts by default. Pipeline recommendation upgraded: record Cognee
  data-id in ingested.json at push time.
- **Lens chips derived** from `belongs_to_set` values present in the export (all six
  sets, incl. content and log), never hardcoded.
- **Workbench:** tabs fire lazily (one billed search per explicit click, cost
  counter shown); `CogneeClient.search` gains verbose/nodeName/topK + 402 mapping;
  dash proxies Cognee async with per-route timeout + error banner.
- **Snapshots** gzipped + property-stripped; diff computed server-side.
- **Honest budget:** v0 ≈ 2 days (incl. D5 layer); **v1 ≈ +5 days**. Build order:
  atlas is 3rd of 3; the provenance breadcrumb and gap cards are its explicit
  survival criteria.
