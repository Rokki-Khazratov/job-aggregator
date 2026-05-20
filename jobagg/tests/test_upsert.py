import sqlite3
import pytest

from jobagg import db


def _make_job(external_id: str = "ext-1", title: str = "Engineer") -> dict:
    return {
        "source_name": "test_source",
        "source_type": "api",
        "external_id": external_id,
        "source_url": "https://example.com/job/1",
        "apply_url": None,
        "title": title,
        "company": "Acme",
        "location_text": "Berlin, DE",
        "city": "Berlin",
        "region": None,
        "country": "DE",
        "remote_type": "onsite",
        "employment_type": "full-time",
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_is_predicted": None,
        "date_posted": "2024-01-01",
        "date_updated_source": None,
        "description_text": "We need a great engineer.",
        "description_hash": "abc123",
        "dedup_key": "engineer|acme|berlin|deadbeef",
        "language": "en",
        "raw_json": {"id": external_id},
    }


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    db.init_db(c)
    yield c
    c.close()


def test_upsert_inserts_new_job(conn):
    db.upsert_job(conn, _make_job())
    conn.commit()
    rows = conn.execute("SELECT * FROM jobs").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "Engineer"


def test_upsert_idempotent(conn):
    job = _make_job()
    db.upsert_job(conn, job)
    conn.commit()
    db.upsert_job(conn, job)
    conn.commit()
    rows = conn.execute("SELECT * FROM jobs").fetchall()
    assert len(rows) == 1


def test_upsert_updates_title(conn):
    db.upsert_job(conn, _make_job(title="Old Title"))
    conn.commit()
    db.upsert_job(conn, _make_job(title="New Title"))
    conn.commit()
    row = conn.execute("SELECT title FROM jobs WHERE external_id='ext-1'").fetchone()
    assert row["title"] == "New Title"


def test_upsert_different_external_ids(conn):
    db.upsert_job(conn, _make_job(external_id="ext-1"))
    db.upsert_job(conn, _make_job(external_id="ext-2"))
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 2


def test_deactivate_missing(conn):
    db.upsert_job(conn, _make_job(external_id="ext-1"))
    db.upsert_job(conn, _make_job(external_id="ext-2"))
    conn.commit()
    n = db.deactivate_missing(conn, "test_source", {"ext-1"})
    conn.commit()
    assert n == 1
    row = conn.execute("SELECT is_active FROM jobs WHERE external_id='ext-2'").fetchone()
    assert row["is_active"] == 0


def test_list_jobs_filter_country(conn):
    j1 = _make_job(external_id="j1")
    j1["country"] = "DE"
    j2 = _make_job(external_id="j2")
    j2["country"] = "AT"
    db.upsert_job(conn, j1)
    db.upsert_job(conn, j2)
    conn.commit()
    rows = db.list_jobs(conn, country="DE")
    assert len(rows) == 1
    assert rows[0]["external_id"] == "j1"


def test_sync_run_logging(conn):
    run_id = db.start_sync_run(conn, "test_source")
    db.finish_sync_run(conn, run_id, status="ok", jobs_seen=5, inserted=3, updated=2)
    row = conn.execute("SELECT * FROM sync_runs WHERE id=?", (run_id,)).fetchone()
    assert row["status"] == "ok"
    assert row["jobs_seen"] == 5
    assert row["inserted"] == 3
    assert row["updated"] == 2
    assert row["error"] is None


def test_sync_run_error_logged(conn):
    run_id = db.start_sync_run(conn, "test_source")
    db.finish_sync_run(conn, run_id, status="error", error="Something went wrong")
    row = conn.execute("SELECT * FROM sync_runs WHERE id=?", (run_id,)).fetchone()
    assert row["status"] == "error"
    assert "Something" in row["error"]
