from __future__ import annotations

import base64
from typing import Any, Iterator

import httpx

from jobagg.hashing import build_dedup_key, clean_text, description_hash
from jobagg.sources.base import BaseJobSource


class BundesagenturSource(BaseJobSource):
    name = "bundesagentur"
    _base = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or self._make_client(
            {"X-API-Key": "jobboerse-jobsuche"}
        )

    def _detail(self, refnr: str) -> dict[str, Any]:
        encoded = base64.b64encode(refnr.encode()).decode("ascii")
        return self._get_json(self._client, f"{self._base}/pc/v4/jobdetails/{encoded}")

    def fetch(
        self,
        query: str,
        location: str | None = None,
        days: int = 7,
        pages: int = 1,
        size: int = 50,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        for page in range(1, pages + 1):
            data = self._get_json(
                self._client,
                f"{self._base}/pc/v4/jobs",
                params={
                    "was": query,
                    "wo": location,
                    "page": page,
                    "size": size,
                    "angebotsart": 1,
                    "veroeffentlichtseit": days,
                },
            )
            stubs = data.get("stellenangebote") or []
            if not stubs:
                break
            for stub in stubs:
                refnr = stub.get("refnr")
                if not refnr:
                    continue
                try:
                    detail = self._detail(refnr)
                except Exception:
                    detail = {}

                title = (
                    detail.get("titel")
                    or detail.get("stellenangebotsTitel")
                    or stub.get("beruf")
                    or ""
                )
                company = detail.get("arbeitgeber") or stub.get("arbeitgeber")
                raw_desc = (
                    detail.get("stellenangebotsBeschreibung")
                    or detail.get("stellenbeschreibung")
                    or ""
                )
                desc = clean_text(raw_desc)

                places = detail.get("arbeitsorte") or []
                first_place: dict[str, Any] = places[0] if places else (stub.get("arbeitsort") or {})
                city = first_place.get("ort")
                region = first_place.get("region")
                country = first_place.get("land") or "DE"
                location_text = ", ".join(p for p in [city, region, country] if p)

                yield {
                    "source_name": self.name,
                    "source_type": "api",
                    "external_id": refnr,
                    "source_url": stub.get("externeUrl"),
                    "apply_url": stub.get("externeUrl"),
                    "title": title,
                    "company": company,
                    "location_text": location_text or None,
                    "city": city,
                    "region": region,
                    "country": country,
                    "remote_type": "unspecified",
                    "employment_type": ",".join(detail.get("arbeitszeitmodelle") or []),
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": "EUR" if detail.get("verguetung") else None,
                    "salary_is_predicted": None,
                    "date_posted": detail.get("aktuelleVeroeffentlichungsdatum"),
                    "date_updated_source": detail.get("modifikationsTimestamp"),
                    "description_text": desc,
                    "description_hash": description_hash(desc),
                    "dedup_key": build_dedup_key(title, company, city or region, desc),
                    "language": "de",
                    "raw_json": {"search": stub, "detail": detail},
                }
