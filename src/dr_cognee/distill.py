"""LLM distillation of scraped sources into structured takeaway records."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

import anthropic
import openai
from pydantic import BaseModel, ConfigDict

from dr_cognee.models import DistilledRecord, Relevance, SourceCategory, SourceStatus
from dr_cognee.sources import SourceStore
from dr_cognee.workspace import Workspace

ANTHROPIC_DISTILL_MODEL = "claude-opus-4-8"
OPENAI_DISTILL_MODEL = "gpt-5.4-nano"
DISTILL_MAX_TOKENS = 8000
MAX_CONTENT_CHARS = 60_000


class DistillProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


DEFAULT_PROVIDER = DistillProvider.OPENAI

DISTILL_SYSTEM_PROMPT = """You are distilling one research source for a knowledge base.

Extract from the source content:
- takeaways: the concrete claims and findings relevant to the research question, one per item
- entities: named tools, projects, companies, papers, and concepts mentioned
- claims_of_use: concrete evidence that a tool or approach is actively used in practice \
(who uses it, production stories, adoption signals) - empty list if none
- relevance: how relevant this source is to the research question (high/medium/low)
- depth_flag: true if the source points at substantially more useful detail than the \
content shown (e.g. full docs, a repo, a longer comparison), false otherwise
- depth_note: if depth_flag is true, what more is there and why it matters; else null

Be faithful to the source; do not invent claims."""


class DistillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    takeaways: list[str]
    entities: list[str]
    claims_of_use: list[str]
    relevance: Relevance
    depth_flag: bool
    depth_note: str | None = None


class DistillBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distilled: int = 0
    failed: list[str] = []


class DistillClient(Protocol):
    def distill(self, prompt: str) -> DistillOutput: ...


class AnthropicDistillClient:
    def __init__(self, model: str = ANTHROPIC_DISTILL_MODEL) -> None:
        self._client = anthropic.Anthropic()
        self.model = model

    def distill(self, prompt: str) -> DistillOutput:
        response = self._client.messages.parse(
            model=self.model,
            max_tokens=DISTILL_MAX_TOKENS,
            system=DISTILL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=DistillOutput,
        )
        parsed = response.parsed_output
        if parsed is None:
            raise ValueError(f"no parsed output (stop_reason={response.stop_reason})")
        return parsed


class OpenAIDistillClient:
    def __init__(self, model: str = OPENAI_DISTILL_MODEL) -> None:
        self._client = openai.OpenAI()
        self.model = model

    def distill(self, prompt: str) -> DistillOutput:
        response = self._client.responses.parse(
            model=self.model,
            instructions=DISTILL_SYSTEM_PROMPT,
            input=prompt,
            text_format=DistillOutput,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError(f"no parsed output (status={response.status})")
        return parsed


def make_distill_client(
    provider: DistillProvider = DEFAULT_PROVIDER, model: str | None = None
) -> DistillClient:
    if provider == DistillProvider.OPENAI:
        return OpenAIDistillClient(model=model or OPENAI_DISTILL_MODEL)
    return AnthropicDistillClient(model=model or ANTHROPIC_DISTILL_MODEL)


def build_distill_prompt(question: str, title: str, url: str, content: str) -> str:
    return (
        f"Research question: {question}\n\n"
        f"Source: {title}\n{url}\n\n"
        f"Content:\n{content[:MAX_CONTENT_CHARS]}"
    )


def to_distilled_record(source_id: str, output: DistillOutput, distilled_at: str) -> DistilledRecord:
    return DistilledRecord(source_id=source_id, distilled_at=distilled_at, **output.model_dump())


def distill_pending(
    store: SourceStore,
    workspace: Workspace,
    client: DistillClient,
    limit: int | None = None,
) -> DistillBatchResult:
    result = DistillBatchResult()
    # docs pages are ingested whole (see ingest.build_payloads); never distill them
    pending = [
        r for r in store.pending(SourceStatus.SCRAPED) if r.category != SourceCategory.DOCS
    ]
    if limit is not None:
        pending = pending[:limit]
    for record in pending:
        content_path = workspace.content_path(record.id)
        if not content_path.exists():
            result.failed.append(f"{record.id}: missing content file")
            continue
        prompt = build_distill_prompt(
            workspace.config.question, record.title, record.url, content_path.read_text()
        )
        try:
            output = _distill_with_retry(client, prompt)
        except Exception as e:  # noqa: BLE001 - batch continues; source stays scraped
            record.error = f"distill failed: {e}"
            store.update(record)
            result.failed.append(f"{record.id}: {e}")
            continue
        distilled = to_distilled_record(record.id, output, datetime.now(UTC).isoformat())
        workspace.distilled_path(record.id).write_text(distilled.model_dump_json(indent=1))
        record.status = SourceStatus.DISTILLED
        record.relevance = output.relevance
        record.depth_flag = output.depth_flag
        record.depth_note = output.depth_note
        record.error = None
        store.update(record)
        result.distilled += 1
    return result


def _distill_with_retry(client: DistillClient, prompt: str) -> DistillOutput:
    try:
        return client.distill(prompt)
    except (anthropic.RateLimitError, openai.RateLimitError):
        return client.distill(prompt)
    except (anthropic.APIStatusError, openai.APIStatusError) as e:
        if e.status_code >= 500:
            return client.distill(prompt)
        raise
