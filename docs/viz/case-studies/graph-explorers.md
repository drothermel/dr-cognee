# Case Study: Anatomy of Knowledge-Graph Explorers

> Wave-2 agent CS2. Saved verbatim, 2026-07-07. Feeds the **drc atlas** design.

## Why these three

The drc explorer sits at the intersection of three lineages. **Neo4j Bloom** (now "Explore" in Neo4j Workspace) is the reference design for *search-first, expand-on-demand* graph exploration by a domain user over an arbitrary property graph — exactly the interaction problem drc has, minus the multi-user enterprise baggage. **InfraNodus** is the reference for the opposite philosophy: *load everything, then let analytics — not the user — decide what is salient*. It is also the closest published analog to a drc dataset (a text-derived concept network of a few thousand nodes for one analyst). **Cognee's own `/visualize` HTML** is the incumbent: it defines the free baseline drc gets today, and its verified source pins down precisely which gaps the new explorer must close. Bloom answers "how do I navigate?", InfraNodus answers "what should I look at?", and Cognee's template answers "what do I already have?"

## Exemplar 1: Neo4j Bloom

**Screen anatomy.** Per the Bloom visual tour docs, the screen is one large canvas (the **scene**) with overlays: a top **search bar**, a **legend/style panel** listing categories and relationship types with rule-based styling, a **card list** overlay showing details for scene elements, and a left **sidebar** of drawers — the most important being the **perspective drawer**. A scene contains *only what you have searched for or expanded to* — never the whole database.

**Interaction grammar.**
- *Search-first entry:* the search bar takes near-natural-language pattern input with typeahead ("Person… KNOWS… Person"), and executing a pattern materializes matching subgraphs into the scene.
- *Search phrases:* named, parameterized aliases for pre-written Cypher, saved inside a perspective and invoked from the same search bar ("orders shipped to **$city**"). They give non-query-writers repeatable power queries.
- *Perspectives:* a domain lens over the same graph — which categories exist, which properties are searchable, styling rules, and which search phrases are available. One graph, many business views.
- *Expand-from-selection:* right-click a node → expand all neighbors, or expand along a chosen relationship type; also "reveal relationships" between scene nodes. Growth is incremental and user-driven.
- *Inspect:* click → card/inspect panel with all properties; slicer and filters scope what is visible; scenes can be saved, exported (PNG/CSV), and shared.

**Design problems solved.** The scene-not-database model solves *overload* (you never render 3k nodes unless you asked to). Search phrases solve *the query-literacy gap* by packaging expertise into reusable verbs. Perspectives solve *one-graph-many-questions*: the same nodes serve different investigations without re-modeling. Expand-from-selection makes exploration *reversible and local* — the frontier grows one decision at a time.

**One weakness.** Bloom has almost no *global* awareness: there is no overview of cluster structure or "what's in here that I haven't searched for." If you don't already know a good starting entity, the empty scene gives you nothing — a cold-start problem InfraNodus inverts.

## Exemplar 2: InfraNodus

**Screen anatomy.** A full-viewport force-directed text network on the left; a collapsible **analytics side panel** on the right with tabs for topics, keywords/influence rankings, structural gaps, and AI insight; a statement/text list linked to the graph; top controls for view modes.

**Interaction grammar.**
- *Topic-cluster overview:* concepts are nodes, co-occurrences are edges; community detection (modularity) colors topical clusters, force layout places them, and node size encodes **betweenness centrality** — so the biggest nodes are the junctions between themes, not merely the most frequent words. The first paint is already an answer: "your corpus is about these 4–6 things."
- *Analytics panel:* ranked influential concepts, topic lists (click a topic → the graph filters/highlights to that cluster and its underlying statements), and network-level structure metrics (biased / focused / diversified / dispersed discourse).
- *Structural gap detection:* an algorithm finds pairs of well-developed clusters that are poorly connected, highlights both, and offers to generate — manually or via built-in GPT — a research question or idea that would bridge them.
- *Subtractive exploration:* remove the top hub concepts to expose the "underlying" second-tier structure.

**Design problems solved.** InfraNodus's core move is turning a would-be hairball into *a list of claims*: "these are your topics, these are the brokers, here is what's missing." Cluster color + betweenness sizing solve *orientation at full-graph scale*; the graph↔statement linkage solves *provenance* (every node click surfaces the source sentences); gap detection converts topology into a *to-do item*, which is the rare case of a graph UI producing forward motion rather than description.

**One weakness.** It is single-lens: everything is one co-occurrence network at one abstraction level. There are no typed nodes, no schema, no way to say "show me documents vs. concepts" — so the analytics are powerful but the *navigation* vocabulary is thin compared to Bloom.

## Exemplar 3: Cognee's built-in visualize

Verified against the cognee repo (`topoteretes/cognee`, `cognee/modules/visualization/`). Two generations exist; the hosted `/api/v1/visualize` behavior confirmed live for drc — a self-contained d3.v7 force layout — matches the **classic template** (e.g. tag `v0.1.43`, `cognee_network_visualization.py`).

**Screen anatomy (classic template).** One full-window SVG. Every node is a fixed-radius circle (`r=13`) colored by a hard-coded type map — Entity `#f47710` orange, EntityType `#6510f4` purple, DocumentChunk `#801212` dark red, TextSummary `#1077f4` blue, unknown types light gray — with a 5px white name label on every node and 3px edge labels on every relationship. Data is embedded directly in the HTML as JSON. The physics: `forceManyBody(-275)`, weak link strength (0.1), centering forces.

**Interaction grammar — the complete list.** Pan/zoom (d3.zoom on the whole container), drag a node (pins during drag, releases after), and a browser-native tooltip: `node.append("title").text(d => JSON.stringify(d))` — the raw properties blob as hover text. That is everything. There is **no search, no filtering, no click-to-inspect panel, no type toggles, no legend, no provenance navigation** — and at drc scale (~3k nodes / 13k edges) SVG per-tick rendering of 3k text labels plus 13k edge labels is both a hairball and a frame-rate disaster.

**What it gives for free.** A zero-setup sanity check: did cognify run, are Entities attached to EntityTypes, roughly how big is the graph, are there disconnected islands. The type-color convention is genuinely useful and worth inheriting as a *convention* even while replacing the hexes.

**The newer main-branch template** (post-Oct-2025 refactor) shows Cognee's own diagnosis of these gaps: canvas rendering with a loading bar and minimap, a substring **search box** ("Enter jumps to match"), **label budgets** (Key/All/Off — "key" = landmarks + high-importance entities), three layouts (**Story**: pinned pipeline columns Documents→Chunks→Entities→Types→Summaries; **Flow**; **Force**), color-by Type/Node-set/User, a click **info panel**, a legend keyed to importance-weight sizing, plus separate Schema and Memory tabs. Its updated palette: TextDocument `#A550FF`, DocumentChunk `#0DFF00`, Entity `#6510F4`, EntityType `#D5C2FF`, TextSummary `#FFB454`, NodeSet `#94A3B8`. Even this version, though, has no expand-from-selection, no analytics (clusters/gaps), no saved views, and search is substring-jump, not query.

**One weakness (shared by both generations).** Everything-at-once: the entire graph is always rendered, so the display can only *style* the hairball, never *scope* it — the exact failure Bloom's scene model exists to prevent.

## Mapping table: exemplar element → drc explorer

| Exemplar element | drc explorer equivalent (using real drc data) |
|---|---|
| Bloom search bar (search-first entry) | Omnibox over node `label` + `properties.description`; Enter materializes the hit + 1-hop neighborhood into the scene, not the full 3k-node graph |
| Bloom search phrases | Canned traversals as chips: "provenance of *$entity*" (Entity → `DocumentChunk` → `TextDocument`), "entities in *$node_set*", "what links *$a* and *$b*" — parameterized graphology path queries |
| Bloom perspectives | **Node-set lenses**: `belongs_to_set` ∈ {docs, distilled, synthesis, report} as toggleable views — "report lens" shows synthesis/report-set nodes styled prominently, docs-set dimmed |
| Bloom scene + saved scenes | Sigma.js viewport holding only materialized nodes; serialize scene (node ids + camera) to URL hash / localStorage for one-user "scenes" |
| Bloom inspect panel / card list | Right rail: type badge, description, `importance_weight`, `topological_rank`, `belongs_to_set`, in/out edges grouped by label |
| Bloom expand-from-selection | Node context menu: expand all / expand by edge label / expand only Entity neighbors (skip chunk plumbing) |
| InfraNodus topic clusters | Louvain (graphology-communities) over the Entity–Entity projection; cluster color as an alternative to type color; cluster list in the analytics rail |
| InfraNodus betweenness sizing | Size Entities by degree or betweenness; fall back to Cognee's `importance_weight` when present |
| InfraNodus structural gaps | Pairs of Entity clusters never co-mentioned in any shared `DocumentChunk` → "gap card" that can seed the next drc research run |
| InfraNodus analytics panel | Left rail (the wide monitor fits three columns: analytics — canvas — inspector): topics, top brokers, orphan entities, per-node-set counts |
| Cognee type colors + Story columns | Keep color-by-type as default; **Entity/EntityType as zoom levels** — zoomed out, aggregate to EntityType meta-nodes; zoom in past a threshold to expand member Entities |
| Cognee `JSON.stringify` tooltip | Replaced by the inspector, but keep a raw-JSON disclosure at the bottom for debugging |
| (absent everywhere) provenance chain | Inspector "Sources" section walking Entity → mentioning `DocumentChunk`s → owning `TextDocument`, rendered as breadcrumbs; chunk/document nodes hidden from the canvas by default |

## Walkthrough: interrogating the pydantic tool graph

The user opens the explorer on the `pydantic` tool-graph dataset. The canvas is *not* a hairball: it shows ~40 EntityType meta-nodes sized by member count, colored by dominant node set. She types **"custom validators"** in the omnibox. Typeahead returns Entities whose label or description matches: `field_validator`, `model_validator`, `custom validation`, `Annotated validators`. She hits Enter on `field_validator`; the scene materializes it plus one hop — sibling validators, its `is_a` link to EntityType `Function/Decorator`, and edges like `applied_to → BaseModel field`, `runs_before → model_validator`.

She right-clicks `model_validator` → *expand by edge label* → `configures`, pulling in `mode="before"` and `mode="wrap"` entities. The analytics rail notes both nodes sit in the same Louvain cluster ("validation"), and flags a **gap card**: the "validation" cluster and the "serialization" cluster share no chunk co-mentions — a hint her docs harvest never covered `model_serializer` interactions with validators, i.e., a candidate follow-up drc run.

Clicking `field_validator`, the inspector shows its description, `importance_weight`, and a **Sources** breadcrumb: three DocumentChunks → `TextDocument: pydantic docs — validators.md (docs set)` and one → `synthesis` set. She switches to the **report lens**: docs-set plumbing dims, and only what survived into synthesis/report stays bright — instantly showing that `Annotated validators` made the report but `wrap validators` never did. She saves the scene to the URL and pastes it into her notes.

## Sources

- Neo4j Bloom docs: [Overview / visual tour](https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-overview/), [Search bar](https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/search-bar/), [Perspectives](https://neo4j.com/docs/bloom-user-guide/current/bloom-perspectives/bloom-perspectives/), [Search phrases](https://neo4j.com/docs/bloom-user-guide/current/bloom-tutorial/search-phrases-advanced/), [About Bloom](https://neo4j.com/docs/bloom-user-guide/current/about-bloom/)
- InfraNodus: [How it works](https://infranodus.com/about/how-it-works), [Text network analysis](https://infranodus.com/docs/text-network-analysis), [Paranyushkin, "InfraNodus: Generating Insight Using Text Network Analysis," WWW '19](https://noduslabs.com/wp-content/uploads/2019/06/InfraNodus-Paranyushkin-WWW19-Conference.pdf)
- Cognee source (verified via GitHub API): [`cognee/modules/visualization/cognee_network_visualization.py` @ v0.1.43](https://github.com/topoteretes/cognee/blob/v0.1.43/cognee/modules/visualization/cognee_network_visualization.py) (classic template: color map, force params, `JSON.stringify` tooltip); [`template.html` @ main](https://github.com/topoteretes/cognee/blob/main/cognee/modules/visualization/template.html) and [`preprocessor.py` @ main](https://github.com/topoteretes/cognee/blob/main/cognee/modules/visualization/preprocessor.py) (search box, label budgets, Story/Flow/Force layouts, updated `_TYPE_COLOR_MAP`)
