# Climate Summariser

Simple words, full story.  
This project downloads public UK Met Office summaries, saves them to your database, and shows the numbers through APIs plus a tiny dashboard. Everything is automated so you can focus on insight, not plumbing.

---

## 1. Why this exists

1. The Met Office shares brilliant historic climate data, but mostly as plain text files.
2. Analysts need something friendlier: a database, APIs, and a chart.
3. We built a pipeline that keeps that data up to date and easy to explore.

---

## 2. What you get

- **Ingestion engine** – parses Met Office `.txt` files into structured records.
- **Data model** – regions, parameters, and climate records with timestamps.
- **REST APIs** – rich filters, summary stats, synchronous dataset ingest and an async trigger endpoint.
- **Dashboard** – one page that lets non-developers explore the data visually.
- **Docker stack** – Postgres, Django web app, and a background worker in one command.
- **Docs & tests** – so future teammates know how to run and extend it.

---

## 3. System overview

| Layer | Job | Files |
| --- | --- | --- |
| Django app | Models, APIs, admin, HTML | `weather/models.py`, `weather/api.py`, `templates/weather/dashboard.html` |
| Services | Download + parse + bulk insert | `weather/services/metoffice.py` |
| Commands | Manual ingestion entry point | `weather/management/commands/ingest_metoffice.py` |
| Worker | Celery worker + Redis queue for scheduled/API ingests | `weather/tasks.py`, `scripts/ingest_worker.sh`, `docker-compose.yml` |
| Frontend | Chart + filters + table | `static/js/dashboard.js`, `static/css/dashboard.css` |

---

## 4. How the data flows (story form)

1. **Choose a dataset**  
   Every link looks like `https://www.metoffice.gov.uk/pub/data/weather/uk/climate/datasets/Tmax/date/UK.txt`.

2. **Download & parse**  
   The service reads the header (“Last updated …”) and the table that starts with `year jan feb … ann`. Missing values such as `---` are ignored.

3. **Store**  
   Each cell becomes a `ClimateRecord` row with:
   - region & parameter (FKs)
   - year
   - period type (`month`, `season`, `annual`)
   - period (`jan`, `win`, `ann`, …)
   - value
   - `source_last_updated` (from Met Office)
   - `fetched_at` (when we pulled it)

4. **Serve & visualise**  
   - `/api/records/` for raw numbers (with pagination/filters).  
   - `/api/records/summary/` for min/max/avg across the filtered slice.  
   - `/` dashboard for people who want charts, not JSON.

5. **Keep it fresh**  
   - Run `python manage.py ingest_metoffice ...` yourself.  
   - Keep the Celery worker + Redis stack running; it handles scheduled or API-triggered jobs.  
   - POST a dataset URL to `/api/ingest/` for a one-off import or call `/api/ingest/trigger/` to queue a background refresh.

---

## 5. Running locally (no Docker)

```bash
python -m venv .venv
. .venv/bin/activate           # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp env.example .env
```

Edit `.env` (use simple words):

```
DJANGO_SECRET_KEY=anything-secret
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:pass@host:5432/db  # required PostgreSQL DSN
DATABASE_SSL_REQUIRE=0                          # set to 1 only if your Postgres demands TLS
CSRF_TRUSTED_ORIGINS=https://your-domain.com     # comma-separated, with scheme
```

Make sure PostgreSQL is running and reachable at the host/port you provided. A quick local option:

```
docker run --name climate-db -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=climate -d postgres:15-alpine
```

Then:

```bash
python manage.py migrate
python manage.py ingest_metoffice --regions UK --parameters Tmax
python manage.py runserver
```

Browse `http://127.0.0.1:8000` for the dashboard or call the APIs.

---

## 6. Running with Docker Compose

```
docker compose up --build
```

What spins up:

- `db` – Postgres 15, data stored in the `pgdata` volume.
- `redis` – lightweight broker backing Celery.
- `web` – Django dev server. It auto-runs migrations + collectstatic before starting.
- `worker` – Runs migrations, optionally performs an immediate ingest, then launches `celery -A config worker`.

Environment dials:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | docker-compose-secret | Change for real deployments. |
| `DATABASE_URL` | postgres://postgres:postgres@db:5432/climate | Already points to the Compose DB. |
| `DATABASE_SSL_REQUIRE` | 0 | Leave 0 for local containers. Set 1 if targeting a remote TLS-only DB. |
| `CELERY_BROKER_URL` | redis://redis:6379/0 | Broker/result backend for Celery. |
| `INGEST_REGIONS` | *(all)* | e.g. `UK SCOTLAND`. |
| `INGEST_PARAMETERS` | *(all)* | e.g. `Tmax Rainfall`. |
| `RUN_INITIAL_INGEST` | 1 | Set to 0 to skip the startup `ingest_metoffice` run. |
| `CELERY_CONCURRENCY` | 1 | Number of worker processes.

Example (UK-only ingestion, two Celery workers):

```
INGEST_REGIONS="UK" CELERY_CONCURRENCY=2 docker compose up worker
```

---

## 7. API reference (plain English)

| Path | Method | Why you’d call it |
| --- | --- | --- |
| `/api/regions/` | GET | See all available regions. |
| `/api/parameters/` | GET | See all parameters (Tmax, Rainfall, Sunshine…). |
| `/api/records/` | GET | Fetch the actual climate numbers. Use filters. |
| `/api/records/summary/` | GET | Quick stats (min, max, average, count, first year, last year). |
| `/api/ingest/` | POST JSON `{ "url": "<met office txt>" }` | Ingest that exact dataset link immediately. |
| `/api/ingest/trigger/` | POST JSON `{ "regions": [], "parameters": [] }` | Queue a Celery job that re-runs `ingest_metoffice` filters. |

Filters supported on records + summary endpoints:

- `region`
- `parameter`
- `period_type` (`month`, `season`, `annual`)
- `period` (`jan`, `win`, `ann`, …)
- `start_year`, `end_year`
- `ordering` (e.g. `year,period` or `-value`)
- `limit`, `offset`

Example request:

```
/api/records/?region=UK&parameter=Tmax&period_type=month&start_year=1990&ordering=year,period&limit=5000
```

Response fields include region/parameter names, value, year, period, `source_last_updated`, and `fetched_at`.

---

## 8. Dashboard tour

- **Filters** – choose region, parameter, period type, optional year range.
- **Summary cards** – show count/min/max/average using the API summary.
- **Trend chart** – Chart.js line plot with auto-colour and auto-skip ticks.
- **Table** – scrollable list of raw values (year + period + value).
- **Source link** – quick jump to the Met Office page for transparency.

No bundlers, no heavy frontend stack. Just HTML + CSS + vanilla JS.

---

## 9. Management commands

| Command | Description |
| --- | --- |
| `python manage.py ingest_metoffice [--regions …] [--parameters …]` | Downloads the chosen datasets and upserts them into the DB. |

Reference data (regions & parameters) is seeded during migrations, so you can call the command immediately after `python manage.py migrate`.

---

## 10. Background worker (what it actually does)

1. Runs `python manage.py migrate` (safety first).
2. Optionally executes `python manage.py ingest_metoffice` once on boot using any filters supplied via `INGEST_*`.
3. Launches `celery -A config worker` which:
   - Listens on Redis for jobs coming from `/api/ingest/trigger/`, scheduled beats, or manual `.delay()` calls.
   - Streams logs back to the container so you can tail progress.

No more tight polling loop—the worker sits idle until a task arrives, then ingests the requested regions/parameters concurrently.

---

## 11. Deployment cheat sheet (Render example)

1. Push code to GitHub.
2. Create a Render Web Service.
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
4. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
5. Environment:
   - `DJANGO_SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`.
   - `DATABASE_URL` (Render Postgres string).
   - `DATABASE_SSL_REQUIRE=1` (Render Postgres requires TLS).
6. Run `python manage.py ingest_metoffice ...` once (via Render shell or locally pointing to the prod DB).

Other clouds (Fly.io, Railway, Azure) follow the same pattern: build image, supply env vars, run ingestion, optionally run the worker as another service.

---

## 12. Testing

```
python manage.py test
```

Coverage includes:

- Parser & ingestion logic (mocked HTTP).
- API filters and summary endpoint.
- Dataset-ingest POST endpoint.
- Celery trigger endpoint validation / task dispatch.

---

## 13. Troubleshooting table

| Issue | Fix |
| --- | --- |
| `server does not support SSL, but SSL was required` | Set `DATABASE_SSL_REQUIRE=0` when talking to the local Compose DB. |
| `/api/ingest/` says “Unknown parameter/region” | Ensure the URL follows `.../<Parameter>/<order>/<Region>.txt` (e.g. `Tmax/date/UK.txt`). |
| Dashboard shows “No data available” | Run ingestion or verify the worker logs. |
| Worker restarts repeatedly | Ensure Redis is reachable (`CELERY_BROKER_URL`) and `INGEST_*` filters are valid—tracebacks appear in the Celery logs. |
| Large API calls are slow | Use pagination (`limit/offset`) or add caching/indices as next steps. |

---

## 14. Project layout

```
config/                  # Django project (settings, URLs, WSGI/ASGI)
weather/                 # App (models, serializers, APIs, services, tests)
templates/weather/       # Dashboard HTML
static/css & static/js   # Dashboard styling and behaviour
scripts/                 # start_web.sh, ingest_worker.sh
Dockerfile               # Production-ready image (Gunicorn)
docker-compose.yml       # Web + worker + Postgres
Procfile                 # Heroku/Render command
env.example              # Copy to .env and tweak
```

---

## 15. Future ideas

- Add user logins / API keys if you open it to the public.
- Expose CSV download for the filtered dataset.
- Add alerting (email/Slack) when values cross thresholds.
- Add Redis caching for heavy summary queries.
- Build a comparison view (multiple regions/parameters on one chart).

Happy climate hacking! 🌦️

