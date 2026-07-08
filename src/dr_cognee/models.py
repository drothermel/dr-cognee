"""Domain models for the deep-research workspace."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SourceCategory(StrEnum):
    WEB = "web"
    NEWS = "news"
    GITHUB = "github"
    RESEARCH = "research"
    PDF = "pdf"


class SourceStatus(StrEnum):
    FOUND = "found"
    SCRAPED = "scraped"
    DISTILLED = "distilled"
    INGESTED = "ingested"
    SKIPPED = "skipped"


class Relevance(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TopicConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    slug: str
    question: str
    facets: list[str]
    dataset_name: str
    created: str


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    title: str
    category: SourceCategory
    found_via: str
    published: str | None = None
    status: SourceStatus = SourceStatus.FOUND
    relevance: Relevance | None = None
    depth_flag: bool = False
    depth_note: str | None = None
    error: str | None = None


class DistilledRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    takeaways: list[str]
    entities: list[str]
    claims_of_use: list[str]
    relevance: Relevance
    depth_flag: bool
    depth_note: str | None = None
    distilled_at: str


class QuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    sources: list[str] = ["web"]
    categories: list[SourceCategory] = []
    tbs: str | None = None
    limit: int = 10


class HarvestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[QuerySpec]
