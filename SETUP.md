# SETUP — Как запустить jobagg

## 1. Требования

- Python 3.11+
- Интернет (для запросов к API)

## 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 3. Настройка .env

```bash
cp .env.example .env
```

Откройте `.env` в редакторе и заполните нужные значения:

| Переменная | Описание | Где взять | Обязательно |
|---|---|---|---|
| `JOBAGG_DB_PATH` | Путь к SQLite-файлу БД | Любой путь, например `./jobagg.db` | Нет (default: `jobagg.db`) |
| `JOBAGG_USER_AGENT` | User-Agent для HTTP-запросов | Укажите свой email: `jobagg/0.1 (+contact: YOUR@EMAIL.COM)` | Нет |
| `ADZUNA_APP_ID` | App ID для Adzuna API | [developer.adzuna.com](https://developer.adzuna.com) → My Apps → App ID | Только для Adzuna |
| `ADZUNA_APP_KEY` | App Key для Adzuna API | Та же страница → App Key | Только для Adzuna |

> **Важно:** `.env` не нужен для Bundesagentur и Arbeitnow — они работают без ключей.

## 4. Заполнить seed-файлы для Greenhouse и Lever

Greenhouse и Lever **не требуют API-ключей** для чтения вакансий. Нужно только указать, какие компании синкать.

### Greenhouse — `jobagg/seeds/greenhouse.txt`

Добавьте board tokens по одному на строку (без пробелов, без `#`):

```
netflix
shopify
airbnb
```

**Где найти board token:**
Откройте страницу вакансий компании. Если URL выглядит как `boards.greenhouse.io/netflix` — токен это `netflix`.

### Lever — `jobagg/seeds/lever.txt`

Добавьте site names по одному на строку:

```
netflix
stripe
revolut
```

**Где найти site name:**
Откройте страницу вакансий компании. Если URL выглядит как `jobs.lever.co/stripe` — site name это `stripe`.

## 5. Инициализация БД

```bash
python3 -m jobagg init-db
```

Создаёт таблицы `sources`, `jobs`, `sync_runs` в файле `jobagg.db` (или по пути из `JOBAGG_DB_PATH`).

## 6. Синхронизация вакансий

### Bundesagentur (Германия, без ключей)

```bash
python3 -m jobagg sync bundesagentur \
  --query "Python Developer" \
  --location "Berlin" \
  --pages 3 \
  --days 7
```

| Флаг | Описание | Default |
|---|---|---|
| `--query` | Поисковый запрос | `developer` |
| `--location` | Город или регион | — |
| `--pages` | Максимум страниц за прогон | `1` |
| `--days` | Только вакансии за последние N дней | `7` |

### Greenhouse (ATS, без ключей)

```bash
python3 -m jobagg sync greenhouse \
  --seed-file jobagg/seeds/greenhouse.txt
```

### Lever (ATS, без ключей)

```bash
python3 -m jobagg sync lever \
  --seed-file jobagg/seeds/lever.txt
```

### Arbeitnow (EU-агрегатор, без ключей)

```bash
python3 -m jobagg sync arbeitnow --pages 5
```

### Adzuna (только при наличии ключей и права использования)

> **ВНИМАНИЕ:** Adzuna ToS ограничивают ongoing commercial aggregation после 14-дневного trial без письменного соглашения. Не запускайте без ключей и не используйте как production-source без лицензии.

Adzuna-адаптер будет добавлен позже. Для подключения потребуется:
1. Зарегистрировать аккаунт на [developer.adzuna.com](https://developer.adzuna.com)
2. Заполнить `ADZUNA_APP_ID` и `ADZUNA_APP_KEY` в `.env`
3. Ознакомиться с [Terms of Service](https://developer.adzuna.com/terms)

## 7. Просмотр данных

```bash
# Последние 20 вакансий по всем источникам
python3 -m jobagg list-jobs

# Только Германия
python3 -m jobagg list-jobs --country DE --limit 50

# Детали вакансии по id
python3 -m jobagg show-job --id 1
```

## 8. Автоматизация через cron

Пример crontab для регулярного синка:

```cron
# Bundesagentur — каждый час
0 * * * * cd /path/to/ams-alternative && python3 -m jobagg sync bundesagentur --query "Python" --location "Berlin" --pages 3 >> logs/ba.log 2>&1

# Greenhouse и Lever — 4 раза в день
0 */6 * * * cd /path/to/ams-alternative && python3 -m jobagg sync greenhouse --seed-file jobagg/seeds/greenhouse.txt >> logs/gh.log 2>&1
30 */6 * * * cd /path/to/ams-alternative && python3 -m jobagg sync lever --seed-file jobagg/seeds/lever.txt >> logs/lever.log 2>&1

# Arbeitnow — каждые 3 часа
15 */3 * * * cd /path/to/ams-alternative && python3 -m jobagg sync arbeitnow --pages 5 >> logs/arbeitnow.log 2>&1
```

## 9. AMS — только ручная ссылка

AMS (Arbeitsmarktservice Österreich) **нельзя** синкать автоматически — их ToS запрещают automated mechanisms для masse job search. Сохранять можно только ручную ссылку пользователя.

## 10. Запуск тестов

```bash
python3 -m pytest jobagg/tests/ -v
```
