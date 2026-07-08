# Reflection — lessons learned & what I'd do differently

Date: 2026-07-07. Written after the design phase closed and while the pitch HTMLs
rendered. This is the honest retrospective on the *process*, not the designs.

## What actually happened (compressed)

Framework → data inventory (from code) → my own candidate brainstorm → 8 parallel
research agents → synthesis → rubric selection (3 use cases) → 3 case-study agents →
3 full design docs → 2 adversarial critique agents (UX + code-grounded feasibility)
→ decision pass on every finding → revised designs → 5 pitch/process/reflection
HTMLs built by agents reading the docs off disk. ~16 subagents total.

## What worked — keep doing

**1. The code-grounded skeptic was the single highest-value agent of the run.**
The feasibility critic read `sources.py`/`ingest.py`/`docs_pull.py` *and the four
real workspaces on disk*, and found things no amount of careful design would have
surfaced: `SourceStore.update` is a non-atomic truncate-then-write (torn reads
guaranteed); docs sources are born `scraped` and never distilled (71/88 in polars);
tool-graph reports cite `[synthesis/*.md]` not source ids (~5 vs 263 id citations);
the ingest manifest is hashes-only. Four design-breaking facts, all sitting in the
repo the whole time.

**2. Live verification beat documentation reading.** R8 probed the hosted tenant's
`openapi.json` and made real GET calls instead of trusting docs. It settled the
project's biggest unknown (graph export: yes, verified, 3k nodes in one call) and
killed a false assumption (INSIGHTS search type no longer exists). Two hours of
read-only probing changed the entire selection calculus.

**3. Brainstorming candidates *before* research landed.** `02-usecase-candidates.md`
was written while agents were still running, so the use-case space came from the
problem structure (moments × data shapes), not from whatever the agents happened to
find. Research then *validated* the bundles instead of dictating them — and where it
changed things (D5 demoted from fallback to preview layer), the delta was visible.

**4. Critique before pitch-building.** Two threatening and ~10 material findings got
fixed in the designs before a single line of pitch HTML existed. The pitches now
carry honest budgets (v1 estimates roughly doubled) and "what the critics said"
sections. Reversed order would have shipped confident wrongness.

**5. Docs-as-you-go made delegation cheap.** Because every phase wrote its artifact
to `docs/viz/`, the five HTML builders needed zero conversation context — just file
paths. The workspace, not the chat, was the source of truth. (This is, pleasingly,
the same lesson drc itself embodies.)

**6. Convergent evidence from overlapping agents.** R1 and R7 independently arrived
at the same architecture (local FastAPI, file-watch → SSE, zero storage); R1 and R6
independently arrived at master-detail + counts-not-percents. The overlap I'd
half-considered trimming became the strongest signal in synthesis: independent
agreement is worth its token cost.

## What went wrong — and the fixes

**1. I let a ground-truth doc go stale, and it poisoned a critique.** R8's findings
invalidated the central caveat of `01-data-inventory.md` ("graph export not
available — biggest feasibility unknown"), and I didn't circle back to update it.
The UX critic then built its most severe atlas finding on the stale sentence.
*Fix adopted mid-run and worth institutionalizing: when new evidence invalidates a
foundational doc, the update happens in the same turn as saving the evidence.*

**2. I designed against the models, not the data.** My data inventory came from
reading `models.py` and `workspace.py` — clean, correct, and misleading. The real
workspaces (which existed on disk the whole time!) held the distribution facts that
mattered: most sources in tool workspaces never pass through distill; real reports
vary wildly in citation density. The feasibility critic did the workspace profiling
I should have done in hour one. *Fix: the data inventory phase should include
profiling actual instances, not just schemas — a 20-minute script over `research/`.*

**3. Token-expensive relay of research docs.** Wave-1 agents returned full documents
in their final messages, which I then re-emitted verbatim into files — paying for
every research doc twice. The HTML wave fixed this (agents Write their own files,
return a 5-line summary). *Fix: any agent producing a >500-word artifact should
write it to disk itself; the coordinator gets a summary and spot-checks.*

**4. Spike-thinking arrived late.** The critique pass produced the consolidated
"1 day of spikes gates 3 weeks of builds" list — watcher torture test,
source_content_hash check, citation-coverage script, rapidfuzz hit-rate. All four
are runnable against data already on disk, and all four should have been *in the
design template* ("§5 must name the riskiest bet and the cheapest spike that retires
it"). The template has been amended in my head; it should be amended in the doc for
next time.

**5. Case studies were half-redundant.** Wave-2's three case studies produced real
value (the concrete screen anatomies and fictional walkthroughs fed the pitch
mockups directly, and CS2 uniquely verified Cognee's visualize template source), but
maybe 40% of their content restated wave-1 findings. *Fix: fold "include one
concrete walkthrough + exact screen anatomy of the single best exemplar" into the
wave-1 prompts, and reserve wave-2 for verification-style deep dives only.*

## If I ran this again — alternative approaches

**A. Data-first (would adopt).** Phase 0 becomes: profile the real workspaces with
scripts (status distributions, citation formats, file sizes, manifest shapes) and
probe the live API — *then* write the framework. Half the critique findings would
have been design inputs instead of design corrections.

**B. Prototype-first (would consider for mission only).** For a personal tool with
live data sitting on disk, a half-day throwaway cockpit spike might teach more than
two research agents. The rubric and market scan earn their cost for the *portfolio*
decision, but the watcher plumbing questions were always going to be settled by
code, not prose. A hybrid — research the selection, prototype the riskiest slice
during the design phase — is probably optimal.

**C. Structured outputs over free markdown (would adopt partially).** Findings-style
agents (critics, the API surveyor) could return schema-validated objects
(finding/severity/evidence/fix), making the decision pass mechanical instead of
editorial. Survey-style agents should stay free-form — their nuance is the value.

**D. Fewer, deeper agents (would not adopt).** Collapsing 8 wave-1 topics into 4
broader ones would halve coordination cost but lose the independence that made
convergence meaningful, and single agents skim when given two fields to cover.

**E. Interactive checkpoints (situational).** This run was fully autonomous by
request. With the user present, two checkpoints would have earned their
interruption cost: after selection (before three design deep-dives) and after
critique (the accepted-changes list rewrote real scope). Everything else was
better off autonomous.

## The uncomfortable question

Three pitches totaling ~3 weeks of build effort now exist for a personal tool whose
owner has a finite hobby budget. The critique's sharpest cross-cutting point — build
the **shared-chassis v0 week** and let usage decide which v1 exists — is really a
statement about this whole exercise: the research produced conviction about *shape*,
but only usage produces conviction about *value*. The honest summary of three weeks
of design work is: build one week of it, then look at which tab stays open.
