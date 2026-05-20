import json
import tempfile
from pathlib import Path

import httpx
import pytest

from jobagg.sources.greenhouse import GreenhouseSource


def _make_client(jobs_payload: list) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": jobs_payload})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _make_seed(tokens: list[str]) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write("\n".join(tokens))
    f.close()
    return Path(f.name)


def test_greenhouse_content_true_maps_description():
    client = _make_client([{
        "id": 42,
        "title": "Backend Engineer",
        "content": "<p>We build great things.</p>",
        "absolute_url": "https://boards.greenhouse.io/acme/jobs/42",
        "location": {"name": "Berlin"},
        "offices": [],
        "updated_at": "2024-03-01T00:00:00.000Z",
    }])
    seed = _make_seed(["acme"])
    source = GreenhouseSource(client=client)
    jobs = list(source.fetch(seed_file=seed))
    assert len(jobs) == 1
    assert jobs[0]["description_text"] == "We build great things."
    assert jobs[0]["title"] == "Backend Engineer"
    assert jobs[0]["source_name"] == "greenhouse"
    assert jobs[0]["external_id"] == "42"


def test_greenhouse_empty_board():
    client = _make_client([])
    seed = _make_seed(["emptyco"])
    source = GreenhouseSource(client=client)
    jobs = list(source.fetch(seed_file=seed))
    assert jobs == []


def test_greenhouse_multiple_tokens():
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        call_count[0] += 1
        return httpx.Response(200, json={"jobs": [{"id": call_count[0], "title": f"Job {call_count[0]}", "content": "desc", "absolute_url": "http://x", "offices": [], "updated_at": "2024-01-01"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    seed = _make_seed(["co1", "co2", "co3"])
    source = GreenhouseSource(client=client)
    jobs = list(source.fetch(seed_file=seed))
    assert len(jobs) == 3
    assert call_count[0] == 3
