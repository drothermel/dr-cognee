# Testing

## Unit tests (no network)

```bash
uv run pytest -q
```

Success: all tests pass. Fixtures live in `tests/fixtures/` (recorded Firecrawl responses);
no test hits a live API.

## Live smoke (Firecrawl + Anthropic + hosted Cognee)

Requires `FIRECRAWL_API_KEY`, `COGNEE_BASE_URL`, `COGNEE_API_KEY`, and `OPENAI_API_KEY`
(distill defaults to OpenAI `gpt-5.4-nano`; `drc distill --provider anthropic` switches to
the Anthropic SDK, which then needs `ANTHROPIC_API_KEY`-resolvable credentials).

```bash
uv run python scripts/smoke_live.py
```

Runs the full pipeline against a throwaway `research/smoke-test/` workspace: one harvest
query (limit 3), one scrape, one distill, ingest + cognify (blocks until done, can take a
few minutes), one `CHUNKS` search.

Success criteria:
- each step prints a `[n/6]` line with non-error evidence (new/seen counts, scraped status,
  distilled=1, pushed>0 on first run, a cognify status, search hits>=1)
- final line is `SMOKE OK`

Re-runs are cheap: the ingest manifest skips unchanged artifacts and harvest dedups seen URLs.
To reset, delete `research/smoke-test/`.
