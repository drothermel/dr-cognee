"""HTTP client for the hosted Cognee tenant."""

import os
import time
from typing import Any

import httpx

API_KEY_HEADER = "X-Api-Key"
DATASETS_PATH = "/api/v1/datasets/"
DATASETS_STATUS_PATH = "/api/v1/datasets/status"
ADD_TEXT_PATH = "/api/v1/add_text"
COGNIFY_PATH = "/api/v1/cognify"
SEARCH_PATH = "/api/v1/search"

IN_PROGRESS_STATUSES = {"DATASET_PROCESSING_STARTED", "DATASET_PROCESSING_INITIATED"}
DEFAULT_SEARCH_TYPE = "GRAPH_COMPLETION"
REQUEST_TIMEOUT_S = 120.0


class CogneeTimeoutError(TimeoutError):
    pass


class CogneeCreditsError(RuntimeError):
    """The hosted tenant has insufficient credits for the requested operation."""


class CogneeClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        base_url = base_url or os.environ["COGNEE_BASE_URL"]
        api_key = api_key or os.environ["COGNEE_API_KEY"]
        self._http = httpx.Client(
            base_url=base_url,
            headers={API_KEY_HEADER: api_key},
            timeout=REQUEST_TIMEOUT_S,
        )

    def ensure_dataset(self, name: str) -> str:
        response = self._http.post(DATASETS_PATH, json={"name": name})
        response.raise_for_status()
        return response.json()["id"]

    def add_text(
        self, dataset_id: str, texts: list[str], node_set: list[str] | None = None
    ) -> None:
        payload: dict[str, Any] = {"textData": texts, "datasetId": dataset_id}
        if node_set:
            payload["nodeSet"] = node_set
        response = self._http.post(ADD_TEXT_PATH, json=payload)
        response.raise_for_status()

    def cognify(self, dataset_id: str, background: bool = True) -> dict[str, Any]:
        response = self._http.post(
            COGNIFY_PATH,
            json={"datasetIds": [dataset_id], "runInBackground": background},
        )
        if response.status_code == httpx.codes.PAYMENT_REQUIRED:
            raise CogneeCreditsError(response.json().get("detail", response.text))
        response.raise_for_status()
        return response.json()

    def dataset_status(self, dataset_id: str) -> str:
        response = self._http.get(DATASETS_STATUS_PATH, params={"dataset": [dataset_id]})
        response.raise_for_status()
        data = response.json()
        entry = data.get(dataset_id)
        if entry is None:
            return "UNKNOWN"
        if isinstance(entry, dict) and "status" in entry:
            return entry["status"]
        if isinstance(entry, dict):
            # keyed by pipeline name -> run info
            statuses = [
                v.get("status", v) if isinstance(v, dict) else v for v in entry.values()
            ]
            return statuses[-1] if statuses else "UNKNOWN"
        return str(entry)

    def wait_for_cognify(
        self, dataset_id: str, timeout_s: float = 900.0, poll_s: float = 10.0
    ) -> str:
        deadline = time.monotonic() + timeout_s
        while True:
            status = self.dataset_status(dataset_id)
            if status not in IN_PROGRESS_STATUSES:
                return status
            if time.monotonic() > deadline:
                raise CogneeTimeoutError(
                    f"cognify still {status} after {timeout_s}s for dataset {dataset_id}"
                )
            time.sleep(poll_s)

    def search(
        self, dataset_id: str, query: str, search_type: str = DEFAULT_SEARCH_TYPE
    ) -> Any:
        response = self._http.post(
            SEARCH_PATH,
            json={"searchType": search_type, "datasetIds": [dataset_id], "query": query},
        )
        response.raise_for_status()
        return response.json()
