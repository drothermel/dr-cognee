from pathlib import Path

import pytest
from pydantic import ValidationError

from dr_cognee.models import SourceCategory, SourceRecord, TopicConfig
from dr_cognee.workspace import Workspace


@pytest.fixture
def config() -> TopicConfig:
    return TopicConfig(
        topic="Agent Knowledge Graphs",
        slug="agent-kg",
        question="Which tool should I use?",
        facets=["packaged", "components"],
        dataset_name="agent-kg",
        created="2026-07-07",
    )


def test_workspace_init_creates_layout(tmp_path: Path, config: TopicConfig) -> None:
    ws = Workspace.init(tmp_path / "agent-kg", config)
    assert ws.topic_file.exists()
    assert ws.log_file.exists()
    assert ws.content_dir.is_dir()
    assert ws.distilled_dir.is_dir()
    assert ws.synthesis_dir.is_dir()


def test_workspace_init_is_idempotent(tmp_path: Path, config: TopicConfig) -> None:
    root = tmp_path / "agent-kg"
    ws = Workspace.init(root, config)
    ws.log_file.write_text("edited log")
    Workspace.init(root, config)
    assert ws.log_file.read_text() == "edited log"


def test_workspace_load_round_trips_config(tmp_path: Path, config: TopicConfig) -> None:
    root = tmp_path / "agent-kg"
    Workspace.init(root, config)
    loaded = Workspace.load(root)
    assert loaded.config == config


def test_workspace_load_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Workspace.load(tmp_path / "nope")


def test_source_record_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SourceRecord(
            id="abc",
            url="https://example.com",
            title="t",
            category=SourceCategory.WEB,
            found_via="q",
            bogus="nope",
        )
