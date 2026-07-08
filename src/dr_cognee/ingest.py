"""Build the Cognee payload from a workspace and push it idempotently."""

import hashlib
from typing import Protocol

from pydantic import BaseModel, ConfigDict, RootModel

from dr_cognee.cognee_client import CogneeCreditsError

from dr_cognee.models import (
    DistilledRecord,
    Relevance,
    SourceCategory,
    SourceRecord,
    SourceStatus,
)
from dr_cognee.sources import SourceStore
from dr_cognee.workspace import Workspace

NODE_SET_DISTILLED = "distilled"
NODE_SET_CONTENT = "content"
NODE_SET_DOCS = "docs"
NODE_SET_SYNTHESIS = "synthesis"
NODE_SET_LOG = "log"
NODE_SET_REPORT = "report"


class IngestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    text: str
    node_set: list[str]


class IngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pushed: int = 0
    skipped: int = 0
    cognify_status: str = ""


class IngestClient(Protocol):
    def add_text(
        self, dataset_id: str, texts: list[str], node_set: list[str] | None = None
    ) -> None: ...

    def cognify(self, dataset_id: str, background: bool = True) -> dict: ...

    def wait_for_cognify(
        self, dataset_id: str, timeout_s: float = 900.0, poll_s: float = 10.0
    ) -> str: ...

    def ensure_dataset(self, name: str) -> str: ...


def render_distilled(record: SourceRecord, distilled: DistilledRecord) -> str:
    lines = [
        f"Source: {record.title}",
        f"URL: {record.url}",
        f"Category: {record.category}",
        f"Relevance: {distilled.relevance}",
        "",
        "Takeaways:",
        *[f"- {t}" for t in distilled.takeaways],
    ]
    if distilled.entities:
        lines += ["", "Entities: " + ", ".join(distilled.entities)]
    if distilled.claims_of_use:
        lines += ["", "Evidence of active use:", *[f"- {c}" for c in distilled.claims_of_use]]
    if distilled.depth_note:
        lines += ["", f"More depth available: {distilled.depth_note}"]
    return "\n".join(lines)


def build_payloads(workspace: Workspace, store: SourceStore) -> list[IngestItem]:
    items = []
    records = store.load()
    for record in records.values():
        content_path = workspace.content_path(record.id)
        # docs pages are already-clean reference text: ingest them whole, no distillation
        if record.category == SourceCategory.DOCS and content_path.exists():
            items.append(
                IngestItem(
                    key=f"docs:{record.id}",
                    text=content_path.read_text(),
                    node_set=[NODE_SET_DOCS],
                )
            )
        distilled_path = workspace.distilled_path(record.id)
        if not distilled_path.exists():
            continue
        distilled = DistilledRecord.model_validate_json(distilled_path.read_text())
        items.append(
            IngestItem(
                key=f"distilled:{record.id}",
                text=render_distilled(record, distilled),
                node_set=[NODE_SET_DISTILLED],
            )
        )
        if (
            record.depth_flag
            and record.relevance == Relevance.HIGH
            and record.category != SourceCategory.DOCS
            and content_path.exists()
        ):
            items.append(
                IngestItem(
                    key=f"content:{record.id}",
                    text=content_path.read_text(),
                    node_set=[NODE_SET_CONTENT],
                )
            )
    for synthesis_file in sorted(workspace.synthesis_dir.glob("*.md")):
        items.append(
            IngestItem(
                key=f"synthesis:{synthesis_file.stem}",
                text=synthesis_file.read_text(),
                node_set=[NODE_SET_SYNTHESIS],
            )
        )
    if workspace.log_file.exists():
        items.append(
            IngestItem(key="log", text=workspace.log_file.read_text(), node_set=[NODE_SET_LOG])
        )
    if workspace.report_file.exists():
        items.append(
            IngestItem(
                key="report", text=workspace.report_file.read_text(), node_set=[NODE_SET_REPORT]
            )
        )
    return items


class IngestManifest(RootModel[dict[str, str]]):
    """Maps ingested artifact key -> sha256 of the text last pushed."""


def _load_manifest(workspace: Workspace) -> dict[str, str]:
    if workspace.ingest_manifest_file.exists():
        return IngestManifest.model_validate_json(
            workspace.ingest_manifest_file.read_text()
        ).root
    return {}


def ingest_workspace(
    workspace: Workspace,
    store: SourceStore,
    client: IngestClient,
    wait: bool = True,
) -> IngestResult:
    dataset_id = client.ensure_dataset(workspace.config.dataset_name)
    manifest = _load_manifest(workspace)
    result = IngestResult()
    for item in build_payloads(workspace, store):
        digest = hashlib.sha256(item.text.encode()).hexdigest()
        if manifest.get(item.key) == digest:
            result.skipped += 1
            continue
        client.add_text(dataset_id, [item.text], node_set=item.node_set)
        manifest[item.key] = digest
        result.pushed += 1
    manifest_json = IngestManifest(dict(sorted(manifest.items()))).model_dump_json(indent=1)
    workspace.ingest_manifest_file.write_text(manifest_json)
    if result.pushed:
        try:
            client.cognify(dataset_id, background=True)
        except CogneeCreditsError as e:
            # pushes stand (manifest already updated); statuses stay un-flipped so a
            # later `drc cognify` + re-ingest can finish the job
            result.cognify_status = f"blocked: {e}"
            return result
        if wait:
            result.cognify_status = client.wait_for_cognify(dataset_id)
        else:
            result.cognify_status = "started"
    else:
        result.cognify_status = "no changes"
    for record in store.pending(SourceStatus.DISTILLED):
        record.status = SourceStatus.INGESTED
        store.update(record)
    for record in store.pending(SourceStatus.SCRAPED):
        if record.category == SourceCategory.DOCS:
            record.status = SourceStatus.INGESTED
            store.update(record)
    return result
