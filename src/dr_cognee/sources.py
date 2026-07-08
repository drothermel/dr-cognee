"""Structured source records: sources.jsonl store with URL dedup."""

import hashlib
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dr_cognee.models import SourceRecord, SourceStatus

TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"ref", "ref_src", "fbclid", "gclid"}
SOURCE_ID_LENGTH = 12


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in TRACKING_PARAMS and not key.startswith(TRACKING_PARAM_PREFIXES)
    ]
    path = parts.path.rstrip("/") or ""
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query_pairs), "")
    )


def source_id(url: str) -> str:
    digest = hashlib.sha256(normalize_url(url).encode()).hexdigest()
    return digest[:SOURCE_ID_LENGTH]


class SourceStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, SourceRecord]:
        if not self.path.exists():
            return {}
        records = {}
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            record = SourceRecord.model_validate_json(line)
            records[record.id] = record
        return records

    def append_new(self, records: list[SourceRecord]) -> list[SourceRecord]:
        existing = self.load()
        new_records = []
        for record in records:
            if record.id in existing:
                continue
            existing[record.id] = record
            new_records.append(record)
        if new_records:
            with self.path.open("a") as f:
                for record in new_records:
                    f.write(record.model_dump_json() + "\n")
        return new_records

    def update(self, record: SourceRecord) -> None:
        records = self.load()
        if record.id not in records:
            raise KeyError(f"Unknown source id: {record.id}")
        records[record.id] = record
        lines = [r.model_dump_json() for r in records.values()]
        self.path.write_text("\n".join(lines) + "\n")

    def counts(self) -> dict[SourceStatus, int]:
        counts: dict[SourceStatus, int] = {status: 0 for status in SourceStatus}
        for record in self.load().values():
            counts[record.status] += 1
        return counts

    def pending(self, status: SourceStatus) -> list[SourceRecord]:
        return [r for r in self.load().values() if r.status == status]

    def open_depth_flags(self) -> list[SourceRecord]:
        return [
            r
            for r in self.load().values()
            if r.depth_flag and r.status == SourceStatus.DISTILLED
        ]
