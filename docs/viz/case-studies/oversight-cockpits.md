# Case Study: Anatomy of Oversight Cockpits

> Wave-2 agent CS1. Saved verbatim, 2026-07-07. Feeds the **drc mission** design.

Three production UIs — Airflow's Grid view, Temporal's workflow detail page, and GitHub Actions' run page — have converged on a shared answer to the same question dr-cognee's run cockpit must answer: *how does one human supervise a machine executing dozens of parallel, failure-prone steps, without reading everything?* This case study dissects each, then maps their load-bearing elements onto the drc pipeline (harvest → scrape → distill → synthesize → ingest, tracked per-source in `sources.jsonl`).

## Why these three

Each exemplar dominates a different axis of the oversight problem:

- **Airflow Grid** is the best-in-class *dense status matrix*: hundreds of task×run states visible in one screen-width, color as the primary channel, detail deferred to hover and a sidebar. It answers "what is the overall shape of this run, and where are the anomalies?"
- **Temporal's workflow detail page** is the best-in-class *live in-flight introspection*: what is running *right now*, what attempt is it on, why did the last attempt fail, and when will it retry — plus four different zoom levels on the same event history. It answers "what is the machine doing at this instant, and is it stuck?"
- **GitHub Actions' run page** is the best-in-class *failure triage funnel*: errors are hoisted upward as annotations while raw logs stream downward, with failed steps auto-expanded so the eye lands on the problem without a single click. It answers "it broke — show me exactly where, immediately."

A drc run has all three needs simultaneously: ~30–80 sources marching through 4–5 stages (Airflow-shaped), one agent doing one thing at a time with retries and rate limits (Temporal-shaped), and per-source scrape/distill errors that must not be buried in a log (Actions-shaped).

## Exemplar 1: Airflow Grid view

**Screen anatomy.** The Grid view is a matrix: **each row is a task, each column is a DAG run**, newest runs at the right edge. Every cell is a small colored square encoding task-instance state (success green, failed red, running lime, up-for-retry gold, skipped pink, queued gray). Above the matrix, column headers carry per-run duration bars — a mini bar chart whose heights make slow runs visually protrude. A **details panel (sidebar)** occupies the right side: with nothing selected it summarizes the DAG; select a run-column or a task-cell and it swaps to that entity's tabs — logs, task duration across recent runs, mapped tasks, code. Controls along the top filter tasks by name/partial ID and set the run-range window (e.g. "last 25 runs"). Information density is the whole point: one 1080p screen comfortably shows ~40 tasks × 25 runs ≈ 1,000 states.

**Interaction grammar.** A strict hover→click→drill escalation. *Hover* a cell → tooltip with state, timestamps, duration, try number — zero navigation cost. *Click* a cell → the sidebar (not a new page) fills with that task instance's logs and actions (mark success/failed, clear for re-run). *Drill* via sidebar tabs for full logs or graph view. Crucially, the matrix never leaves the screen; context is preserved while detail rotates through the sidebar.

**Failure surfacing.** Failures are red squares in a mostly-green field — preattentive pop-out, no scanning required. Vertical red stripes mean "this run broke everywhere" (systemic); horizontal red streaks mean "this task breaks every run" (chronic). The matrix layout makes *pattern shape* diagnostic before any text is read.

**What Airflow 3 changed.** The 3.x UI is a full React rewrite: dark/light themes, redesigned navigation, and the Grid promoted even more firmly to the primary landing surface, with the details panel unified so run-level and task-level inspection share one consistent side-panel pattern rather than the 2.x mix of modals and page jumps.

**Design problems solved.** The cell solves *state legibility at scale* (color > text). The sidebar solves *drill-down without context loss*. The column duration bars solve *anomaly detection in the time dimension*.

**Weakness.** The Grid is nearly silent about *why*. A red cell tells you failure happened but the error text lives two interactions deep (click → logs tab → scroll). There is no hoisting of error messages to the matrix level — the opposite of Actions' annotations.

## Exemplar 2: Temporal workflow detail

**Screen anatomy.** The workflow detail page stacks: (1) a **header** with workflow ID, type, status badge, run ID, task queue, start/close times, duration, SDK, state-transition count; (2) **Input and Results** panels showing the workflow's arguments and return value as JSON; (3) the **Pending Activities panel** — a card list of activities currently in flight or backing off, each showing activity type, state (Scheduled/Started), **attempt count** (e.g. "Attempt 7"), the **last failure message** from the most recent attempt, and next-retry timing; clicking one opens the full Pending Activities tab; (4) the **Event History** section with **four switchable views**: **Timeline** (horizontal Gantt-like bars per activity/timer, clickable for detail), **All** (the complete flat event log — every `ActivityTaskScheduled`/`Started`/`Completed`/`Failed`), **Compact** (events logically grouped into one row per activity/signal/timer — the "what happened" digest), and **JSON** (raw, downloadable). At the list level, the UI supports **saved views** (up to 20 per user, filterable by status/ID/type/time/search attributes), including a pre-built **Task Failures view** surfacing workflows currently experiencing task failures or timeouts.

**Interaction grammar.** Escalation is by *representation*, not just by click: Compact for the gestalt, Timeline for duration shape, All for forensic ordering, JSON for tooling. Within any view, click an event → expandable detail with payloads. Pending Activities short-circuits all of this for the live case: no history spelunking needed to learn "attempt 7, last failure: 429 rate-limited, retrying in 40s."

**Design problems solved.** Pending Activities solves the single most anxiety-producing oversight question — *is it working or is it wedged?* — by making retry state a first-class panel rather than an inference from logs. The four-view history solves the "one rendering can't serve both skimming and forensics" problem. The Task Failures saved view solves triage-across-many-runs.

**Weakness.** No dense fleet overview. The detail page is superb for *one* workflow; across fifty, you get a paginated table of status chips, nothing like Airflow's matrix. And the All view is famously verbose — three-plus events per activity — which is exactly why Compact had to exist.

## Exemplar 3: GitHub Actions run page

**Screen anatomy.** Left rail: the **job list/graph** — every job with a status icon (green check, red X, amber spinner), and in graph view, dependency edges between jobs so you see what's blocked on what. Top of the main pane: the **run summary**, showing overall result plus an **Annotations block** — error and warning messages *hoisted out of the logs* ("Process completed with exit code 1", plus any `::error file=...,line=...` messages workflows emit), each deep-linking to the failing step. Below: the selected job's **step list**, each step a collapsible accordion row with status icon and duration. **Failed steps are automatically expanded** to show their output; passing steps stay collapsed. Logs support search (expanded steps only), per-line **permalinks** for sharing, timestamps, and ANSI color. While a job runs, its log pane **streams live**, tailing output — but the user can scroll back through earlier lines without losing the stream.

**Interaction grammar.** The page is a funnel: red job icon in the rail → click → failed step already open → error line already colored red → annotation at top already quoting it. In the common case the number of *required* interactions to see the error text is zero-to-one. Expansion state is the unit of attention: collapse what passed, expand what didn't.

**Design problems solved.** Auto-expand solves *time-to-error*. Annotations solve *error hoisting* — the summary answers "why did it fail" without entering logs at all. The job graph solves dependency comprehension. Live streaming with backscroll solves "watch it happen" without hostage-taking the scroll position.

**Weakness.** Poor cross-run and intra-run density: one job's logs at a time, no matrix of history, and the visualization graph is widely criticized (see the community discussion "GHA visualization graph considered harmful") as decorative — it consumes space without adding drill-down value. Long log steps also make search-only-in-expanded-steps a trap.

## Mapping table: exemplar element → drc cockpit

| Exemplar element | drc cockpit equivalent |
|---|---|
| Airflow grid cell (task × run, color = state) | **Source × stage cell**: rows = sources from `sources.jsonl`, columns = found → scraped → distilled → ingested; cell color = status, red = `error`, gold pulse = in-progress |
| Airflow hover tooltip | Hover a cell → url, title, category, `found_via`, relevance, `depth_flag`, timing, error string |
| Airflow sidebar details panel | Right-hand **source inspector** (wide-monitor budget): click a row → distilled record, raw-scrape excerpt, error detail; matrix never leaves screen |
| Airflow column duration bars | Per-stage progress/duration header: counts + elapsed per pipeline stage; a bulging distill bar = LLM slowdown |
| Airflow vertical vs. horizontal red patterns | Vertical red column = stage-wide breakage (e.g. Firecrawl key expired); scattered red in one category row-group = bad domain/source class |
| Temporal Pending Activities panel | **"Now" strip**: "agent is distilling `src_014` (arxiv.org/…) — attempt 2, last failure: 429, retry in 30s" — always visible, top of screen |
| Temporal attempt count + last failure | Per-cell retry badge and error tooltip fed by the `status`/`error` fields, distinguishing *retrying* from *dead* |
| Temporal Compact vs. All vs. JSON views | Agent event feed with three zooms: per-source digest / full tool-call log / raw JSONL download |
| Temporal Timeline view | Horizontal run timeline: bars per stage per source, exposing stragglers and rate-limit gaps |
| Temporal Task Failures saved view | One-click **"problems" filter**: matrix collapses to only sources with `status=error` or `relevance` below threshold |
| Actions error annotations (hoisted) | **Source-error strip** under the "Now" strip: "3 errors — src_007 scrape timeout · src_019 distill JSON parse · src_023 403" — each deep-links to its cell |
| Actions auto-expanded failed step | Opening an errored source auto-expands its failing stage's log section; healthy stages stay collapsed |
| Actions live streaming + backscroll | Tail of agent stdout/tool events, auto-follow with a "resume following" pill when the overseer scrolls back |
| Actions job dependency graph | Small stage-DAG chip showing pipeline order and current phase (mostly linear; kept minimal, heeding the GHA-graph weakness) |

## Walkthrough: 90 seconds back from coffee

**0:00** — She sits down. The "Now" strip reads: *distilling `src_031` — "Retrieval-augmented distillation survey" — attempt 1 — 12s elapsed*. Not wedged. Below it, the amber error strip says **2 errors**, so something happened while she was gone.

**0:10** — Eyes drop to the matrix filling the wide monitor: 46 rows, 4 stage columns. The scraped column is solid green; distilled is two-thirds green with a lime cell crawling downward — the live cursor of the agent. Two red cells, both in the distill column, both in the `blog` category band. Horizontal-pattern instinct: not systemic, source-specific.

**0:25** — She hovers the first red cell: `src_019 — distill error: model returned unparseable JSON — attempt 3/3`. Dead, not retrying. Hovers the second: `src_024 — 429 from provider — retrying at 14:32:10`. That one will heal itself; ignore.

**0:40** — Click on `src_019`. The matrix stays put; the inspector panel slides in with the distill stage auto-expanded — Actions-style — showing the truncated LLM response. She sees the scrape pulled a cookie-banner-polluted page; garbage in. She hits **mark skipped** (the Airflow-borrowed cell action) so synthesis won't wait on it, and flags `depth_flag` down.

**1:05** — Quick glance at the stage header bars: distill averaging 21s/source, 11 sources remaining ≈ 4 minutes to synthesis. The timeline zoom shows one straggler earlier — a 90-second distill on a PDF-heavy source — but nothing current.

**1:20** — She flips the event feed from Compact to the live tail for ten seconds, watches `src_032` get scheduled, scrolls back briefly to skim the 429 backoff messages, taps "resume following."

**1:30** — Verdict formed: one dead source (handled), one self-healing, pipeline on pace. She goes back to her other work, leaving the lime cell to keep crawling. Total clicks: two. Total log lines read: about fifteen.

## Sources

- [Airflow UI Overview (Grid view) — Apache Airflow stable docs](https://airflow.apache.org/docs/apache-airflow/stable/ui.html)
- [Temporal Web UI reference — docs.temporal.io](https://docs.temporal.io/web-ui)
- [Temporal Events and Event History — docs.temporal.io](https://docs.temporal.io/workflow-execution/event)
- [Temporal Activity Operations (pending activity state, attempts, last failure) — docs.temporal.io](https://docs.temporal.io/activity-operations)
- [Using workflow run logs — GitHub Docs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)
- [Using the visualization graph — GitHub Docs](https://docs.github.com/actions/managing-workflow-runs/using-the-visualization-graph)
- [GitHub Actions: Workflow visualization — GitHub Changelog](https://github.blog/changelog/2020-12-08-github-actions-workflow-visualization/)
- [GHA visualization graph considered harmful — GitHub community discussion #18035](https://github.com/orgs/community/discussions/18035)
