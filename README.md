# jobagg — DACH Job Aggregator MVP

A minimal CLI tool for collecting job listings from multiple legally compliant sources, normalizing them into a unified schema, and storing them in SQLite.

## Sources

| Source | Type | Auth | Role |
|---|---|---|---|
| Bundesagentur für Arbeit | API | None (public key) | Primary DE source |
| Greenhouse Job Board API | ATS | None | Direct-employer feed |
| Lever Postings API | ATS | None | Direct-employer feed |
| Arbeitnow | Aggregator | None | EU/DACH feed |
| Adzuna | Aggregator | app_id + app_key | Licensed enrichment (optional) |

> **AMS** is not supported as an automated source — their terms prohibit automated aggregation.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env if needed

# 3. Initialize the database
python3 -m jobagg init-db

# 4. Sync jobs
python3 -m jobagg sync bundesagentur --query "Python" --location "Berlin" --pages 2

# 5. View results
python3 -m jobagg list-jobs --country DE --limit 10
python3 -m jobagg show-job --id 1
```

Full setup guide: [SETUP.md](SETUP.md)

## Project structure

```
jobagg/
  main.py          ← CLI (argparse)
  config.py        ← env vars
  db.py            ← SQLite: init, upsert, list, sync_runs
  hashing.py       ← clean_text, description_hash, dedup_key
  sources/
    base.py        ← BaseJobSource + retry helper
    bundesagentur.py
    greenhouse.py
    lever.py
    arbeitnow.py
  seeds/
    greenhouse.txt ← board tokens (fill in manually)
    lever.txt      ← site names (fill in manually)
  tests/           ← pytest + httpx.MockTransport
```

## CLI reference

```bash
python3 -m jobagg init-db
python3 -m jobagg sync bundesagentur --query STR [--location STR] [--pages N] [--days N]
python3 -m jobagg sync greenhouse --seed-file PATH
python3 -m jobagg sync lever --seed-file PATH
python3 -m jobagg sync arbeitnow [--pages N]
python3 -m jobagg list-jobs [--country CODE] [--limit N]
python3 -m jobagg show-job --id N
```

## Tests

```bash
python3 -m pytest jobagg/tests/ -v
```

## Legal

- **Bundesagentur:** Public API. Do not scrape contact details (CAPTCHA-protected).
- **Greenhouse / Lever:** Published job board APIs, read-only. Do not use POST apply endpoints.
- **Arbeitnow:** Free public API. Do not abuse request frequency.
- **Adzuna:** 14-day trial. Ongoing commercial aggregation requires a written agreement.
- **AMS:** Automated aggregation is prohibited by ToS. Manual links only.
