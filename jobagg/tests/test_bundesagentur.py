import base64
import json

import httpx
import pytest

from jobagg.sources.bundesagentur import BundesagenturSource


def _make_transport(search_resp: dict, detail_resp: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "jobdetails" in path:
            return httpx.Response(200, json=detail_resp)
        return httpx.Response(200, json=search_resp)

    return httpx.MockTransport(handler)


def test_ba_search_then_detail_flow():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if "jobdetails" in path:
            return httpx.Response(200, json={
                "titel": "Python Developer",
                "arbeitgeber": "Acme GmbH",
                "stellenangebotsBeschreibung": "Great job.",
                "arbeitsorte": [{"ort": "Berlin", "region": "Berlin", "land": "DE"}],
                "arbeitszeitmodelle": ["VOLLZEIT"],
            })
        return httpx.Response(200, json={
            "stellenangebote": [
                {"refnr": "ABC-123", "beruf": "Developer", "arbeitgeber": "Acme"},
            ]
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = BundesagenturSource(client=client)
    jobs = list(source.fetch(query="Python", pages=1))

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Python Developer"
    assert jobs[0]["external_id"] == "ABC-123"
    assert jobs[0]["city"] == "Berlin"
    assert jobs[0]["source_name"] == "bundesagentur"
    assert "jobdetails" in calls[1]


def test_ba_empty_search_stops():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"stellenangebote": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = BundesagenturSource(client=client)
    jobs = list(source.fetch(query="Python", pages=3))
    assert jobs == []


def test_ba_detail_error_skips_description():
    def handler(request: httpx.Request) -> httpx.Response:
        if "jobdetails" in request.url.path:
            return httpx.Response(500)
        return httpx.Response(200, json={
            "stellenangebote": [{"refnr": "X-1", "beruf": "Dev", "arbeitgeber": "Co"}]
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = BundesagenturSource(client=client)
    jobs = list(source.fetch(query="dev", pages=1))
    assert len(jobs) == 1
    assert jobs[0]["description_text"] == ""
