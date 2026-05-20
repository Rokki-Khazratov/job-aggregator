from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from jobagg import config


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_DDL = """
CREATE TABLE IF NOT EXISTS sources (
    name        TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    base_url    TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS jobs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name          TEXT NOT NULL,
    source_type          TEXT NOT NULL,
    external_id          TEXT NOT NULL,
    source_url           TEXT,
    apply_url            TEXT,
    title                TEXT NOT NULL,
    company              TEXT,
    location_text        TEXT,
    city                 TEXT,
    region               TEXT,
    country              TEXT,
    remote_type          TEXT,
    employment_type      TEXT,
    salary_min           REAL,
    salary_max           REAL,
    salary_currency      TEXT,
    salary_is_predicted  INTEGER,
    date_posted          TEXT,
    date_updated_source  TEXT,
    description_text     TEXT,
    description_hash     TEXT,
    dedup_key            TEXT,
    language             TEXT,
    raw_json             TEXT NOT NULL,
    first_seen_at        TEXT NOT NULL,
    last_seen_at         TEXT NOT NULL,
    is_active            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name  TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL DEFAULT 'running',
    jobs_seen    INTEGER NOT NULL DEFAULT 0,
    inserted     INTEGER NOT NULL DEFAULT 0,
    updated      INTEGER NOT NULL DEFAULT 0,
    deactivated  INTEGER NOT NULL DEFAULT 0,
    error        TEXT
);
"""

_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_source_ext
    ON jobs(source_name, external_id);

CREATE INDEX IF NOT EXISTS ix_jobs_dedup_key
    ON jobs(dedup_key);

CREATE INDEX IF NOT EXISTS ix_jobs_country_city_active
    ON jobs(country, city, is_active);
"""

_UPSERT_SQL = """
INSERT INTO jobs (
    source_name, source_type, external_id, source_url, apply_url,
    title, company, location_text, city, region, country,
    remote_type, employment_type,
    salary_min, salary_max, salary_currency, salary_is_predicted,
    date_posted, date_updated_source,
    description_text, description_hash, dedup_key, language,
    raw_json, first_seen_at, last_seen_at, is_active
) VALUES (
    :source_name, :source_type, :external_id, :source_url, :apply_url,
    :title, :company, :location_text, :city, :region, :country,
    :remote_type, :employment_type,
    :salary_min, :salary_max, :salary_currency, :salary_is_predicted,
    :date_posted, :date_updated_source,
    :description_text, :description_hash, :dedup_key, :language,
    :raw_json, :now, :now, 1
)
ON CONFLICT(source_name, external_id) DO UPDATE SET
    source_type         = excluded.source_type,
    source_url          = excluded.source_url,
    apply_url           = excluded.apply_url,
    title               = excluded.title,
    company             = excluded.company,
    location_text       = excluded.location_text,
    city                = excluded.city,
    region              = excluded.region,
    country             = excluded.country,
    remote_type         = excluded.remote_type,
    employment_type     = excluded.employment_type,
    salary_min          = excluded.salary_min,
    salary_max          = excluded.salary_max,
    salary_currency     = excluded.salary_currency,
    salary_is_predicted = excluded.salary_is_predicted,
    date_posted         = excluded.date_posted,
    date_updated_source = excluded.date_updated_source,
    description_text    = excluded.description_text,
    description_hash    = excluded.description_hash,
    dedup_key           = excluded.dedup_key,
    language            = excluded.language,
    raw_json            = excluded.raw_json,
    last_seen_at        = excluded.last_seen_at,
    is_active           = 1
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_DDL)
    conn.executescript(_INDEXES)
    conn.commit()


def upsert_job(conn: sqlite3.Connection, job: dict[str, Any]) -> bool:
    """Returns True if a new row was inserted, False if existing row was updated."""
    payload = dict(job)
    payload["raw_json"] = json.dumps(payload.get("raw_json", {}), ensure_ascii=False)
    payload["now"] = _now()
    before = conn.execute("SELECT changes()").fetchone()[0]
    conn.execute(_UPSERT_SQL, payload)
    after = conn.execute("SELECT changes()").fetchone()[0]
    # SQLite changes() returns 1 for both insert and update via ON CONFLICT
    # We check last_insert_rowid to distinguish: insert gives a new id
    return after > before


def deactivate_missing(
    conn: sqlite3.Connection, source_name: str, seen_ids: set[str]
) -> int:
    """Mark jobs from source_name not in seen_ids as is_active=0. Returns count."""
    if not seen_ids:
        return 0
    placeholders = ",".join("?" * len(seen_ids))
    result = conn.execute(
        f"UPDATE jobs SET is_active=0, last_seen_at=? "
        f"WHERE source_name=? AND is_active=1 AND external_id NOT IN ({placeholders})",
        [_now(), source_name, *seen_ids],
    )
    return result.rowcount


def list_jobs(
    conn: sqlite3.Connection,
    country: str | None = None,
    limit: int = 20,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM jobs WHERE is_active=1"
    params: list[Any] = []
    if country:
        query += " AND UPPER(country)=UPPER(?)"
        params.append(country)
    query += " ORDER BY date_posted DESC, last_seen_at DESC LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()


def get_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def start_sync_run(conn: sqlite3.Connection, source_name: str) -> int:
    cur = conn.execute(
        "INSERT INTO sync_runs (source_name, started_at, status) VALUES (?, ?, 'running')",
        (source_name, _now()),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def finish_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    jobs_seen: int = 0,
    inserted: int = 0,
    updated: int = 0,
    deactivated: int = 0,
    error: str | None = None,
) -> None:
    conn.execute(
        """UPDATE sync_runs SET
            finished_at=?, status=?, jobs_seen=?, inserted=?,
            updated=?, deactivated=?, error=?
           WHERE id=?""",
        (_now(), status, jobs_seen, inserted, updated, deactivated, error, run_id),
    )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
