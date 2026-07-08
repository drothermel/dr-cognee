# Case Study: Anatomy of Evidence-First Readers

> Wave-2 agent CS3. Saved verbatim, 2026-07-07. Feeds the **drc dossier** design.

## Why these three

An evidence-first reader treats every generated sentence as a promise that must be redeemable on demand. The three exemplars here each solved a different slice of that problem, and together they cover the design space the drc report reader lives in:

- **NotebookLM** solved the *verification loop*: how a citation chip becomes a near-zero-cost round trip from claim to source passage and back.
- **Elicit** solved the *structured extraction surface*: how to show one claim per cell across many sources, with the supporting quote one click away — and how a report stays a "living document" whose pipeline steps are editable.
- **gwern.net** solved the *depth-control problem*: how a single reading surface offers a graded ladder of detail (title → margin note → sidenote → collapse → popup) so the reader chooses their own evidence depth without losing their place.

drc's data model — `report.md` citing source ids, each resolving to a `SourceRecord` (url/title/category/relevance), a `DistilledRecord` (takeaways, entities, `claims_of_use`), and full scraped content on disk — is essentially a pre-built version of what all three systems compute at runtime. The design question is purely presentational: which of these interaction grammars to borrow. A very wide monitor plus a single power user means we can be greedier than any of these products: keep all three panels open at once.

## Exemplar 1: NotebookLM citations

**Screen anatomy.** Three vertical panels: a *Sources* rail (left) listing uploaded documents with checkboxes; a *Chat* panel (center) holding the generated answer; a *Studio/notes* panel (right). Answers are studded with small numbered inline citation chips (superscript-style buttons), one per grounded span — citations moved inline from an older bottom-tray design, and can map to text or images. The source viewer opens *in place of* the source list, so answer and evidence coexist side by side rather than in a modal that hides the answer.

**Verifying one claim.** (1) Hover the numbered chip → a card shows the exact quoted passage plus source title: **1 hover, 0 clicks** for a plausibility check. (2) If the quote alone doesn't settle it, click the chip → the source viewer opens and auto-scrolls to the cited passage, highlighted, with surrounding context: **1 click** total for full in-context verification. The answer never leaves the screen, so "return to reading" costs zero clicks.

**What each element solves.** The hover card solves *verification latency*: most doubts die at the quote, so the common case costs no navigation at all. The click-to-highlighted-passage solves *quote-mining risk*: the reader sees the sentence in its native paragraph, catching out-of-context extractions. Side-by-side persistence solves *place-keeping*: you never lose your position in the answer. This is what makes verification approximately free — the cost curve is hover < click < read-around, and each step is optional.

**Weakness: citation noise.** Dense answers sprout a chip after nearly every sentence, sometimes several per sentence, and the chips carry no differentiating signal — chip 3 backed by a definitive primary passage looks identical to chip 14 backed by a loosely relevant chunk. The reader can't triage *which* citations deserve checking; retrieval granularity (chunks) also means the highlighted region is sometimes broader or slightly off from the actual claim. Uniform chips invite either checking everything or checking nothing.

## Exemplar 2: Elicit tables

**Screen anatomy.** The core artifact is a *papers × columns* matrix: each row a paper, each column a user-defined extraction question ("sample size", "intervention", "main finding" — effectively claims). Cells hold short extracted answers; each cell carries a quote affordance (a speech-bubble-style indicator) signaling that a supporting excerpt exists. Above the table sits the search/screening pipeline; in report mode, a prose synthesis appears with **sentence-level citations**, each claim linked to the exact quote in a source paper. Clicking a report claim or a table cell opens the supporting quote, with a path onward into the paper itself.

**Verifying one claim.** (1) Click the cell (or the report sentence's citation): a panel reveals the verbatim excerpt from the paper that produced the value — **1 click**. (2) If the excerpt is ambiguous, click through to the paper view scrolled to that passage — **2 clicks** total for full context. Accuracy checking is thus built into the reading motion: if an extracted value looks wrong, the falsifying evidence is one click away.

**What each element solves.** The matrix solves *cross-source comparability*: the same claim-question asked of every source makes disagreement visually obvious (scan a column, spot the outlier). Cell-level quotes solve *extraction trust*: the model's answer and its raw evidence are permanently paired, so the reader audits the extraction, not just the synthesis. The "living document" framing — reports whose pipeline steps (search, screening criteria, extraction columns) can be modified and the report regenerated, and living reviews that update as new papers appear — solves *staleness and rigidity*: the report is a view over a pipeline, not a frozen artifact. That framing maps directly onto drc, where the report is likewise a rendering of harvest → scrape → distill → synthesize stages that can be re-run.

**Weakness: the table flattens.** Cells force complex, hedged findings into short strings; nuance ("effect only in subgroup X, n=12") gets truncated into a confident-looking value, and the reader only discovers the hedge if they click. The uniform grid also gives every source equal visual weight regardless of quality or relevance — a weak preprint's cell looks exactly like a strong RCT's.

## Exemplar 3: gwern.net sidenotes & popups

**Screen anatomy.** A narrow central text column with deliberately wide margins reclaimed as an *evidence surface*: footnotes render as always-visible **sidenotes** alongside the sentence that spawned them, alternating left/right margins. Links come in grades: plain links, live-preview links, and dotted-underline *annotated links* that pop up a "mini-page" — title/author/date/tags/backlinks metadata block plus an abstract. Popups are **recursive**: links inside a popup pop up further popups, each draggable, resizable, pinnable, or fullscreen-able. Long tangents sit in collapsed disclosure regions inline.

**Verifying one claim.** A claim with a sidenote: **0 interactions** — a saccade to the margin reads the note; gwern calls this effortlessness "the greatest advantage," and notes that implementations requiring clicks "defeat much of the point." A claim resting on a citation link: **1 hover** pops the annotation (abstract, metadata, often a curated excerpt); **1 more hover/click inside the popup** reaches the full document or a deeper annotation. Depth is strictly pay-as-you-go.

**What each element solves.** Sidenotes solve *evidence adjacency*: supporting material is spatially co-located with the claim, so no navigation and no place-loss — the strongest possible answer to the footnote round trip. Annotation popups solve *link opacity*: a bare URL becomes a structured preview, letting the reader judge a source without leaving. Recursion solves *depth without commitment*. And the explicit detail ladder — link title/tooltip → margin note → sidenote paragraph → collapsed section → popup annotation → full page — is "semantic zoom": one document serving skimmers and deep-divers simultaneously, each choosing a rung.

**Weakness: layout fragility and density.** Sidenotes require real horizontal space and runtime layout to avoid overlapping when notes are long or clustered; on narrow screens the whole system degrades to pop-ins or endnotes. And for new readers, three grades of underline, collapses, and recursive popups impose a real learning curve — the apparatus can compete with the text. (For drc this weakness is mostly moot: one power user, one very wide monitor.)

## Mapping table: exemplar element → drc report reader

| Exemplar element | drc equivalent (real data model) |
|---|---|
| NotebookLM citation chip | Inline citation chip on a source id in `report.md`; hover → `SourceRecord` card (title, url, category, relevance score) |
| NotebookLM hover-quote | Hover card second layer: the matched `DistilledRecord` takeaway text — the quote-level check without opening anything |
| NotebookLM click → highlighted passage | Click chip → right panel opens the local scraped-content file, scrolled/highlighted to the passage the takeaway was distilled from |
| NotebookLM sources rail | Left panel: all `SourceRecord`s for the report, filterable by `category` and sortable by `relevance` |
| Elicit papers×claims matrix | "Evidence grid" view: sources × distilled dimensions; for ranked-options reports, options × criteria with cells backed by takeaways |
| Elicit cell-click → quote | Cell click → the `DistilledRecord` takeaway + jump-link into scraped content |
| Elicit sentence-level report citation | Claim spans in `report.md` bound to specific takeaway ids, not just source ids — citation resolves to a *claim*, not a whole document |
| Elicit living document / editable pipeline | Report header exposes pipeline provenance; "re-distill this source" / "re-run synthesis" actions since the report is a view over drc stages |
| gwern sidenote | Margin column (wide monitor!) auto-showing the cited takeaway beside each claim in the viewport — 0-interaction verification for the common case |
| gwern annotation popup mini-page | `SourceRecord` + `DistilledRecord` summary popup: title, url, category, relevance, top takeaways, entities |
| gwern recursive popups | From a source popup, pop entities → other sources sharing that entity; takeaways → their passages |
| gwern detail ladder | drc's ladder: chip → hover `SourceRecord` card → margin takeaway → popup `DistilledRecord` → full scraped content panel |
| gwern link grades (plain/annotated) | **Evidence-valence badge**: claims backed by `claims_of_use` (real-world usage evidence) get a distinct chip style vs. claims backed only by marketing/docs takeaways — the differentiated-chip signal NotebookLM lacks, computed from data drc already separates at distill time |

## Walkthrough: doubting a ranking claim

The report "Best agent memory layer" is open in the center panel; the left panel lists 34 `SourceRecord`s by relevance; the right panel is empty. The report ranks Zep above Letta, and one sentence stops the reader: *"Zep's temporal knowledge graph gives it the strongest production track record for multi-session recall [s12][s19]."* The chip for `s12` wears the solid green **claims_of_use** badge; `s19`'s chip is hollow — takeaway-only. That asymmetry is itself information: only one of the two citations rests on evidence of real-world use.

Because the claim is on-screen, its margin note is already visible gwern-style: the `s12` takeaway reads "Team reports replacing bespoke session-summary store with Zep in production; recall quality improved across multi-week sessions." Zero interactions spent; the doubt narrows — is this a customer report or vendor content? **Hover** the chip: the `SourceRecord` card shows an engineering blog URL, `category: practitioner-writeup`, relevance 0.91, plus the `DistilledRecord`'s `claims_of_use` entry verbatim. Still ambiguous — "improved recall quality" could be paraphrase-inflated. **Click**: the right panel opens the local scraped file, auto-scrolled to the highlighted passage. The surrounding paragraph confirms it's a third-party team's postmortem, with the caveat that they tested only two alternatives. One hover on hollow `s19` shows a Zep docs page — marketing-adjacent, correctly badged.

Verdict in **one hover and one click** (plus one free margin-note read): the ranking claim is real but overstated — "strongest track record" rests on one practitioner report. The reader pins the `s12` popup, pops its "multi-session recall" entity to see which other sources mention it (two, both hollow-badged), and annotates the report sentence: *soften to "the only third-party production validation found."* The report is a living view; the doubt is resolved, logged, and the reader's place in the center panel was never lost.

## Sources

- [NotebookLM inline citations — FSU Service Center](https://servicecenter.fsu.edu/s/article/How-do-NotebookLM-s-inline-citations-work-and-why-are-they-important)
- [NotebookLM tutorial (citations: hover for quote, click to auto-scroll source viewer)](https://sites.google.com/view/notebook-lm/tutorial)
- [Using NotebookLM — UBC Digital Scholarship in Arts](https://disa.arts.ubc.ca/toolkits/knowledge-management-tools-for-researchers/tips-for-researchers-using-notebooklm/)
- [Elicit AI Data Extraction Guide — IntuitionLabs](https://intuitionlabs.ai/articles/elicit-data-extraction-clinical-papers)
- [Elicit Reports](https://elicit.com/solutions/reports) and [Elicit Systematic Review announcement](https://elicit.com/blog/systematic-review)
- [Elicit evaluation — Deakin University LibGuides (living reviews)](https://deakin.libguides.com/AI-Evaluations/Elicit)
- [Gwern — Sidenotes in Web Design](https://gwern.net/sidenote)
- [Gwern — Design of This Website (popups, annotations, progressive disclosure)](https://gwern.net/design)
