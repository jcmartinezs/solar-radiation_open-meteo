# solar-radiation_open-meteo

Flask API that fetches solar radiation variables from **Open-Meteo** and stores them in **MySQL**.

## Local setup

### 1) Create a virtualenv + install

```bash
cd solar-radiation_open-meteo
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
# (or) pip install -r requirements.txt
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

### POST `/api/ingest/open-meteo`

Example (hourly):

```bash
curl -X POST http://127.0.0.1:5000/api/ingest/open-meteo \
  -H 'Content-Type: application/json' \
  -d '{
    "latitude": 4.7110,
    "longitude": -74.0721,
    "start_date": "2024-01-01",
    "end_date": "2024-01-07",
    "timezone": "UTC",
    "product": "archive",
    "hourly": ["shortwave_radiation", "direct_radiation", "diffuse_radiation"],
    "daily": [],
    "replace_existing": true
  }'
```

Notes:
- `product`: `archive` (historical) or `forecast` (recent/future).
- `hourly` / `daily`: pass any variable names supported by Open-Meteo for that endpoint.
- `replace_existing=true` deletes matching existing rows (same lat/lon/interval/variable/time range) before inserting.

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

When you’re ready, we can add:
- `Dockerfile` for the API
- `docker-compose.yml` with a local MySQL container
- production settings + deployment instructions
