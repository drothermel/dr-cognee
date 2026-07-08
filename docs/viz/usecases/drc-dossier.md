# Design: drc dossier — the Report & Evidence Studio

Use case 3 of 3. Design process per `00-framework.md` §8. Evidence base: research/
provenance-report-ux.md; case-studies/evidence-first-readers.md; synthesis §S5;
tool-graph skill contract (docs/skills/tool-graph/SKILL.md).

---

## 1. Goal, audience, context

**Goal.** Make the run's outputs *trustworthy and usable*: read report.md with
verification approximately free, audit any claim down to the source passage, see at
a glance which claims rest on real usage evidence vs marketing, and (for tool-graph
workspaces) use the synthesis as a living capability atlas.

**Audience & context.** Same single power user, wide monitor. Two reading modes with
different postures: **read** (linear, after a run: is this report right? what's the
recommendation?) and **audit** (skeptical, spot-checking: which claims are thin?).
Tool-graph workspaces add a third, long-lived posture: **reference** (months later:
"what were pydantic's serialization controls again?").

**Questions ranked:**
1. Can I trust this sentence? (claim → evidence, ≤2 interactions)
2. Which claims are thin or vendor-only? (valence at a glance)
3. What does the evidence actually say, in context? (full-source verification)
4. Where are the honest gaps? (rendered, not buried in prose)
5. (tool mode) What are the controls/extension points, with doc pointers?

**Non-goals.** Not an editor for report.md (the agent writes reports; the human
annotates); not a general markdown previewer; no cloud rendering — everything reads
local files.

## 2. Problems & constraints

**P1 — No citation spans.** Reports cite `[src_ab12]`-style ids (per skill contract
"source pointers (id → URL)"), but nothing anchors a claim to a passage.
*Resolution ladder (S5):* (a) v1 renders takeaway-level evidence — the cited
source's DistilledRecord is the hover card — and fuzzy-matches takeaway text against
the content file for scroll-to-highlight (accept imperfect matches, show a "≈"
marker when confidence is low); (b) recommend the pipeline upgrade: distill emits a
`quote` span per takeaway/claim (one schema field + one prompt line), which makes
highlighting exact. The design must be fully useful at level (a).

**P2 — Citation format variance.** report.md is agent-written; id citation syntax
may vary run to run. *Resolution:* tolerant extraction — match known source ids
anywhere in the text (they're short hashes, collision-unlikely); also linkify bare
URLs that match sources.jsonl. Uncited paragraphs are detected by absence.

**P3 — Valence isn't labeled per citation.** distilled records separate
`claims_of_use` from `takeaways`, but a *citation* isn't classified. *Resolution:*
derive: a citation of source S supporting a usage claim gets USE valence when S's
claims_of_use is non-empty and the claim text aligns (fuzzy); VENDOR when S's URL
domain matches the subject entity's domain (vendor self-description); SECONDHAND
otherwise. Badges carry a tooltip explaining the derivation — derived signals must
be inspectable, never oracular (scite lesson).

**P4 — Gap honesty must survive rendering.** The skill requires an "open questions /
thin coverage" section; the UI must amplify, not just display. *Resolution:* gap
markers computed independently (uncited paragraphs, VENDOR-only rankings,
single-source claims) and cross-linked with the report's own gaps section.

**P5 — Tool mode needs structure the synthesis has but markdown hides.**
configuration-and-controls synthesis is "every knob as a scannable list."
*Resolution:* parse synthesis md structure (headings/lists) into a filterable index;
no new pipeline output needed.

## 3. UX flow

**Entry.** Topic Shelf → `/w/<slug>/dossier`. Default: **Read mode**, report
rendered, margin notes on.

**Read loop (the detail ladder, S5):**
1. Read prose. Citation chips inline; the *current viewport's* citations project
   always-visible **margin sidenotes** (strongest supporting takeaway + valence
   badge) into the right margin — 0-interaction verification for the common case.
2. Hover a chip → evidence card: source title/domain/category/relevance, the
   supporting takeaway or claims_of_use quote, valence badge, grade chip. Target:
   80% of doubts die here.
3. Click → tri-panel engages: center report holds position; right-center panel
   shows the full DistilledRecord; far-right panel opens the content file
   scrolled/highlighted (exact with spans, ≈ with fuzzy). `Esc` collapses back.
4. Chips are numbered consistently with the left source rail (Perplexity pattern);
   clicking a rail source highlights every chip citing it (highlight-if-visible).

**Audit loop (`a` toggles Audit mode):** the claim table — rows = extracted claims
(report sentences containing citations or ranking language), columns = valence
roll-up (`USE:3 VENDOR:1`), grade, source count, sources; sort by "weakest first."
Cell click flips through supporting quotes in context (Elicit). Un-cited claims and
VENDOR-only rankings float to the top with warning tint. A coverage header states:
N claims · M fully grounded · K thin · J uncited.

**Reference loop (tool workspaces, `Atlas` tab within dossier):** the capability
index — parsed from synthesis files — as a three-column browsable index: controls
(flags/env/config, filterable by name), extension points, ecosystem/usage notes;
every entry keeps its doc pointer (source id → docs URL) and a "open in graph"
link to drc atlas's corresponding entity search.

**Cross-links.** Entity mentions in the report link to atlas searches; source cards
link to the mission grid's row (post-run, for seeing that source's pipeline history).
The three surfaces form one app.

## 4. UI design

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ dossier: agent-memory-layers      [Read] [Audit a] [Atlas*]        claims: 41 ✓31 ~7 ⚠3          │
├────────────┬──────────────────────────────────────┬───────────────┬───────────────────────────────┤
│ SOURCES    │  REPORT (center, position sacred)    │ MARGIN NOTES  │ EVIDENCE PANELS (on click)    │
│ 34 sources │                                      │               │                               │
│ by rel ▾   │  ## Ranked: memory layers            │ s12 ●USE      │ ┌ DistilledRecord s12 ──────┐ │
│ ● s12 blog │  1. **Zep** — strongest production   │ "replaced     │ │ takeaways (5)             │ │
│ ○ s19 docs │  track record for multi-session      │  bespoke      │ │ claims_of_use (2)         │ │
│ ○ s07 hn   │  recall [s12][s19]                   │  store w/     │ │ entities · relevance hi   │ │
│ …          │       ▲chips: s12 solid-green USE,   │  Zep in prod" │ └───────────────────────────┘ │
│ filters:   │        s19 hollow VENDOR             │               │ ┌ content/s12.md ───────────┐ │
│ USE-only   │                                      │ s19 ○VENDOR   │ │ …auto-scrolled, passage   │ │
│ cat ▾ rel ▾│  2. **Letta** — … ⚠no-source marker  │ docs page     │ │ highlighted (≈ if fuzzy)  │ │
│            │  on this sentence                    │               │ └───────────────────────────┘ │
├────────────┴──────────────────────────────────────┴───────────────┴───────────────────────────────┤
│ AUDIT TABLE (a): claim ▾weakest │ valence      │ grade │ n │ sources                              │
│ "strongest production record"   │ USE:1 VEND:1 │ B3    │ 2 │ s12 s19   [flip quotes ▸]           │
│ "sub-100ms retrieval at scale"  │ VEND:1       │ C5 ⚠  │ 1 │ s19       [flip quotes ▸]           │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
* Atlas tab appears for tool-graph workspaces (capability index parsed from synthesis/)
```

- **Chips:** solid green = USE-backed; hollow = VENDOR; gray = SECONDHAND; dashed
  amber = uncited-claim marker on the sentence itself. Numbered to match the rail.
- **Grade chip:** lightweight Admiralty two-axis — reliability letter from category
  (docs=A, research=B, practitioner web=C, vendor=D…) × corroboration number
  (independent supporting sources). Legend one hover away; axes shown separately in
  the tooltip (R5's conflation warning).
- **Margin notes:** gwern rules — visible by default, JS overlap reflow, never
  click-to-expand. Density cap: one note per paragraph (strongest evidence),
  overflow collapses into the paragraph's chip count.
- **Typography:** report column ~70ch for readability; the wide canvas is spent on
  the rails and panels, not on line length. Fira Code for ids/data; a serif for
  report prose (reading surface, not console).
- **Capability index (tool mode):** dense three-column list, type-to-filter, each
  row: control name · one-liner · doc pointer chip · graph link.

## 5. Operationalization

**Stack.** Same `drc dash` chassis; dossier is server-rendered markdown (markdown-it
or Python-Markdown) with a custom renderer pass that (1) extracts source-id tokens →
chip spans, (2) builds the claim index, (3) computes valence/grades, (4) emits
margin-note data attributes. Client JS: sidenote reflow (~80 lines), panel
management, audit table sorting — Alpine.js scale, no build step.

**Data plumbing.**
- `ReportIndex` (new `dr_cognee/dash/report_index.py`, Pydantic): built on page load
  (or file change) from report.md + sources.jsonl + distilled/*.json + content/*.
  Members: claims (sentence, cited ids, valence rollup, grade), citation→evidence
  map (takeaway text + match span + confidence), gap list.
- Fuzzy matching: `difflib`/rapidfuzz of takeaway text against content; store best
  span + ratio; threshold below which the UI shows ≈ and opens the doc un-scrolled.
- Synthesis parser for tool mode: heading/list-structure walk of synthesis/*.md →
  capability entries; resilient to format drift (unparsed sections render as plain
  markdown with a note).
- Everything cached in-process, invalidated by the same watcher as mission.

**Pipeline recommendations (not requirements):**
1. Distill emits `quote` (verbatim snippet) per takeaway/claim → exact highlights.
2. Report skill instructed to keep the `[src_xxxx]` citation form (one sentence in
   the skill) → less tolerant-parsing risk.
3. Optional per-claim valence from the distill LLM later, replacing the derivation
   heuristics; keep the heuristic as fallback forever.

**Build phases.**
- **v0 (1-2 days):** chip extraction + hover cards + tri-panel with fuzzy highlight.
  Answers question 1.
- **v1 (+2 days):** margin sidenotes + valence badges + grades + gap markers +
  source rail interactions. Answers 1-4.
- **v1.5 (+2 days):** audit table + tool-mode capability index + atlas/mission
  cross-links.

**Risks.**
- *Fuzzy match misleads* (highlights wrong passage): always show match confidence;
  below threshold, no highlight rather than a wrong one.
- *Valence heuristic misclassifies*: badge tooltips show the derivation inputs;
  misclassification is inspectable and cheap to mentally correct — and the audit
  table sorts by weakness, so errors surface where scrutiny already is.
- *Report format drift breaks claim extraction*: extraction is best-effort per
  sentence; a "parse coverage" stat in the audit header (e.g. "38/41 sentences
  indexed") keeps degradation honest.

**Effort estimate.** v0 ≈ 1.5 days; v1 ≈ +2 days; v1.5 ≈ +2 days. New code isolated
in `dr_cognee/dash/dossier*`; zero pipeline changes required, two one-line skill
edits recommended.

## 6. Revisions (post-critique — supersedes §1-5 where they conflict)

Full decisions in `../05-critique-response.md`. Design-changing items:

- **Tool-mode citation reality.** Measured on real reports: the deep-research report
  has 263 id citations, but tool-graph reports have ~5 and cite
  `[synthesis/<facet>.md]` instead. So: synthesis-pointer citations are parsed as
  first-class (chip → Controls index section), and the tool-graph skill is amended
  NOW with the id-citation contract. The 1-hour citation-coverage script runs
  against existing reports before any build.
- **Docs-source card defined** (docs sources have no DistilledRecord): title, URL,
  found_via, first-heading excerpt from the content file; docs are excluded from
  valence (a "docs" chip, never SECONDHAND-by-default).
- **Valence ladder replaces the heuristic.** (1) Parse the report's own
  `[vendor]`/`[practitioner]` labels (the agent already writes them); (2) computable
  proxies only; (3) unlabeled → no badge. Subject-entity inference dropped.
- **Admiralty grades cut.** Valence badge + source count carry the trust signal;
  audit table sorts weakest-first.
- **Gap markers tamed:** v1 flags only ranking-section sentences with zero
  citations.
- **Highlight tiers gated by spikes:** rapidfuzz hit-rate test on an existing
  workspace runs before v0; the distill `quote`-span change is a prerequisite for
  the exact-highlight tier (fuzzy stays as the labeled fallback tier).
- **Read-mode idle state:** evidence panel shows the viewport's strongest evidence.
- **"Atlas" tab renamed "Controls"** and promoted from v1.5 to v1 for tool
  workspaces — it's the retention claim of this whole surface.
- **Honest budget:** v0 ≈ 1.5 days (deep-research mode); tool mode is a second
  evidence model: **+4 days**, not +2.
