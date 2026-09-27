# solar-radiation_open-meteo

Flask API that fetches solar radiation variables from **Open-Meteo** and stores them in **MySQL**.

## Local setup

### 1) Create a virtualenv + install (uv)

```bash
cd solar-radiation_open-meteo
uv venv
source .venv/bin/activate

# Install from the lockfile (recommended)
uv sync

# Or install editable without the lockfile
# uv pip install -e .
```

If you prefer classic `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your MySQL settings. You can use either:

- `DATABASE_URL` (recommended), or
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`

### 3) Create tables

```bash
flask --app solar_radiation_api:create_app init-db
```

### 4) Run the API

```bash
flask --app solar_radiation_api:create_app run --debug
```

Health check:

```bash
curl http://127.0.0.1:5000/health
```

## Ingest Open-Meteo data

This API uses **API keys**. You create users with an **admin key**, then users can ingest data.

### 0) Create an API user

1) Set `ADMIN_API_KEY` in your `.env`.

2) Call the admin endpoint to create a user (choose an API key you will store securely):

```bash
curl -X POST http://127.0.0.1:5000/api/users \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: YOUR_ADMIN_API_KEY' \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "api_key": "alice-dev-key"
  }'
```

3) Use that API key on ingestion calls:

- `Authorization: Bearer <api_key>` (recommended)
- or `X-API-Key: <api_key>`

### POST `/api/ingest/open-meteo`

Example (hourly):

```bash
curl -X POST http://127.0.0.1:5000/api/ingest/open-meteo \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer alice-dev-key' \
  -d '{
    "latitude": 4.7110,
    "longitude": -74.0721,
    "start_date": "2024-01-01",
    "end_date": "2024-01-07",
    "timezone": "UTC",
    "product": "archive",
    "hourly": [
      "temperature_2m",
      "terrestrial_radiation",
      "global_tilted_irradiance",
      "direct_normal_irradiance",
      "diffuse_radiation",
      "direct_radiation",
      "shortwave_radiation",
      "terrestrial_radiation_instant",
      "global_tilted_irradiance_instant",
      "direct_normal_irradiance_instant",
      "diffuse_radiation_instant",
      "direct_radiation_instant",
      "shortwave_radiation_instant"
    ],
    "daily": [],
    "replace_existing": true
  }'
```

Notes:
- `product`: `archive` (historical) or `forecast` (recent/future).
- `hourly`: if omitted or `[]`, the API uses the default list above and validates variables.
- `daily`: you can pass Open-Meteo daily variable names (not validated yet).
- `replace_existing=true` deletes matching existing rows (same lat/lon/interval/variable/time range) before inserting.

Every measurement row stores who inserted it in `created_by_user_id` / `created_by_username`.

### GET `/api/measurements`

```bash
curl 'http://127.0.0.1:5000/api/measurements?latitude=4.711&longitude=-74.0721&variable=shortwave_radiation&interval=hourly&start=2024-01-01T00:00&end=2024-01-02T00:00&limit=200'
```

## Using your remote server (SSH tunnel)

You shared:
- server: `141.148.172.198`
- user: `ubuntu`
- SSH public key already on the server

A simple workflow is:

1) Create an SSH tunnel from your laptop to the server’s MySQL port:

```bash
ssh -L 3307:127.0.0.1:3306 ubuntu@141.148.172.198
```

2) Point the API to localhost:3307:

```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3307
```

(Or set `DATABASE_URL` accordingly.)

## Create the GitHub repo

If you have GitHub CLI set up:

```bash
gh repo create solar-radiation_open-meteo --public --source=. --remote=origin --push
```

Otherwise:

1) Create a new repository named `solar-radiation_open-meteo` on GitHub.
2) Add it as a remote and push:

```bash
git remote add origin git@github.com:<YOUR_GH_USERNAME>/solar-radiation_open-meteo.git
git add -A
git commit -m "Initial Flask + MySQL API scaffold"
git push -u origin main
```

## Next steps (Docker)

### Run locally with Docker Compose

This starts:
- `db`: MySQL 8.0
- `api`: Flask API (Gunicorn)

```bash
cd solar-radiation_open-meteo
docker compose up --build
```

API will be on:

```bash
curl http://127.0.0.1:8000/health
```

Defaults are defined in `docker-compose.yml` (including `ADMIN_API_KEY`). Change those before using outside local dev.

### Deployment later

When you’re ready to deploy to your server, we can reuse the same `Dockerfile` and provide:
- a production `docker-compose.yml` (no public MySQL port)
- persistent volumes
- proper secrets management
- reverse proxy (Caddy/Nginx) + TLS
