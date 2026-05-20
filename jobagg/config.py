from __future__ import annotations

import os

DB_PATH: str = os.environ.get("JOBAGG_DB_PATH", "jobagg.db")

USER_AGENT: str = os.environ.get(
    "JOBAGG_USER_AGENT",
    "jobagg/0.1 (+contact: you@example.com)",
)

ADZUNA_APP_ID: str | None = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY: str | None = os.environ.get("ADZUNA_APP_KEY")

REQUEST_TIMEOUT = 20.0
CONNECT_TIMEOUT = 5.0
