# Veneto City Data API

Veneto City Data API is an asynchronous FastAPI service that combines official Italian open
data to describe municipalities in Veneto with more than 50,000 residents. It turns two large,
source-specific CSV datasets into a small, typed JSON API and a flat CSV export.

The population threshold is evaluated from the source data at runtime. City names and the list
of eligible municipalities are never hardcoded.

## Features

- Retrieve the latest demographic profile for Veneto's largest municipalities.
- Combine population data from ISTAT with municipal income data from the Italian Ministry of
  Economy and Finance (MEF).
- Report total population, sex distribution, broad age groups, and average age.
- Report taxpayers, total declared income, average income per taxpayer, and total net tax.
- Sort results by name, population, or average income.
- Export the complete collection as CSV.
- Cache upstream ZIP files for 24 hours and fall back to stale data during temporary outages.
- Keep the reference year and retrieval metadata of each source visible in every response.

## Data Sources

| Provider | Dataset | Current reference | Purpose |
| --- | --- | --- | --- |
| [ISTAT](https://demo.istat.it/app/?i=POS&l=en) | Resident population by age and sex | January 1, 2026 | Demographics and population threshold |
| [MEF — Department of Finance](https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?tree=2025) | Municipal personal income tax statistics | Tax year 2024 | Income and tax indicators |

ISTAT open data is published under the Creative Commons Attribution 4.0 license. MEF's open
data terms permit reuse with attribution to “MEF — Dipartimento delle Finanze.” This project
does not redistribute the source archives; it downloads and caches them when the API is used.

The providers publish on different schedules. Demographic and economic values therefore have
independent `reference_year` fields and must not be interpreted as observations from the same
period.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Check application availability |
| `GET` | `/api/v1/cities` | List eligible Veneto municipalities |
| `GET` | `/api/v1/cities/{istat_code}` | Retrieve one eligible municipality |
| `GET` | `/api/v1/cities/export.csv` | Download the collection as CSV |

The list and export endpoints accept the same query parameters:

| Parameter | Values | Default |
| --- | --- | --- |
| `sort` | `name`, `population`, `average_income` | `name` |
| `direction` | `asc`, `desc` | `asc` |

Example requests:

```bash
curl http://127.0.0.1:8000/api/v1/cities
curl "http://127.0.0.1:8000/api/v1/cities?sort=population&direction=desc"
curl http://127.0.0.1:8000/api/v1/cities/028060
curl -OJ http://127.0.0.1:8000/api/v1/cities/export.csv
```

Example response (values abbreviated):

```json
{
  "count": 5,
  "minimum_population": 50000,
  "cities": [
    {
      "istat_code": "028060",
      "name": "Padova",
      "province": "Padova",
      "region": "Veneto",
      "demographics": {
        "population": 208202,
        "males": 100717,
        "females": 107485,
        "age_0_17": 27212,
        "age_18_64": 124685,
        "age_65_plus": 56305,
        "average_age": 47.65,
        "source": {
          "organization": "ISTAT",
          "url": "https://demo.istat.it/...",
          "reference_year": 2026,
          "retrieved_at": "2026-09-04T08:00:00Z",
          "stale": false
        }
      },
      "economics": {
        "taxpayers": 162532,
        "total_declared_income_eur": "5158296728",
        "average_income_per_taxpayer_eur": "31737.11",
        "total_net_tax_eur": "1087098743",
        "source": {
          "organization": "MEF — Dipartimento delle Finanze",
          "url": "https://www1.finanze.gov.it/...",
          "reference_year": 2024,
          "retrieved_at": "2026-09-04T08:00:00Z",
          "stale": false
        }
      }
    }
  ]
}
```

The example abbreviates source URLs; use the running API for complete metadata and current
observations. An absent economic observation is returned as `null`, never as a fabricated zero.

## Tech Stack

| Technology | Purpose |
| --- | --- |
| Python 3.14 | Runtime and type syntax |
| FastAPI + Uvicorn | ASGI API and OpenAPI documentation |
| HTTPX | Asynchronous source downloads |
| Pydantic | Public API models and validation |
| uv | Python installation, dependency management, and lockfile |
| Ruff | Linting and formatting |
| ty | Static type checking |
| pytest + respx | Tests and deterministic HTTP simulation |

## Architecture

```text
HTTP request
    → FastAPI router
    → city aggregation service
    → ISTAT and MEF clients
    → concurrency-safe file cache
    → official ZIP/CSV sources
```

Source clients parse provider-specific fields into internal records. The service joins those
records by the six-digit ISTAT municipality code and builds the public Pydantic models. No
database is required.

```text
src/veneto_city_data/
├── api/routes.py
├── clients/
│   ├── istat.py
│   └── mef.py
├── services/cities.py
├── cache.py
├── config.py
├── main.py
└── models.py
```

## Local Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Git

`uv` installs the required Python version automatically.

```bash
git clone git@github.com:medioalanum/veneto-city-data-api.git
cd veneto-city-data-api
uv python install
uv sync --frozen
uv run uvicorn veneto_city_data.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive OpenAPI documentation.

The first data request downloads both official archives. Later requests reuse files under
`data/cache/` until the 24-hour TTL expires.

## Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `CACHE_DIR` | `data/cache` | Local source archive directory |
| `CACHE_TTL_SECONDS` | `86400` | Fresh-cache lifetime |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Upstream HTTP timeout |
| `MINIMUM_POPULATION` | `50000` | Strict population threshold |
| `ISTAT_DATA_URL` | Current ISTAT ZIP URL | Override the demographic archive |
| `MEF_DATA_URL` | Current MEF ZIP URL | Override the income archive |

When a refresh fails, the API uses an existing expired archive and sets `stale` to `true`. If no
cached archive exists, affected requests return HTTP `503 Service Unavailable`.

Source URLs contain their reference year. Updating to a newly published edition only requires
changing the relevant URL; the response metadata automatically reflects its year.

## Testing and Quality

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest --cov=veneto_city_data --cov-report=term-missing
```

Tests use small in-memory ZIP fixtures and simulated HTTP responses. They never contact ISTAT or
MEF. GitHub Actions runs the same checks for every push to `main` and every pull request.

## Limitations

- Only the latest source archive configured for each provider is available; there is no
  historical query API.
- The 50,000-resident cutoff is strict: a municipality with exactly 50,000 residents is excluded.
- Average income is calculated as total declared income divided by the number of taxpayers; it is
  not household income or per-capita income.
- Upstream schemas and download URLs can change. Parser tests detect known schema changes, while
  environment variables allow source URLs to be updated without changing application code.

## License

The application source code is available under the [MIT License](LICENSE). Data remains subject
to the terms and attribution requirements of ISTAT and MEF.
