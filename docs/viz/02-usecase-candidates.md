# Use-case candidates — my brainstorm (pre-research)

Written before wave-1 research lands, so selection isn't anchored on whatever the
agents happen to find. Each candidate: the moment(s) it serves (M1-M7 from
00-framework.md), data it consumes (D1-D10), and a gut read against the rubric.
Final scoring happens in 04-selection.md after research.

## Candidates

### C1. Run Cockpit (mission control)
Live dashboard for an in-flight run. Status board (counts by status × category ×
facet), live activity feed derived from watching sources.jsonl diffs ("3 new sources
from query X", "src_ab12 scraped→distilled"), log.md narrative pane, error strip,
cognify progress. **M1 M2 M4 · D1 D2 D10.** Gut: high decision value, all data
available (needs watcher-derived events), moderate build. The "trust the agent"
surface.

### C2. Triage Desk
Between-iteration cockpit: depth-flag queue with depth_note + distilled preview,
facet × category coverage heatmap, keyboard-fast source table, errors. Possibly a
"steering note" composer appending to log.md for the agent to read. **M3 · D1 D4 D6.**
Gut: this is where the human actually changes the run's direction — top decision value.

### C3. Entity Emergence Map
Live local entity co-occurrence graph built from distilled/*.json as distill runs —
the knowledge graph *preview* before Cognee. Recurring entities ranked; "deserves a
targeted query" candidates surfaced. **M2 M5 · D4 D5.** Gut: cheap, novel, perfect
provenance (entity → source ids); doubles as fallback if hosted graph export is weak.

### C4. Graph Explorer
Post-cognify KG explorer: search-first entry, ego-network expansion, community/
node-set lenses, provenance panel (node/edge → supporting artifacts). **M5 · D7 (+D5
fallback).** Gut: the headline "explore the graph" ask; feasibility gated on R8.

### C5. Evidence-Linked Report Reader
report.md rendered with citations resolved: hover evidence cards, tri-panel
report | distilled takeaways | full source content, claim-strength badges
(evidenced-use vs marketing per claims_of_use), gap honesty surfaced. **M6 · D9 D4 D3
D1.** Gut: directly serves the final artifact; wide-monitor tri-panel is a natural fit.

### C6. Run Replay
Post-hoc scrubber replaying a run: status transitions, entity graph growth, log
narrative synced on one timeline. **M7 · D1-history D2 D5.** Gut: charming, lower
decision value; needs an event log captured during the run (same watcher as C1 —
cheap if C1 exists, expensive alone).

### C7. Coverage Radar
Saturation & coverage analytics: new-vs-seen per harvest round (the loop-until-dry
curve made visible), sources per facet × category matrix, thin-coverage alerts,
query-yield table. **M1 M3 · D1 (found_via parsing).** Gut: strong steering value;
probably a *panel* inside C1/C2 rather than a standalone tool.

### C8. Synthesis Diff Viewer
Per-facet synthesis with iteration-over-iteration diffs — "what changed in
understanding". **M3 M7 · D6 (needs snapshotting; git or watcher copies).** Gut:
lovely but thin alone; a panel, not a product.

### C9. Graph Diff / Cognify Delta
Before/after comparison across cognify runs: added entities/edges, merged nodes.
**M4 M5 · D7 snapshots.** Gut: gated hard on R8 (export twice + diff); high wow,
uncertain feasibility.

### C10. Query Workbench
Interactive query console over the topic dataset: history, side-by-side search types
(GRAPH_COMPLETION vs CHUNKS vs INSIGHTS), answers linked back to sources, saved
verification question sets. **M5 M6 · D8 D7.** Gut: cheap (search API is wired
today), high knowledge-exploration value, pairs naturally with C4 or C5.

### C11. Tool Capability Atlas (tool-graph mode)
For per-tool graphs: the capability map as an interactive browser — every control/
flag/env var as a scannable, searchable index with doc pointers; extension points;
ecosystem. **M5 M6 · D6 D9 D1(docs).** Gut: the most *useful daily artifact* of
tool-graph runs, but it's really a rendering of synthesis docs — may fold into C5.

### C12. Topic Shelf
Home screen across research/ workspaces: every topic, status, counts, links into the
other tools. **M7 · all, shallow.** Gut: trivial to build, zero standalone value —
the navigation chrome around whichever tools win.

### C13. Harvest Inspector
Query-matrix forensics: which queries surfaced what, dupe rates, found_via Sankey.
**M1 · D1.** Gut: subsumed by C7.

### C14. Ambient Pulse
Tiny always-on-top strip/menu-bar widget: run heartbeat, stage, error count.
**M1.** Gut: off-brief (not a web canvas use), noted for completeness.

## Emerging bundles (likely shape of the top 3)

The candidates cluster into three natural products, which conveniently cover
live / graph / report:

- **A. Live Run Cockpit** = C1 + C2 + C7 (+C8 as a panel, +C6 replay as a stretch).
  One surface with two modes: watching (live) and steering (triage).
- **B. Graph & Knowledge Explorer** = C4 + C3 + C10 (+C9 stretch). Entity-first
  exploration with the local co-occurrence graph as the always-available layer and
  the Cognee graph when available; query workbench docked.
- **C. Report & Evidence Studio** = C5 + C11 (+C10 shared). The reading/verification
  surface for the run's outputs.

Selection confirmed/adjusted after wave-1 research in 04-selection.md.
