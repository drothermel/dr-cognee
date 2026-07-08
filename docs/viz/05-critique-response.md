# Critique Response — decisions on every finding

Date: 2026-07-07. Inputs: `critique/ux-critique.md`, `critique/feasibility-critique.md`.
Verdicts: **ACCEPT** (design changed as suggested) · **MODIFY** (changed differently) ·
**REJECT** (with reason). Each design doc gains a "§6 Revisions" section encoding the
accepted changes; where §6 conflicts with §1-5, §6 wins.

## Meta-finding first

The UX critic's "atlas stands on unverified endpoints" was a **stale-doc artifact**:
`01-data-inventory.md` predated R8's live verification and was never updated. Fixed —
the inventory now records the verified endpoints. Lesson for the reflection doc: when
a research finding invalidates an earlier ground-truth doc, update the doc in the same
breath. The critic's residual point (no D5 fallback layer in atlas) stands and is
accepted below.

## Mission

| Finding | Verdict | Decision |
|---|---|---|
| Triage verbs don't persist (threatening) | **ACCEPT** | Pull the directives file forward to v1 as `viz/directives.jsonl`; every verb appends a directive record (dismiss/snooze are directives to the *dashboard* with the same schema); queues derive from sources ⊖ directives |
| Esc overload: mark-all-seen vs dismiss (material) | **ACCEPT** | Shared keymap: Esc = dismiss topmost pane, everywhere, always; mark-all-seen = explicit badge-chip click only |
| Thin facets as a queue tab (material) | **ACCEPT** | Thin facets live in the facet rail (⚠ + one "add to steering note" action); queue tabs are source-shaped only |
| Trust channel buried (minor) | **ACCEPT** | Latest log.md line renders inline in the Now strip; the full narrative pane stays at bottom |
| Watcher self-watch + unbounded events.jsonl (material, both critics) | **ACCEPT** | `viz/` excluded from the watch filter; events.jsonl rotates at 10MB (keep last 2) |
| Torn reads of sources.jsonl (threatening) | **ACCEPT** | Two-sided fix: watcher treats parse-failure/shrunk-file as retry-after-debounce (never emits removals from a failed parse); AND `SourceStore.update` gains atomic tmp-write+rename — an accepted 3-line pipeline change (the "pure additions" promise is amended, not silently broken) |
| Funnel/grid wrong for tool-graph workspaces (material) | **ACCEPT** | Per-category lanes: docs lane = pulled → pushed; web lane = found → scraped → distilled → pushed; funnel rendered as counts-by-state per lane |
| "Ingested" status vs manifest truth (material) | **ACCEPT** | Grid's last column = **pushed**, derived from `ingested.json` keys; status-vs-manifest disagreement surfaces as a distinct cell state, not hidden |
| Stall threshold cries wolf on distill (minor) | **ACCEPT** | Threshold per last-event-kind (distill: 3× median distill gap observed this run; default 180s) |
| Cognee env KeyError / dataset-id write (minor) | **ACCEPT** | Lazy client; widget degrades to "not configured"; dataset id cached after first resolve |
| v1 effort 2-3d is fantasy | **ACCEPT** | Re-budgeted: v1 = 5-6 days |
| Skeptic: chat window competes | **MODIFY** | Not a design change but a pitch reframe: the cockpit's durable core is the grid + queues + delta (things a linear chat transcript is bad at); v0 scopes to exactly that; Now/feed panels are cheap by-products of the watcher, not the value claim |

## Atlas

| Finding | Verdict | Decision |
|---|---|---|
| No D5 fallback / empty state (threatening→material after doc fix) | **ACCEPT** | The local entity co-occurrence graph is the atlas's **pre-cognify layer and empty state**: same scene UI, data from distilled/*.json, banner "local preview — cognify to get the full graph." Cognee snapshots are the enhanced mode |
| FA2 server/client self-contradiction (material) | **ACCEPT** | Resolved: FA2 runs client-side in a web worker on first snapshot load; positions POSTed back into the snapshot file; consumed by overview + diff; ego scenes use radial layout seeded from stored positions |
| URL scenes break on re-cognify (material) | **ACCEPT** | Scenes serialize as `{search, expansions: [(label,type,edge-label)...], lenses, camera}` — re-resolved on load; a missing label degrades to a note, not a broken link |
| Diff mode reintroduces the hairball (material) | **ACCEPT** | Diff is scene-scoped; the global "most rewired entities" ranked list is the entry point (click → scoped diff scene around that entity) |
| Workbench triple-billing (minor) | **ACCEPT** | Search-type tabs fire lazily, one explicit click each; per-run cost counter in the drawer |
| Pre-export overview needs edges (minor) | **ACCEPT** | Types-only overview until a snapshot exists, labeled as such |
| Provenance join built on hash-only manifest (threatening) | **ACCEPT** | Ordered plan: (1) 2-hour spike — check `source_content_hash` against `ingested.json` digests on existing datasets; if it matches, the join is a dict lookup; (2) else v1 joins stable keys (docs/distilled/content) by re-hash; synthesis/log/report render "ingested artifact (revision unknown)"; (3) pipeline recommendation upgraded: record Cognee data-id (or pushed-text snapshot) in `ingested.json` at push time |
| Orphan TextDocuments from add-only re-pushes (material, same cluster) | **ACCEPT** | Orphans (documents with no manifest match) are labeled "superseded revision" in lenses and excluded from counts by default, toggleable |
| Lens chips hardcode 4 of 6 node sets (material) | **ACCEPT** | Chips generated from `belongs_to_set` values present in the export |
| Search 402/params/async (material) | **ACCEPT** | `CogneeClient.search` gains `verbose/nodeName/topK` + 402→`CogneeCreditsError`; dash proxies Cognee on async httpx with per-route timeout + error banner |
| Snapshot size on tool graphs (minor) | **ACCEPT** | Snapshots gzipped, unrendered properties stripped, diff computed server-side |
| v1 effort +2-3d understated | **ACCEPT** | Re-budgeted: v1 = +5 days (provenance layer is the bulk) |
| Skeptic: graph browsing is the weakest-demand job | **MODIFY** | Concede in the pitch: atlas is ranked 3rd of 3 for build order; its two earn-their-keep features (provenance breadcrumb, gap cards) are named as the survival criteria, and the spike gates the investment |

## Dossier

| Finding | Verdict | Decision |
|---|---|---|
| Tool reports don't cite ids (threatening) | **ACCEPT** | `[synthesis/<facet>.md]`-style pointers parsed as first-class citations (chip → capability index section); tool-graph skill amended NOW with the one-line id-citation contract; the 1-hour citation-coverage script runs against the four existing reports before build |
| Docs sources have no DistilledRecord (material) | **ACCEPT** | Docs-source card defined: title, URL, found_via, first-heading excerpt from content file; docs excluded from valence (shown as "docs" chip, not SECONDHAND) |
| VENDOR heuristic uncomputable (material, both critics) | **ACCEPT** | Valence ladder: (1) parse the report's own `[vendor]`/`[practitioner]` labels when present (the agent already writes them); (2) computable proxies (category, docs-domain); (3) unlabeled → no badge, never a guessed one. Subject-entity inference dropped |
| Claim extractor cries wolf (material) | **ACCEPT** | v1 gap markers only on ranking-section sentences with zero citations; vocabulary expands only after observing real reports; parse-coverage stat kept but relabeled "indexed sentences" |
| Admiralty grades = complexity creep (material) | **ACCEPT** | Grades cut entirely; valence badge + source count remain; audit table's weakest-first sort carries the corroboration signal |
| Fuzzy-match viability asserted, not tested (material) | **ACCEPT** | The rapidfuzz spot-test against an existing workspace gates v0; the distill `quote`-span change is upgraded from "recommendation" to **prerequisite for the exact-highlight tier** (fuzzy remains the fallback tier, expectations labeled) |
| Dead canvas in Read mode (minor) | **ACCEPT** | Evidence panel idle state = strongest evidence for the current viewport |
| URL normalization before join (minor) | **ACCEPT** | Report URLs pass through `normalize_url` |
| Recomputation storms (minor) | **ACCEPT** | Cache keyed per (citation, content mtime) |
| Tool-mode effort hidden (+2→+4) | **ACCEPT** | Re-budgeted; tool mode acknowledged as a second evidence model |
| Skeptic: reports are read once | **MODIFY** | Pitch reframe: read/audit is per-run value; the *retention* claim moves to the capability index ("Controls" tab), which is promoted from v1.5 to v1 for tool workspaces |

## Cross-cutting

| Finding | Verdict | Decision |
|---|---|---|
| "Atlas" tab name collision | **ACCEPT** | Dossier's tab renamed **Controls** |
| Esc semantics diverge | **ACCEPT** | One keymap doc in the chassis spec: Esc = dismiss topmost pane everywhere; scene-clear (atlas) = explicit ⌫ button/`⇧Esc`; mark-seen (mission) = badge click |
| Two provenance chains can disagree | **ACCEPT** | One `provenance.py` service in the chassis; both surfaces consume it; single confidence vocabulary: `exact` / `fuzzy(ratio)` / `revision-unknown` / `unresolved` |
| viz/ dir is unmanaged shared state | **ACCEPT** | Chassis contract: every viz/ file has a `version` field; retention rules (events 10MB×2, snapshots keep last 5); single watcher owns invalidation; documented in one chassis page |
| Portfolio busts weekend budget; M7 unserved | **MODIFY** | Pitch structure adopts **shared-chassis v0 week**: watcher+events+grid+inspector (mission v0) + D5 scene (atlas v0) + chips+hover cards (dossier v0) ≈ 1 week total; usage decides which v1 gets built next. M7 (retrospective) stays cut for now — the event log accumulates the data so a future replay/retro tool is possible; noted honestly in the pitches rather than stretched into a fourth use case |

## Pre-build spike list (consolidated, ~1 day total)

1. **Watcher torture test** (½ day): awatch vs scripted SourceStore.update loop on a
   real workspace; count parse failures/phantom events. Gates mission.
2. **source_content_hash join check** (2h): compare graph-export hashes against
   ingested.json digests on the existing datasets. Decides atlas provenance design.
3. **Citation-coverage script** (1h): id-regex + normalized-URL + synthesis-pointer
   extraction over the four existing report.md files. Gates dossier scope split.
4. **rapidfuzz hit-rate** (1h): takeaway→content match ratios on
   agent-graph-knowledge-base. Sets dossier highlight-tier expectations.
