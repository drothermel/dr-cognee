"""Per-topic workspace: directory layout and topic.yaml."""

from pathlib import Path

import yaml

from dr_cognee.models import TopicConfig

TOPIC_FILE = "topic.yaml"
LOG_FILE = "log.md"
SOURCES_FILE = "sources.jsonl"
CONTENT_DIR = "content"
DISTILLED_DIR = "distilled"
SYNTHESIS_DIR = "synthesis"
REPORT_FILE = "report.md"
INGEST_MANIFEST_FILE = "ingested.json"


class Workspace:
    def __init__(self, root: Path, config: TopicConfig) -> None:
        self.root = root
        self.config = config

    @property
    def topic_file(self) -> Path:
        return self.root / TOPIC_FILE

    @property
    def log_file(self) -> Path:
        return self.root / LOG_FILE

    @property
    def sources_file(self) -> Path:
        return self.root / SOURCES_FILE

    @property
    def content_dir(self) -> Path:
        return self.root / CONTENT_DIR

    @property
    def distilled_dir(self) -> Path:
        return self.root / DISTILLED_DIR

    @property
    def synthesis_dir(self) -> Path:
        return self.root / SYNTHESIS_DIR

    @property
    def report_file(self) -> Path:
        return self.root / REPORT_FILE

    @property
    def ingest_manifest_file(self) -> Path:
        return self.root / INGEST_MANIFEST_FILE

    def content_path(self, source_id: str) -> Path:
        return self.content_dir / f"{source_id}.md"

    def distilled_path(self, source_id: str) -> Path:
        return self.distilled_dir / f"{source_id}.json"

    @classmethod
    def init(cls, root: Path, config: TopicConfig) -> "Workspace":
        ws = cls(root, config)
        for directory in (root, ws.content_dir, ws.distilled_dir, ws.synthesis_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if not ws.topic_file.exists():
            ws.topic_file.write_text(yaml.safe_dump(config.model_dump(), sort_keys=False))
        if not ws.log_file.exists():
            ws.log_file.write_text(
                f"# Research log: {config.topic}\n\n"
                f"Question: {config.question}\n\n"
                f"Facets: {', '.join(config.facets)}\n"
            )
        return ws

    @classmethod
    def load(cls, root: Path) -> "Workspace":
        topic_file = root / TOPIC_FILE
        if not topic_file.exists():
            raise FileNotFoundError(f"No workspace at {root} (missing {TOPIC_FILE})")
        config = TopicConfig(**yaml.safe_load(topic_file.read_text()))
        return cls(root, config)
