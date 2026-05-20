import tempfile
from pathlib import Path

import httpx
import pytest

from jobagg.sources.lever import LeverSource


def _make_seed(sites: list[str]) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write("\n".join(sites))
    f.close()
    return Path(f.name)


def test_lever_pagination_stops():
    pages = [
        [{"id": "a1", "text": "Job 1", "descriptionPlain": "desc", "hostedUrl": "https://x", "applyUrl": "https://y", "categories": {}, "createdAt": 1700000000000}],
        [{"id": "a2", "text": "Job 2", "descriptionPlain": "desc", "hostedUrl": "https://x", "applyUrl": "https://y", "categories": {}, "createdAt": 1700000000000}],
        [],
    ]
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        resp = pages[min(call_count[0], len(pages) - 1)]
        call_count[0] += 1
        return httpx.Response(200, json=resp)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    seed = _make_seed(["acme"])
    source = LeverSource(client=client)
    jobs = list(source.fetch(seed_file=seed))
    assert len(jobs) == 2


def test_lever_maps_fields():
    payload = [{
        "id": "xyz-123",
        "text": "Senior Engineer",
        "descriptionPlain": "We want the best.",
        "hostedUrl": "https://jobs.lever.co/acme/xyz-123",
        "applyUrl": "https://jobs.lever.co/acme/xyz-123/apply",
        "categories": {"location": "Munich", "commitment": "Full-time"},
        "workplaceType": "remote",
        "salaryRange": {"min": 70000, "max": 100000, "currency": "EUR"},
        "createdAt": 1700000000000,
    }]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload if "skip=0" in str(request.url) else [])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    seed = _make_seed(["acme"])
    source = LeverSource(client=client)
    jobs = list(source.fetch(seed_file=seed))
    assert len(jobs) == 1
    j = jobs[0]
    assert j["title"] == "Senior Engineer"
    assert j["remote_type"] == "remote"
    assert j["salary_min"] == 70000.0
    assert j["salary_currency"] == "EUR"
    assert j["city"] == "Munich"
