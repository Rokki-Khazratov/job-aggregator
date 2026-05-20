from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import httpx

from jobagg.hashing import build_dedup_key, clean_text, description_hash, detect_language
from jobagg.sources.base import BaseJobSource


class GreenhouseSource(BaseJobSource):
    name = "greenhouse"
    _base = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or self._make_client()

    def _fetch_board(self, board_token: str) -> list[dict[str, Any]]:
        data = self._get_json(
            self._client,
            f"{self._base}/{board_token}/jobs",
            params={"content": "true"},
        )
        return data.get("jobs") or []

    def fetch(
        self,
        seed_file: str | Path,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        tokens = _read_seed(seed_file)
        for token in tokens:
            try:
                jobs = self._fetch_board(token)
            except Exception:
                continue
            for job in jobs:
                raw_desc = job.get("content") or ""
                desc = clean_text(raw_desc)
                title = job.get("title") or ""

                offices = job.get("offices") or []
                first_office = offices[0] if offices else {}
                location_text = job.get("location", {}).get("name") or first_office.get("name")

                yield {
                    "source_name": self.name,
                    "source_type": "ats",
                    "external_id": str(job["id"]),
                    "source_url": job.get("absolute_url"),
                    "apply_url": job.get("absolute_url"),
                    "title": title,
                    "company": token,
                    "location_text": location_text,
                    "city": None,
                    "region": None,
                    "country": None,
                    "remote_type": "unspecified",
                    "employment_type": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "salary_is_predicted": None,
                    "date_posted": job.get("updated_at"),
                    "date_updated_source": job.get("updated_at"),
                    "description_text": desc,
                    "description_hash": description_hash(desc),
                    "dedup_key": build_dedup_key(title, token, location_text, desc),
                    "language": detect_language(desc),
                    "raw_json": job,
                }


def _read_seed(path: str | Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
