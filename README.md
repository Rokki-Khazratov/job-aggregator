# jobagg — DACH Job Aggregator MVP

Минимальный CLI-инструмент для сбора вакансий из нескольких юридически нормальных источников, нормализации в единую схему и хранения в SQLite.

## Источники

| Источник | Тип | Auth | Роль |
|---|---|---|---|
| Bundesagentur für Arbeit | API | Нет (публичный key) | Базовый DE-источник |
| Greenhouse Job Board API | ATS | Нет | Direct-employer feed |
| Lever Postings API | ATS | Нет | Direct-employer feed |
| Arbeitnow | Aggregator | Нет | EU/DACH feed |
| Adzuna | Aggregator | app_id + app_key | Licensed enrichment (опционально) |

> **AMS** не поддерживается как автоматический источник — их условия запрещают automated aggregation.

## Быстрый старт

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Настроить окружение
cp .env.example .env
# Отредактируйте .env при необходимости

# 3. Инициализировать БД
python3 -m jobagg init-db

# 4. Синкнуть вакансии
python3 -m jobagg sync bundesagentur --query "Python" --location "Berlin" --pages 2

# 5. Посмотреть результат
python3 -m jobagg list-jobs --country DE --limit 10
python3 -m jobagg show-job --id 1
```

Подробная инструкция: [SETUP.md](SETUP.md)

## Структура проекта

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
    greenhouse.txt ← board tokens (заполнить вручную)
    lever.txt      ← site names (заполнить вручную)
  tests/           ← pytest + httpx.MockTransport
```

## CLI

```bash
python3 -m jobagg init-db
python3 -m jobagg sync bundesagentur --query STR [--location STR] [--pages N] [--days N]
python3 -m jobagg sync greenhouse --seed-file PATH
python3 -m jobagg sync lever --seed-file PATH
python3 -m jobagg sync arbeitnow [--pages N]
python3 -m jobagg list-jobs [--country CODE] [--limit N]
python3 -m jobagg show-job --id N
```

## Тесты

```bash
python3 -m pytest jobagg/tests/ -v
```

## Legal

- **Bundesagentur:** Публичный API. Не скрейпить контактные данные (CAPTCHA-protected).
- **Greenhouse / Lever:** Published job board APIs, read-only. Не использовать POST-apply endpoints.
- **Arbeitnow:** Free public API. Не злоупотреблять частотой запросов.
- **Adzuna:** Trial 14 дней. Ongoing commercial aggregation требует письменного соглашения.
- **AMS:** Automated aggregation запрещена ToS. Только ручные ссылки.
