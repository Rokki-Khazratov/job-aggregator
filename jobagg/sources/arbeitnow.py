from __future__ import annotations

from typing import Any, Iterator

import httpx

from jobagg.hashing import build_dedup_key, clean_text, description_hash
from jobagg.sources.base import BaseJobSource

_REMOTE_MAP = {True: "remote", False: "onsite"}


class ArbeitnowSource(BaseJobSource):
    name = "arbeitnow"
    _start_url = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or self._make_client()

    def fetch(
        self,
        max_pages: int = 5,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        url: str | None = self._start_url
        page = 0
        while url and page < max_pages:
            data = self._get_json(self._client, url)
            jobs = data.get("data") or []
            for job in jobs:
                raw_desc = job.get("description") or ""
                desc = clean_text(raw_desc)
                title = job.get("title") or ""
                company = job.get("company_name")
                location_text = job.get("location")
                remote_raw = job.get("remote")
                remote_type = _REMOTE_MAP.get(remote_raw, "unspecified")
                external_id = job.get("slug") or job.get("url") or ""

                yield {
                    "source_name": self.name,
                    "source_type": "aggregator",
                    "external_id": external_id,
                    "source_url": job.get("url"),
                    "apply_url": job.get("url"),
                    "title": title,
                    "company": company,
                    "location_text": location_text,
                    "city": None,
                    "region": None,
                    "country": None,
                    "remote_type": remote_type,
                    "employment_type": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "salary_is_predicted": None,
                    "date_posted": job.get("created_at"),
                    "date_updated_source": None,
                    "description_text": desc,
                    "description_hash": description_hash(desc),
                    "dedup_key": build_dedup_key(title, company, location_text, desc),
                    "language": "en",
                    "raw_json": job,
                }

            links = data.get("links") or {}
            url = links.get("next")
            page += 1
