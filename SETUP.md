# SETUP — Getting started with jobagg

## 1. Requirements

- Python 3.11+
- Internet connection (for API requests)

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure .env

```bash
cp .env.example .env
```

Open `.env` in a text editor and fill in the values:

| Variable | Description | Where to get it | Required |
|---|---|---|---|
| `JOBAGG_DB_PATH` | Path to the SQLite database file | Any path, e.g. `./jobagg.db` | No (default: `jobagg.db`) |
| `JOBAGG_USER_AGENT` | User-Agent header for HTTP requests | Put your email: `jobagg/0.1 (+contact: YOUR@EMAIL.COM)` | No |
| `ADZUNA_APP_ID` | App ID for Adzuna API | [developer.adzuna.com](https://developer.adzuna.com) → My Apps → App ID | Only for Adzuna |
| `ADZUNA_APP_KEY` | App Key for Adzuna API | Same page → App Key | Only for Adzuna |

> **Note:** No `.env` setup is required for Bundesagentur or Arbeitnow — they work without any credentials.

## 4. Fill in seed files for Greenhouse and Lever

Greenhouse and Lever **do not require API keys** for reading job listings. You only need to specify which companies to sync.

### Greenhouse — `jobagg/seeds/greenhouse.txt`

Add board tokens, one per line (no spaces, no `#`):

```
netflix
shopify
airbnb
```

**How to find the board token:**
Open a company's career page. If the URL is `boards.greenhouse.io/netflix`, the token is `netflix`.

### Lever — `jobagg/seeds/lever.txt`

Add site names, one per line:

```
netflix
stripe
revolut
```

**How to find the site name:**
Open a company's career page. If the URL is `jobs.lever.co/stripe`, the site name is `stripe`.

## 5. Initialize the database

```bash
python3 -m jobagg init-db
```

Creates the `sources`, `jobs`, and `sync_runs` tables in `jobagg.db` (or the path set in `JOBAGG_DB_PATH`).

## 6. Sync jobs

### Bundesagentur (Germany, no credentials needed)

```bash
python3 -m jobagg sync bundesagentur \
  --query "Python Developer" \
  --location "Berlin" \
  --pages 3 \
  --days 7
```

| Flag | Description | Default |
|---|---|---|
| `--query` | Search query | `developer` |
| `--location` | City or region | — |
| `--pages` | Max pages per run | `1` |
| `--days` | Only jobs posted within the last N days | `7` |

### Greenhouse (ATS, no credentials needed)

```bash
python3 -m jobagg sync greenhouse \
  --seed-file jobagg/seeds/greenhouse.txt
```

### Lever (ATS, no credentials needed)

```bash
python3 -m jobagg sync lever \
  --seed-file jobagg/seeds/lever.txt
```

### Arbeitnow (EU aggregator, no credentials needed)

```bash
python3 -m jobagg sync arbeitnow --pages 5
```

### Adzuna (requires credentials and confirmed usage rights)

> **WARNING:** Adzuna's ToS restrict ongoing commercial aggregation after the 14-day trial without a written agreement. Do not run without valid credentials, and do not use as a production source without a license.

The Adzuna adapter will be added later. To enable it you will need to:
1. Register at [developer.adzuna.com](https://developer.adzuna.com)
2. Set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env`
3. Review the [Terms of Service](https://developer.adzuna.com/terms)

## 7. Browse data

```bash
# Last 20 jobs across all sources
python3 -m jobagg list-jobs

# Germany only
python3 -m jobagg list-jobs --country DE --limit 50

# Full details for a single job
python3 -m jobagg show-job --id 1
```

## 8. Automate with cron

Example crontab for regular syncing:

```cron
# Bundesagentur — every hour
0 * * * * cd /path/to/ams-alternative && python3 -m jobagg sync bundesagentur --query "Python" --location "Berlin" --pages 3 >> logs/ba.log 2>&1

# Greenhouse and Lever — 4 times a day
0 */6 * * * cd /path/to/ams-alternative && python3 -m jobagg sync greenhouse --seed-file jobagg/seeds/greenhouse.txt >> logs/gh.log 2>&1
30 */6 * * * cd /path/to/ams-alternative && python3 -m jobagg sync lever --seed-file jobagg/seeds/lever.txt >> logs/lever.log 2>&1

# Arbeitnow — every 3 hours
15 */3 * * * cd /path/to/ams-alternative && python3 -m jobagg sync arbeitnow --pages 5 >> logs/arbeitnow.log 2>&1
```

## 9. AMS — manual links only

AMS (Arbeitsmarktservice Austria) **must not** be synced automatically — their ToS prohibit automated mass job search. Only user-provided deeplinks may be stored.

## 10. Run tests

```bash
python3 -m pytest jobagg/tests/ -v
```
