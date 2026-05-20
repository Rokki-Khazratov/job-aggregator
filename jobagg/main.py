from __future__ import annotations

import argparse
import json
import sys
import traceback

from jobagg import config, db
from jobagg.sources.arbeitnow import ArbeitnowSource
from jobagg.sources.bundesagentur import BundesagenturSource
from jobagg.sources.greenhouse import GreenhouseSource
from jobagg.sources.lever import LeverSource

_BATCH_SIZE = 50


def cmd_init_db(args: argparse.Namespace) -> None:
    conn = db.get_connection(args.db)
    db.init_db(conn)
    print(f"Database initialized: {args.db or config.DB_PATH}")


def cmd_sync(args: argparse.Namespace) -> None:
    conn = db.get_connection(args.db)
    db.init_db(conn)

    source_name = args.source
    run_id = db.start_sync_run(conn, source_name)

    jobs_seen = inserted = updated = deactivated = 0
    batch: list[dict] = []

    def _flush(batch: list[dict]) -> tuple[int, int]:
        _ins = _upd = 0
        for job in batch:
            before = conn.execute("SELECT changes()").fetchone()[0]
            db.upsert_job(conn, job)
            # changes() returns 1 for both INSERT and UPDATE via ON CONFLICT;
            # distinguish by checking whether first_seen_at == last_seen_at
            # (only true on a brand-new row where both were set to the same :now)
            row = conn.execute(
                "SELECT first_seen_at, last_seen_at FROM jobs "
                "WHERE source_name=? AND external_id=?",
                (job["source_name"], job["external_id"]),
            ).fetchone()
            if row and row["first_seen_at"] == row["last_seen_at"]:
                _ins += 1
            else:
                _upd += 1
        conn.commit()
        return _ins, _upd

    try:
        source, fetch_kwargs = _build_source(args)
        seen_ids: set[str] = set()

        for job in source.fetch(**fetch_kwargs):
            jobs_seen += 1
            seen_ids.add(job.get("external_id", ""))
            batch.append(job)

            if len(batch) >= _BATCH_SIZE:
                ins, upd = _flush(batch)
                inserted += ins
                updated += upd
                batch.clear()

        if batch:
            ins, upd = _flush(batch)
            inserted += ins
            updated += upd

        if source_name in ("greenhouse", "lever") and seen_ids:
            deactivated = db.deactivate_missing(conn, source_name, seen_ids)
            conn.commit()

        db.finish_sync_run(
            conn, run_id,
            status="ok",
            jobs_seen=jobs_seen,
            inserted=inserted,
            updated=updated,
            deactivated=deactivated,
        )
        print(
            f"[{source_name}] done — seen={jobs_seen} inserted={inserted} "
            f"updated={updated} deactivated={deactivated}"
        )

    except Exception as exc:
        if batch:
            try:
                conn.commit()
            except Exception:
                pass
        db.finish_sync_run(
            conn, run_id,
            status="error",
            jobs_seen=jobs_seen,
            inserted=inserted,
            updated=updated,
            error=traceback.format_exc(),
        )
        print(f"[{source_name}] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_cleanup(args: argparse.Namespace) -> None:
    conn = db.get_connection(args.db)
    n = db.mark_stale(conn, stale_days=args.stale_days)
    conn.commit()
    print(f"Marked {n} jobs as inactive (last_seen_at older than {args.stale_days} days)")


def _build_source(args: argparse.Namespace) -> tuple[object, dict]:
    src = args.source
    if src == "bundesagentur":
        return BundesagenturSource(), {
            "query": args.query,
            "location": args.location,
            "pages": args.pages,
            "days": args.days,
        }
    if src == "greenhouse":
        return GreenhouseSource(), {"seed_file": args.seed_file}
    if src == "lever":
        return LeverSource(), {"seed_file": args.seed_file}
    if src == "arbeitnow":
        return ArbeitnowSource(), {"max_pages": args.pages}
    raise ValueError(f"Unknown source: {src}")


def cmd_list_jobs(args: argparse.Namespace) -> None:
    conn = db.get_connection(args.db)
    rows = db.list_jobs(conn, country=args.country, limit=args.limit)
    if not rows:
        if args.format == "json":
            print("[]")
        else:
            print("No jobs found.")
        return

    if args.format == "json":
        result = []
        for row in rows:
            d = dict(row)
            d.pop("raw_json", None)
            result.append(d)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(
                f"[{row['id']}] {row['title']} @ {row['company'] or '—'} "
                f"| {row['city'] or row['location_text'] or '—'} "
                f"| {row['source_name']} | {row['date_posted'] or '—'}"
            )


def cmd_show_job(args: argparse.Namespace) -> None:
    conn = db.get_connection(args.db)
    row = db.get_job(conn, args.id)
    if not row:
        print(f"Job id={args.id} not found.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(dict(row), ensure_ascii=False, indent=2))
    else:
        for k in row.keys():
            val = row[k]
            if k in ("description_text", "raw_json") and val and len(str(val)) > 300:
                val = str(val)[:300] + "…"
            print(f"{k}: {val}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m jobagg",
        description="DACH job aggregator CLI",
    )
    parser.add_argument("--db", default=None, metavar="PATH", help="SQLite DB path (overrides JOBAGG_DB_PATH)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Initialize the SQLite database schema")

    sync_p = sub.add_parser("sync", help="Sync jobs from a source")
    sync_p.add_argument("source", choices=["bundesagentur", "greenhouse", "lever", "arbeitnow"])
    sync_p.add_argument("--query", default="developer", help="[BA] search query")
    sync_p.add_argument("--location", default=None, help="[BA] location")
    sync_p.add_argument("--pages", type=int, default=1, help="[BA/Arbeitnow] max pages")
    sync_p.add_argument("--days", type=int, default=7, help="[BA] posted within N days")
    sync_p.add_argument("--seed-file", default=None, help="[Greenhouse/Lever] path to seed file")

    list_p = sub.add_parser("list-jobs", help="List jobs from the database")
    list_p.add_argument("--country", default=None, help="Filter by country code (e.g. DE)")
    list_p.add_argument("--limit", type=int, default=20, help="Max rows to show")
    list_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    show_p = sub.add_parser("show-job", help="Show a single job by id")
    show_p.add_argument("--id", type=int, required=True, help="Job id")
    show_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    cleanup_p = sub.add_parser("cleanup", help="Mark stale jobs inactive")
    cleanup_p.add_argument("--stale-days", type=int, default=30, help="Mark inactive if not seen in N days")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init-db":
        cmd_init_db(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "list-jobs":
        cmd_list_jobs(args)
    elif args.command == "show-job":
        cmd_show_job(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)


if __name__ == "__main__":
    main()
