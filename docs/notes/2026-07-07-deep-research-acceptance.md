# Deep-research acceptance run — findings

Run: "Agent Graph Knowledge Base" question, workspace `research/agent-graph-knowledge-base`,
dataset `agent-graph-knowledge-base`. 128 sources found, 101 distilled+ingested (soft budget
of 80 exceeded deliberately after critic gate found gaps). Cognify completed; final report at
`research/agent-graph-knowledge-base/report.md` (ranked options per category with source map).

## Verdict

The flow produced a deep-research-grade report: ranked packaged solutions (Graphiti #1,
Cognee #2, neo4j-labs/agent-memory, CORE, LightRAG/HippoRAG), managed services, MCP memory
servers, and component stacks, with vendor-claims vs practitioner-evidence labeling and an
explicit thin-coverage section. Critic gate demonstrably improved coverage (Vertex AI,
memory-poisoning security, A2A, Mem0 graph-removal primary sourcing were all critic finds).

## Did the graph add value?

Modest yes: GRAPH_COMPLETION stitched cross-facet comparisons (temporal models across tools,
risk-per-integration-pattern matrix) faster than raw notes. But graph answers embellished
beyond sources (invented/marketing-sourced "case studies"), so the agent correctly used the
graph as organizer/cross-check and kept report claims grounded in distilled records.
SUMMARIES added little over synthesis files.

## drc/skill improvement backlog (from run friction — not yet implemented)

1. `dataset_status` poll during ingest can crash on transient 503 — add bounded retry on
   the status poll; also "push ok, poll failed" messaging. Re-run after a poll crash prints
   `cognify: no changes` which misleads (manifest saved, cognify state unknown).
2. Depth flags never clear once resolved — `drc status` list only grows. Add a resolved
   marker (e.g. `drc resolve-flag <id>` or auto-clear when a follow-up source cites it).
3. Query output ergonomics: SUMMARIES returns raw node JSON with IndexSchema noise;
   GRAPH_COMPLETION returns one huge markdown string inside JSON — add `--plain` rendering.
4. Distilled records carry no facet attribution — status can't show per-facet source counts.
5. Skill: add default skip-list (youtube/facebook/linkedin/reddit rarely scrapeable or
   worth it) and a warning that `--tbs qdr:m` surfaces vendor content-marketing heavily.
6. Cosmetic: `topic.yaml` created date is UTC (off-by-one vs local evening).
7. Scrape failures in run: 4, all reddit.com (Firecrawl unsupported) — consistent with
   pilot runs.
