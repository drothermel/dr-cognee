# Design: drc mission — the Run Cockpit

Use case 1 of 3. Design process per `00-framework.md` §8. Evidence base: research/
live-observability.md, corpus-triage-ux.md, local-webapp-stack.md; case-studies/
oversight-cockpits.md; synthesis §S2, §S3.

---

## 1. Goal, audience, context

**Goal.** One screen that lets Danielle supervise and steer an in-flight drc run —
deep-research or tool-graph — without reading everything, and triage the corpus
between iterations.

**Audience & context.** One power user on a very wide (~3800px usable), fairly tall
monitor. During a run the *agent* operates `drc`; the human tabs in every few minutes.
The cockpit therefore optimizes for the **re-engagement moment**: "I've been away —
what happened, is anything stuck, where should I steer next?" A run lasts tens of
minutes across phases (harvest → scrape → distill → synthesis → ingest/cognify),
touching 20–300 sources.

**Questions the screen must answer, ranked:**
1. Is the agent working right now, or wedged? (trust)
2. What broke while I was away? (errors)
3. What changed since I last looked? (delta)
4. Where is coverage thin / which depth flags matter? (steering)
5. What is the run learning? (knowledge pulse)

**Non-goals.** Not a control panel for running drc commands (the agent does that);
not a log viewer replacement (raw logs are an escape hatch, not the surface); not
post-hoc analytics (that's a later mode, not v1).

## 2. Problems & constraints

**P1 — No timestamps in SourceRecord.** `sources.jsonl` is a state document, not an
event stream. *Resolution:* the cockpit's watcher mints `viz/events.jsonl` by diffing
keyed snapshots on every file change (S2). History exists only from the moment the
cockpit first watches a workspace — acceptable for a live tool; noted honestly in the
UI ("observed since 14:02").

**P2 — sources.jsonl is rewritten, not appended.** Tailing corrupts. *Resolution:*
full reparse on change, id→hash diff, semantic transition events (R7's plumbing
pattern, verbatim).

**P3 — Unknown totals during fan-out.** Harvest keeps growing the denominator.
*Resolution:* counts-by-state, never percent bars (R1 pattern 8).

**P4 — Steering has no channel.** The human can see but not redirect without
switching to the agent chat. *Resolution:* v1 ships read-only triage + a "copy
steering note" affordance (composes a markdown directive block to paste at the
agent); v1.5 adds `viz/directives.jsonl` that the skill instructs the agent to read
between iterations (S6.3). The design must work fully without the directives file.

**P5 — Zero-maintenance bias.** No DB, no build step, no daemon beyond `drc dash`.
*Resolution:* FastAPI + watchfiles + SSE + htmx; state lives in the workspace and
in browser localStorage (last-seen timestamp).

**Constraint summary:** all data from D1-D6 + D10 (inventory doc); Cognee touched
only for cognify status; wide canvas is mandatory, multi-monitor irrelevant.

## 3. UX flow

**Entry.** `uv run drc dash` → browser at `localhost:7317` → Topic Shelf home (list
of workspaces under research/, live badge on any workspace with recent file
activity). Click a topic → the cockpit. Deep-linkable: `/w/<slug>/mission`.

**Primary loop (watching):** glance top strip (Now panel + funnel + error strip) →
if all green, leave. Target: <5 seconds to the "all fine" verdict.

**Re-engagement loop (the flagship):** on tab focus, "since you left" badges light
up: new-source dots on grid rows, count chips on queue tabs ("+6 distilled · 2
errors"), a highlighted segment on the activity sparkline for the away period.
Pressing `Esc` (or clicking the badge chip) marks-all-seen and stores the new
last-seen timestamp.

**Triage loop (between iterations):** switch from Watch to Triage with `t`. Queue
tabs (zero-target): `Depth flags (7)` `Errors (3)` `Unreviewed high-rel (4)`
`Thin facets (2)`. Within a queue: `j/k` moves the row cursor (detail pane follows),
verbs act and auto-advance — `c` chase (adds to steering note), `x` dismiss flag,
`r` retry-suggest, `s` skip-suggest, `z` snooze, `n` free-text note. A rolling
last-10-decisions strip at the bottom is click-editable (undo). `Enter` on the
steering-note composer copies the assembled directive block.

**Failure drill:** error strip entry → click → grid scrolls to the cell, detail pane
opens with the failing stage auto-expanded (Actions pattern), raw log section lazy-
loaded below.

**Exit.** Nothing to save; close the tab. Server keeps watching (cheap); the
localStorage timestamp makes the next visit's delta correct.

**State diagram (modes):**

```
            ┌────────────┐   t   ┌────────────┐
  Shelf ───▶│   WATCH    │◀─────▶│   TRIAGE   │
            │ (default)  │       │ (queues)   │
            └─────┬──────┘       └─────┬──────┘
                  │ click error/cell   │ j/k/verbs
                  ▼                    ▼
            ┌──────────────────────────────┐
            │  INSPECT (detail pane focus, │
            │  grid stays; Esc returns)    │
            └──────────────────────────────┘
```

## 4. UI design

**Canvas plan (3840×1600 reference).** Three vertical bands under a full-width top
strip. The grid band scrolls vertically (sources); the timeline strip (v1.5) scrolls
horizontally. Fira Code for all data text; color is the primary state channel.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NOW ▶ distilling src_031 "RAG survey…" attempt 1 · 12s   │ found 46 → scraped 41 → distilled 29 →  │
│ activity ▁▂▅▃▁▁▇▂ (since-you-left segment highlighted)   │ ingested 0 · skip 3 · ⛔ 2 ERRORS ────▶ │
├──────────────┬────────────────────────────────────────────────────────┬────────────────────────────┤
│ FACET RAIL   │  SOURCE × STAGE GRID                    [Watch|Triage] │  INSPECTOR                 │
│              │  ── grouped by facet, category bands ──                │                            │
│ category ▾   │        F  S  D  I    rel  ⚑  title                     │  src_019  practitioner     │
│  web    18   │  ────  ●  ●  ●  ○    hi   ⚑  Zep in production…       │  ─ takeaways (5) ─         │
│  github 11   │  ────  ●  ●  ◐  ○    med     Agent memory bench…      │  • replaced bespoke……      │
│  docs   88   │  ────  ●  ●  ⛔  ○    —      Blog: LLM stacks…         │  • …                       │
│ facets ▾     │  ────  ●  ◌  ·  ·    —      HN thread: graphrag       │  ─ claims_of_use (2) ─     │
│  memory  12  │   (● done ◐ running ◌ queued ⛔ error · not-yet)       │  • "we run this for…"      │
│  eval     3⚠ │                                                        │  ─ error / raw log ─       │
│ found_via ▾  │  QUEUE TABS (Triage): Depth ⚑7 · Err 3 · HiRel 4      │    (auto-expanded when     │
│  q1 yield 9  │  last-10 verbs: c c x z c … (editable undo strip)      │     entered via error)     │
├──────────────┴────────────────────────────────────────────────────────┴────────────────────────────┤
│ LOG NARRATIVE (log.md tail, rendered md)   │ ENTITY PULSE: top recurring entities ▎bar; new bold   │
└────────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

Panel specs:

- **Now panel** (top-left): current agent action inferred from the latest event
  (e.g. a source flipping to `scraped` implies scraping phase), elapsed since last
  event, and a stall warning (amber >90s without any file event during an active
  phase; "possibly waiting on cognify" during ingest). Cognify: dataset status
  polled via the server every 15s while `ingested.json` is newer than last poll.
- **Funnel strip:** counts-by-state, each count a click-filter on the grid. Skips
  and errors always visible, never folded into "done."
- **Error strip:** hoisted, red, newest-first, each entry deep-links to its cell.
- **Grid:** rows = sources (newest first within facet groups), columns = the four
  stages. Cell tooltips carry url/found_via/relevance/error. Category color-bands on
  the row edge make "all the reds are blogs" readable as a shape (CS1's
  vertical/horizontal pattern diagnostic). Row density ~28px; 50 rows visible.
- **Facet rail:** Flamenco-style counts (query previews) for category, facet,
  status, relevance, found_via yield; ⚠ marks thin facets (below coverage
  threshold). Every count is a filter; no zero-result clicks.
- **Inspector:** renders the DistilledRecord as formatted content (takeaways,
  entities as chips, claims_of_use called out), never raw JSON; error text + lazy
  raw-log accordion at the bottom.
- **Log narrative:** rendered markdown tail of log.md — the agent's own voice,
  the trust channel.
- **Entity pulse (C3-as-panel):** top-N recurring entities across distilled records,
  bar = source count, bold = first seen since last visit. Click → filters grid to
  sources mentioning it. This is the "what is it learning" answer and the seed of
  the atlas's pre-cognify preview.

**Visual language.** Dark theme; state palette: green done, lime pulsing running,
gray queued, pink skip, red error, gold retry. Since-you-left = violet dot. All
counts tabular-lined Fira Code. No percent bars anywhere.

## 5. Operationalization

**Stack** (R7 primary): FastAPI + Jinja2 + htmx(SSE ext) + Alpine.js; sse-starlette;
watchfiles; served by `drc dash` (new Typer subcommand). Graph/sparkline rendering:
inline SVG from the server (no chart lib). No build step; htmx/alpine vendored.

**Data plumbing.**
- `WorkspaceWatcher` (new module `dr_cognee/dash/watcher.py`): holds Pydantic
  snapshots per artifact; on `awatch` batch → semantic events; appends to
  `<workspace>/viz/events.jsonl`; fans out to SSE subscribers.
- Event model: `{ts, kind: source_added|status_changed|distilled|synthesis_updated|
  log_appended|ingest_manifest|error, source_id?, from?, to?, detail?}`.
- Server routes: `/w/{slug}/mission` (page), `/w/{slug}/events` (SSE),
  `/w/{slug}/fragment/{panel}` (htmx partials), `/w/{slug}/cognify-status`
  (Cognee proxy). Directives (v1.5): `POST /w/{slug}/directives` appends jsonl.
- Client state: only `lastSeen` in localStorage; everything else server-rendered.

**Build phases.**
- **v0 (a day):** watcher + events.jsonl + funnel strip + grid + inspector, 2s SSE
  refresh, no triage mode. Already answers questions 1–2.
- **v1 (a weekend):** Now panel, error strip, facet rail, log narrative, entity
  pulse, since-you-left badges, Watch/Triage modes with j/k + verbs writing a
  steering-note block. Answers all five questions.
- **v1.5:** directives.jsonl contract + one paragraph added to the two skills
  ("between iterations, read viz/directives.jsonl if present"); timeline strip
  (per-source stage waterfall from events.jsonl); cognify-status widget.

**Risks & mitigations.**
- *Stall inference wrong* (agent thinking ≠ wedged): label the warning "no file
  activity for 90s," never "stuck" — report the observable, not the diagnosis.
- *Event log gaps* (cockpit not running during part of a run): the grid is always
  correct (state-based); only deltas/timeline degrade. UI states "observed since T."
- *Directive contract drift*: keep directives schema one Pydantic model shared by
  dash writer and (future) drc reader; version field from day one.

**Effort estimate.** v0 ≈ 1 day; v1 ≈ 2–3 days; v1.5 ≈ 1–2 days. All pure additions
to the repo (`dr_cognee/dash/`), no changes to existing pipeline modules until v1.5's
one-line skill edits.

## 6. Revisions (post-critique — supersedes §1-5 where they conflict)

Full decisions in `../05-critique-response.md`. Design-changing items:

- **Triage persists.** `viz/directives.jsonl` moves to v1; every verb appends a
  directive record; queues derive from sources ⊖ directives. No lost triage work.
- **Grid & funnel are per-category lanes.** Docs sources are born `scraped` and skip
  distill (verified in docs_pull.py/ingest.py): docs lane = pulled → pushed; web lane
  = found → scraped → distilled → pushed. Last column is **pushed**, derived from
  `ingested.json` keys, with an explicit status-vs-manifest disagreement state.
- **Watcher hardening.** `viz/` excluded from the watch filter; parse-failure/shrunk
  file = retry, never phantom removals; events.jsonl rotates (10MB × 2). Accepted
  pipeline change: `SourceStore.update` gains atomic tmp-write+rename.
- **Keymap.** Esc = dismiss topmost pane only; mark-all-seen = explicit badge click.
  Thin facets leave the queue tabs (facet-rail ⚠ + add-to-steering-note only).
- **Now strip** includes the latest log.md line (the agent's own voice up top).
  Stall threshold scales per last-event-kind (distill default 180s).
- **Cognee widget** lazy + degrades to "not configured"; dataset id cached.
- **Honest budget:** v0 ≈ 1 day; **v1 ≈ 5–6 days**; pre-build spike: ½-day watcher
  torture test against a real workspace.
- **Pitch frame:** the durable core is grid + queues + since-you-left delta —
  the things a chat transcript is bad at; v0 scopes to exactly that.
