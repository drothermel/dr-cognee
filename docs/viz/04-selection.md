# Use-Case Selection — rubric scoring and the top 3

Date: 2026-07-07. Inputs: candidates from `02-usecase-candidates.md`, rubric from
`00-framework.md` §7, evidence from `research/` + `03-synthesis.md`.

## Scoring

Scale 1-5. Criteria: **DV** decision value · **DA** data availability · **BC** build
cost (5 = cheapest) · **MD** maintenance drag (5 = lightest) · **WC** wide-canvas
payoff. (Distinctness is applied at portfolio level, not per-row.)

| Candidate | DV | DA | BC | MD | WC | Σ | Notes |
|---|---|---|---|---|---|---|---|
| C1 Run Cockpit | 5 | 5 | 4 | 4 | 5 | 23 | Event log derivable by watcher (S2); patterns fully converged (S3) |
| C2 Triage Desk | 5 | 4 | 4 | 4 | 5 | 22 | Directives queue needs a small agent-contract addition (S6.3) |
| C3 Entity Emergence Map | 3 | 5 | 4 | 4 | 4 | 20 | Strong as a *panel*; thin as a standalone product |
| C4 Graph Explorer | 5 | 5 | 3 | 4 | 5 | 22 | Unblocked by R8's verified export; guardrails from R3 keep scope sane |
| C5 Evidence Report Reader | 5 | 4 | 4 | 4 | 5 | 22 | Spans need fuzzy-match fallback (S5); otherwise all data on disk |
| C6 Run Replay | 2 | 3 | 3 | 4 | 4 | 16 | R4: replay is theater; cheap only once C1's event log exists |
| C7 Coverage Radar | 4 | 5 | 5 | 5 | 3 | 22 | Best as panels inside C1/C2 — not distinct enough alone |
| C8 Synthesis Diff | 3 | 3 | 4 | 4 | 3 | 17 | Needs snapshotting; a panel, not a product |
| C9 Graph Diff | 4 | 4 | 3 | 4 | 4 | 19 | Enabled by S6.4 snapshot-on-ingest; belongs *inside* C4 |
| C10 Query Workbench | 4 | 5 | 5 | 5 | 4 | 23 | Cheapest high-value item; belongs inside C4 (and links from C5) |
| C11 Tool Capability Atlas | 4 | 4 | 4 | 4 | 4 | 20 | A rendering mode of C5 for tool-graph workspaces |
| C12 Topic Shelf | 2 | 5 | 5 | 5 | 2 | 19 | Navigation chrome; include for free in whatever ships |
| C13 Harvest Inspector | 3 | 5 | 5 | 5 | 3 | 21 | Subsumed by C7 panels |
| C14 Ambient Pulse | 2 | 4 | 4 | 4 | 1 | 15 | Off-brief (not the web canvas) |

## The portfolio decision

Raw scores cluster the winners exactly along the bundle lines predicted in
`02-usecase-candidates.md` and confirmed in `03-synthesis.md` §S7. Applying the
distinctness rule (cover live + graph + report — the user's three named targets):

### ✦ Use case 1 — **Run Cockpit** (C1 + C2 + C7, with C3 as a live panel)
*The live-oversight surface.* Watch an in-flight run (grid, Now panel, activity feed,
log narrative), triage between iterations (depth-flag/error/thin-facet queues with
keyboard verbs), steer the agent (directives queue), and watch knowledge accumulate
(entity emergence mini-map). Moments M1-M4 + M7.

### ✦ Use case 2 — **Graph & Knowledge Explorer** (C4 + C10, with C9 as a diff mode, C3 shared)
*The graph surface.* Search-first Cognee graph explorer with community overview, ego
workhorse view, node-set lenses, provenance-on-click down to source files, docked
query workbench with side-by-side search types, and cognify-to-cognify diff. Moment M5.

### ✦ Use case 3 — **Report & Evidence Studio** (C5 + C11, sharing C10's query pane)
*The reading surface.* Report reader with citation chips, hover evidence cards,
tri-panel claim→distilled→source verification, valence badges (USE/VENDOR/SECONDHAND),
gap markers, claim-table audit mode; renders tool-graph workspaces as a capability
atlas. Moments M6 + M6-adjacent.

**Shared chassis** (from S2): one `drc dash` FastAPI app; the three use cases are
three surfaces on the same watcher/event-log/Cognee-proxy foundation. C12 Topic Shelf
becomes the app's home screen for free.

**Explicitly cut:** standalone replay (C6 — revisit once the event log has accumulated
real runs), ambient pulse (C14 — off-brief), standalone synthesis diff (C8 — a cockpit
panel if it earns it later).

## Names for the pitches

1. **drc mission** — the Run Cockpit
2. **drc atlas** — the Graph & Knowledge Explorer
3. **drc dossier** — the Report & Evidence Studio
