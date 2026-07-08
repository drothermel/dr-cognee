# dr-cognee

The repo currently contains:
1. An attempt to use Firecrawl to do a deep research pass, ingest it into the Cognee graph and improve it before finally returning a report.
2. A almost entirely autonomous research flow for ways to visualize the complex workflow and output.

## Results

All outputs, including for intermediate steps, can be found in [docs/viz](docs/viz).  And html reports listed below need to be downloaded and then opened in the browser to view.
- **Research Process Report**: [research-process.html](docs/viz/reports/research-process.html)
- **Proposal 1: Process Execution Viewer**: [drc-mission.html](docs/viz/reports/drc-mission.html)
- **Proposal 2: Graph Explorer**: [drc-atlas.html](docs/viz/reports/drc-atlas.html)
- **Proposal 3: Report Viewer**: [drc-dossier.html](docs/viz/reports/drc-dossier.html)
- **Process Reflection**: [reflection.html](docs/viz/reports/reflection.html)

## Pull Relevant Turns from Logs
```bash
jq -r '
    def emit($label; $body):
      "",
      ("#-  " + $label + "  "),
      "",
      $body,
      "";

    if .origin.kind? == "human" then
      emit("  USER   "; (.message.content?, .attachment.prompt?) | select(. != null))
    elif any(.. | strings; . == "end_turn") then
      emit("ASSISTANT"; .message.content[]? | select(.type? == "text") | .text? // empty)
    else
      empty
    end
  ' ~/.claude/projects/-Users-daniellerothermel-drotherm-repos-dr-cognee/f462a1da-3482-4d29-be8d-46a8bc2621e3.jsonl | sed 's/# /## /g' | sed 's/#- /# /g'
```


## Conversation

###    USER     

Please review the changes on this branch + the notes in docs/ and describe what is currently being built


###  ASSISTANT  

##### What's being built: `dr-cognee` — a research-to-knowledge-graph pipeline, now growing a "tool graph" mode

This branch essentially contains the whole project (main has almost nothing before it — the 11 commits add ~4,900 lines). It builds up in two waves.

###### Wave 1: the `drc` deep-research pipeline (earlier commits)

Per the approved design spec (`docs/superpowers/specs/2026-07-07-deep-research-cognee-design.md`), the goal is a repeatable pipeline where an agent researches a topic and leaves behind both a deep-research-grade report *and* a queryable hosted-Cognee knowledge graph, rather than a one-shot answer. The architecture is "Toolbox + Playbook":

- **Toolbox** — a Typer CLI (`drc`, in `src/dr_cognee/`) operating on a per-topic workspace directory (`research/<slug>/` with `topic.yaml`, `log.md`, `sources.jsonl`, `content/`, `distilled/`, `synthesis/`, `report.md`). Commands: `init`, `harvest` (Firecrawl search fan-out with URL dedup), `scrape`, `add-source`, `distill` (one LLM call per source producing structured takeaways/entities/`claims_of_use`/depth flags), `ingest` (push to a per-topic hosted Cognee dataset + cognify), `query`, `status`. Everything is idempotent and resumable via per-source status transitions (found → scraped → distilled → ingested).
- **Playbook** — the `deep-graph-research` skill (`docs/skills/deep-graph-research/SKILL.md`), which supplies the agent's judgment: facet decomposition, a breadth-sweep query matrix, an interleaved distill-and-deepen loop, critic subagents as a feedback gate, then ingest and a graph-enriched report.

A mid-branch commit also swapped the distill LLM provider to OpenAI (`gpt-5.4-nano` default) with a `--provider` option.

###### Wave 2: the tool-graph flow (the last two commits — the current focus)

A second use of the same machinery: instead of researching an open question, build a dedicated knowledge graph for **one tool or library** (its capabilities, controls, extension points, usage patterns) sourced primarily from official docs rather than web search. This added:

- **`drc pull-docs`** (`src/dr_cognee/docs_pull.py`) — pulls docs directly without Firecrawl, via two vendored mirror modules (from dr-notion): an **llms.txt manifest mirror** and a **GitHub docs-tree mirror** (git sparse checkout). Pulled pages are registered as `category=docs` sources, already `scraped`, deduped by URL.
- **The `tool-graph` skill** (`docs/skills/tool-graph/SKILL.md`) — the playbook: init with tool-shaped facets → probe for `llms.txt` / locate the GitHub docs tree → `pull-docs` → small targeted Firecrawl gap-fill harvests → per-facet "capability map" synthesis → ingest, verify with graph queries, write `report.md`.
- **Two fixes from the live pilot** (top commit): the llms mirror now follows off-origin links (pydantic's manifest lives on `docs.pydantic.dev` but links to `pydantic.dev`, so the pull initially registered 0 sources), and `drc distill` now skips `docs`-category sources (docs are ingested whole under a `docs` node set — the pilot would otherwise have burned 88 pointless LLM calls).

###### The uncommitted notes (`docs/notes/`, currently untracked)

`2026-07-07-tool-graph-pilot.md` is a running log of the first real run: a **pydantic pilot** that worked end-to-end (88 docs via llms.txt + 2 gap-fill harvests + synthesis + ingest + verification queries), the two iteration findings that became the top commit, open watch items (cognify time at ~100 items; whether the `docs` node-set separation is usefully queryable in Cognee), and an **llms.txt availability probe** for the next candidate tools — pydanticAI, cognee, Codex CLI, and Claude Code have manifests; polars doesn't and will need the GitHub-docs fallback.

So in one sentence: the branch built the `drc` deep-research → Cognee pipeline, and the work in flight is its second application — per-tool knowledge graphs pulled directly from official docs — with the pydantic pilot done and a queue of tools (polars, pydanticAI, cognee, Codex CLI, Claude Code) lined up next.


###    USER     

great! so now, I'd like you to brainstorm what types of visualization tools would be useful to let a user view whats going on during the deep research (or, in the future pass, during the tool research) and the graph updating etc.  And then to explore the results, both the graph itself and the knowledge it carries and the report that is produced from a request.

Do an extensive brainstorm process that starts by making your own docs/viz subdir and writing a framework for how you'll think thorugh this systematically and do market research for different ideas and best methods for visualization and ux of those methods + how to operationalize them.  Then orchestrate subagents to actually do the research and some of the brainstorming (or you can own that part) and make documents as you go for coherent topics, clean case studies and examples, logs of the investigation, etc.  Then choose 3 top usecases to really spec out.  and for each of them, do a full design process from clarifying the goal and audience and context, to defining the problems that need to be solved and the constraints, to designing the ux flow, to designing the ui, to designing the operationalization.  the final result at the end of this should be 3 clean reports (as html files) that pitch the three ideas separate + one that layous out the full research process at a high level + the result of reflecting on your process and coming up with lessons learned and alternative approaches you would have taken if you did this again.  Make the html pages for someone wiht a very wide monitor (thats pretty tall too) so it can really use the full canvas and scroll in multiple directions.

Does this request make sense? before doing any more exploration and you recap what I'm asking you for?


###  ASSISTANT  

Enjoy the walk! No discussion needed — everything is clarified and I'm executing through the full task autonomously.

**Status so far:**
- `docs/viz/` created with the framework (`00-framework.md`: data shapes D1–D10, lifecycle moments M1–M7, evaluation rubric, design template), a code-grounded data inventory (`01-data-inventory.md`), my own pre-research brainstorm of 14 candidate use cases (`02-usecase-candidates.md`), and a running investigation log.
- **8 research agents are running in parallel** covering: pipeline/agent-run observability tools, graph viz libraries, graph exploration UX, dynamic/growing graph viz, provenance & citation UX, corpus triage UX, local web-app stacks, and the critical feasibility question — what graph data hosted Cognee can actually serve.

As they report back I'll save the research docs, run wave-2 case studies, score and pick the top 3 use cases, run the full design process on each, and finish with the 5 wide-canvas HTML reports in `docs/viz/reports/`.


###  ASSISTANT  

Waiting on the two critics before revising the designs and building the HTML deliverables.


###  ASSISTANT  

Inventory doc corrected. Waiting on the feasibility skeptic before revising all three designs in one pass.


###  ASSISTANT  

Log is current. Four HTML builders still rendering (mission, atlas, process, reflection) — I'll verify all five files and wrap up when they land.


###  ASSISTANT  

Atlas pitch landed (1,248 lines, verified tag-balanced). Two pitches done, three builders still rendering (mission, process overview, reflection).


###  ASSISTANT  

Reflection report done (1,130 lines). Still rendering: the mission pitch and the process overview.


###  ASSISTANT  

Process overview done (1,430 lines, with the 11-stage horizontal timeline). Only the mission pitch remains.


###  ASSISTANT  

#### Done — the full brainstorm ran end-to-end while you were out 🥾

**The five deliverables are in `docs/viz/reports/`** — open them in a browser (they're self-contained, designed for your wide monitor, dark theme, Fira Code):

- **`drc-mission.html`** — pitch 1: the **Run Cockpit**. Live local dashboard for an in-flight run: a source×stage grid with per-category lanes, a "Now" panel, hoisted errors, "since you left" delta badges, and keyboard-verb triage queues that write steering directives for the agent. Build first (v0 ≈ 1 day).
- **`drc-dossier.html`** — pitch 2: the **Report & Evidence Studio**. Citation chips with hover evidence cards, gwern-style always-visible margin notes, tri-panel claim→distilled-record→highlighted-passage verification, USE/vendor valence badges, a weakest-first audit table, and a "Controls" capability index for tool graphs. Build second.
- **`drc-atlas.html`** — pitch 3: the **Graph Explorer**. Search-first (never the hairball), ego scenes with expand-on-demand, node-set lenses, provenance-on-click down to your content files, a docked query workbench, and scene-scoped cognify diffs. Build third, gated on a 2-hour spike.
- **`research-process.html`** — the whole investigation as a horizontally-scrolling 11-stage timeline, findings gallery, scoring table, and artifact map.
- **`reflection.html`** — honest retro: what worked, what went wrong, five alternative approaches with verdicts.

**How it got there** (all traceable in `docs/viz/` — 29 artifacts): framework + data inventory → my own 14-candidate brainstorm → **8 parallel research agents** → synthesis → rubric selection → **3 case-study agents** → 3 full design docs → **2 adversarial critics** → every finding adjudicated and the designs revised → 5 HTML builders.

**Three findings worth knowing even if you read nothing else:**
1. **Hosted Cognee serves full graph export** — verified live: `GET /api/v1/datasets/{id}/graph` returned 3,033 nodes / 13,189 edges in one call. The graph explorer went from "biggest unknown" to fully unblocked.
2. **The code-grounded critic found real design-breakers**: `SourceStore.update` is a non-atomic rewrite (torn reads for any watcher), docs sources never pass through distill (71/88 in polars), and tool-graph reports cite `[synthesis/*.md]` with only ~5 source-id citations vs 263 in the deep-research report. All three designs were revised accordingly.
3. **The critique's best cross-cutting advice**: rather than committing to ~3 weeks across all three v1s, build a **shared-chassis v0 week** (grid+inspector, local co-occurrence scene, citation chips+hover cards) and let usage decide which v1 exists. There's also a ~1-day pre-build spike list in `05-critique-response.md` that gates everything.

One process confession, documented in the reflection: I let `01-data-inventory.md` go stale after the live API verification landed, and a critic built its most severe finding on the stale sentence — fixed, and logged as a lesson.

