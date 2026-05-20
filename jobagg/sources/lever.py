from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import httpx

from jobagg.hashing import build_dedup_key, clean_text, description_hash
from jobagg.sources.base import BaseJobSource


_REMOTE_MAP = {
    "remote": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "in office": "onsite",
    "work from home": "remote",
}


class LeverSource(BaseJobSource):
    name = "lever"
    _base = "https://api.lever.co/v0/postings"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or self._make_client()

    def _fetch_site(self, site: str, limit: int = 50) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        skip = 0
        while True:
            batch = self._get_json(
                self._client,
                f"{self._base}/{site}",
                params={"mode": "json", "skip": skip, "limit": limit},
            )
            if not batch:
                break
            all_jobs.extend(batch)
            skip += limit
        return all_jobs

    def fetch(
        self,
        seed_file: str | Path,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        sites = _read_seed(seed_file)
        for site in sites:
            try:
                jobs = self._fetch_site(site)
            except Exception:
                continue
            for job in jobs:
                title = job.get("text") or ""
                desc = clean_text(job.get("descriptionPlain") or job.get("description") or "")

                cats = job.get("categories") or {}
                location_text = cats.get("location")
                city = cats.get("location")

                workplace = (job.get("workplaceType") or "").lower()
                remote_type = _REMOTE_MAP.get(workplace, "unspecified")

                salary = job.get("salaryRange") or {}
                salary_min = salary.get("min")
                salary_max = salary.get("max")
                salary_currency = salary.get("currency")

                yield {
                    "source_name": self.name,
                    "source_type": "ats",
                    "external_id": job.get("id") or "",
                    "source_url": job.get("hostedUrl"),
                    "apply_url": job.get("applyUrl"),
                    "title": title,
                    "company": site,
                    "location_text": location_text,
                    "city": city,
                    "region": None,
                    "country": None,
                    "remote_type": remote_type,
                    "employment_type": cats.get("commitment"),
                    "salary_min": float(salary_min) if salary_min is not None else None,
                    "salary_max": float(salary_max) if salary_max is not None else None,
                    "salary_currency": salary_currency,
                    "salary_is_predicted": 0 if salary else None,
                    "date_posted": _ms_to_iso(job.get("createdAt")),
                    "date_updated_source": None,
                    "description_text": desc,
                    "description_hash": description_hash(desc),
                    "dedup_key": build_dedup_key(title, site, city, desc),
                    "language": "en",
                    "raw_json": job,
                }


def _ms_to_iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(timespec="seconds")


def _read_seed(path: str | Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
