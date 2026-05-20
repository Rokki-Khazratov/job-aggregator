import httpx
import pytest

from jobagg.sources.arbeitnow import ArbeitnowSource


def _job(slug: str) -> dict:
    return {
        "slug": slug,
        "title": f"Job {slug}",
        "company_name": "Acme",
        "description": "<p>Good job.</p>",
        "url": f"https://www.arbeitnow.com/jobs/{slug}",
        "location": "Berlin",
        "remote": False,
        "created_at": "2024-01-01",
    }


def test_arbeitnow_next_link_pagination():
    page1 = {
        "data": [_job("j1"), _job("j2")],
        "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
    }
    page2 = {
        "data": [_job("j3")],
        "links": {"next": None},
    }
    pages = [page1, page2]
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        resp = pages[min(call_count[0], len(pages) - 1)]
        call_count[0] += 1
        return httpx.Response(200, json=resp)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = ArbeitnowSource(client=client)
    jobs = list(source.fetch(max_pages=10))
    assert len(jobs) == 3
    assert jobs[0]["external_id"] == "j1"
    assert jobs[2]["external_id"] == "j3"


def test_arbeitnow_respects_max_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "data": [_job("j1")],
            "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = ArbeitnowSource(client=client)
    jobs = list(source.fetch(max_pages=2))
    assert len(jobs) == 2


def test_arbeitnow_maps_remote():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "data": [{**_job("r1"), "remote": True}],
            "links": {"next": None},
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = ArbeitnowSource(client=client)
    jobs = list(source.fetch(max_pages=1))
    assert jobs[0]["remote_type"] == "remote"


def test_arbeitnow_strips_html_from_description():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "data": [{**_job("h1"), "description": "<b>Bold</b> text &amp; more"}],
            "links": {"next": None},
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = ArbeitnowSource(client=client)
    jobs = list(source.fetch(max_pages=1))
    assert jobs[0]["description_text"] == "Bold text & more"
