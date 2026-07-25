# UrbanFlow Location Intelligence

[![Tests](https://github.com/mertcanpolat/urbanflow-location-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/mertcanpolat/urbanflow-location-intelligence/actions/workflows/tests.yml)

UrbanFlow Location Intelligence is a full-stack geospatial data project developed to analyse New York City Yellow Taxi demand by location and time.

The project combines spatial ETL, PostgreSQL/PostGIS, a FastAPI backend, and an interactive Leaflet dashboard. Its main purpose is not only to produce a working application, but also to demonstrate how a GIS-oriented data product can be designed with maintainable software architecture, testing, containerisation, and technical documentation.

## Project Status

### Sprint 1 — Data Pipeline and Dashboard

- ETL pipeline
- PostgreSQL and PostGIS
- FastAPI
- Leaflet
- Chart.js
- Materialized View
- Interactive dashboard

### Sprint 2 — Software Architecture and Engineering

- Modular code structure
- Router–Service–Repository architecture
- Logging
- Centralised exception handling
- Pytest test suite
- Dockerfile
- Docker Compose
- Git repository
- GitHub repository
- Technical documentation

## Project Objectives

UrbanFlow aims to answer questions such as:

- Which taxi zones generate the highest pickup demand?
- How does demand change by date and hour?
- How are trips distributed across boroughs?
- Which zones should be prioritised for mobility, transport, or location-intelligence analysis?
- How can large spatial datasets be exposed through a clean and testable API?

## Technology Stack

| Layer | Technologies |
|---|---|
| Data source | NYC Yellow Taxi trip data, NYC Taxi Zones |
| ETL | Python, GeoPandas/Pandas-based processing scripts |
| Database | PostgreSQL 17, PostGIS 3.5 |
| Backend | FastAPI, SQLAlchemy, Psycopg |
| Validation | Pydantic |
| Frontend | HTML, CSS, JavaScript |
| Mapping | Leaflet |
| Charts | Chart.js |
| Testing | Pytest, HTTPX |
| Containerisation | Docker, Docker Compose |
| Version control | Git, GitHub |

## System Architecture

The application follows a layered architecture:

```text
Client / Dashboard
        |
        v
FastAPI Router Layer
        |
        v
Service Layer
        |
        v
Repository Layer
        |
        v
PostgreSQL + PostGIS
```

### Router Layer

The router layer defines HTTP endpoints, validates incoming parameters, and returns API responses.

Main router modules:

- `api/routers/system.py`
- `api/routers/dashboard.py`
- `api/routers/zones.py`

### Service Layer

The service layer contains application-level logic and coordinates operations between routers and repositories.

Main service modules:

- `api/services/dashboard_service.py`
- `api/services/zone_service.py`

### Repository Layer

The repository layer is responsible for SQL queries and database access.

Main repository modules:

- `api/repositories/dashboard_repository.py`
- `api/repositories/zone_repository.py`

This separation keeps HTTP handling, business logic, and database operations independent from one another.

## Data Flow

```text
Public taxi datasets
        |
        v
Download scripts
        |
        v
Inspection and validation
        |
        v
ETL and data loading
        |
        v
PostgreSQL + PostGIS
        |
        v
Materialized views and SQL queries
        |
        v
FastAPI endpoints
        |
        v
Leaflet map and Chart.js dashboard
```

## Project Structure

```text
urbanflow-location-intelligence/
│
├── api/
│   ├── core/
│   │   ├── exceptions.py
│   │   └── logging_config.py
│   │
│   ├── models/
│   │   ├── filters.py
│   │   └── responses.py
│   │
│   ├── repositories/
│   │   ├── dashboard_repository.py
│   │   └── zone_repository.py
│   │
│   ├── routers/
│   │   ├── dashboard.py
│   │   ├── system.py
│   │   └── zones.py
│   │
│   ├── services/
│   │   ├── dashboard_service.py
│   │   └── zone_service.py
│   │
│   ├── database.py
│   └── main.py
│
├── database/
│   ├── init/
│   └── queries/
│
├── src/
│   ├── download_taxi_zones.py
│   ├── download_yellow_trips.py
│   ├── inspect_taxi_zones.py
│   ├── inspect_yellow_trips.py
│   ├── load_taxi_zones.py
│   └── load_yellow_trips.py
│
├── tests/
│   ├── conftest.py
│   ├── test_dashboard.py
│   ├── test_system.py
│   └── test_zones.py
│
├── web/
│   ├── app.js
│   ├── index.html
│   └── styles.css
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── compose.yaml
└── requirements.txt
```

## Main Features

### Spatial Taxi-Zone Map

Taxi zones are returned from the backend as GeoJSON and displayed on a Leaflet map.

The map can be used to:

- visualise spatial demand distribution,
- compare taxi zones,
- inspect zone-level metrics,
- filter results by borough and time,
- connect map interactions with dashboard charts.

### Dashboard KPIs

The dashboard exposes summary indicators such as:

- total trip count,
- filtered trip count,
- average trip distance,
- average total amount,
- number of taxi zones,
- date range of the dataset.

### Demand Analysis

The application supports:

- daily demand trends,
- hourly demand profiles,
- top taxi-zone rankings,
- borough filtering,
- date filtering,
- zone-level analysis.

### Materialized View

Aggregated data can be stored in a PostgreSQL materialized view.

This reduces repeated computation for dashboard queries and improves response performance when the underlying trip table is large.

## API Endpoints

FastAPI automatically generates interactive API documentation.

After the application starts:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Dashboard: `http://localhost:8000/map`

### System Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Returns basic API information |
| GET | `/health` | Checks API and database health |
| GET | `/map` | Serves the web dashboard |
| GET | `/api/v1/summary` | Returns general dataset statistics |

### Dashboard Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Returns filtered dashboard KPIs |
| GET | `/api/v1/dashboard/daily-trend` | Returns daily trip-demand values |

### Zone Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/boroughs` | Returns available borough names |
| GET | `/api/v1/zones/top` | Returns zones with the highest overall demand |
| GET | `/api/v1/zones/geojson` | Returns filtered taxi zones as GeoJSON |
| GET | `/api/v1/zones/ranking` | Returns filtered zone rankings |
| GET | `/api/v1/zones/{location_id}/hourly` | Returns hourly demand for one taxi zone |

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
POSTGRES_DB=urbanflow
POSTGRES_USER=urbanflow_user
POSTGRES_PASSWORD=change_this_password
POSTGRES_PORT=5432

PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=change_this_password
PGADMIN_PORT=5050

DB_HOST=localhost
DB_PORT=5432
DB_NAME=urbanflow
DB_USER=urbanflow_user
DB_PASSWORD=change_this_password
```

Do not commit the real `.env` file to GitHub.

For a public repository, an `.env.example` file should be included with placeholder values.

## Running with Docker Compose

### Requirements

- Docker Desktop
- Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/mertcanpolat/urbanflow-location-intelligence.git
cd urbanflow-location-intelligence
```

### 2. Create the environment file

Create `.env` in the project root and add the required variables.

### 3. Build and start the services

```bash
docker compose up --build
```

The Compose configuration starts:

- PostGIS database
- pgAdmin
- FastAPI application

### 4. Open the services

- API: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/map`
- pgAdmin: `http://localhost:5050`

### 5. Stop the services

```bash
docker compose down
```

To remove the database and pgAdmin volumes as well:

```bash
docker compose down -v
```

> Warning: removing volumes deletes the persisted local database data.

## Running Locally without Docker

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure the database connection

Create the `.env` file and make sure PostgreSQL/PostGIS is running.

When the API runs outside Docker, `DB_HOST` should normally be:

```env
DB_HOST=localhost
```

### 4. Start the API

```bash
python -m uvicorn api.main:app --reload
```

## Running the Tests

The project uses Pytest for API and application tests.

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run a specific test module:

```bash
pytest tests/test_zones.py -v
```

The current test suite covers system, dashboard, and taxi-zone behaviour.

## Logging

Application logging is configured centrally in:

```text
api/core/logging_config.py
```

The routers and services use named loggers to record:

- incoming requests,
- successful operations,
- query results,
- invalid resources,
- database failures,
- unexpected application errors.

Centralised logging makes debugging and production monitoring easier than scattered `print()` statements.

## Exception Handling

Global exception handlers are registered in:

```text
api/core/exceptions.py
```

This provides consistent error responses and prevents raw internal errors from being exposed directly to API consumers.

Expected examples include:

- `404 Not Found` for an unknown taxi zone,
- `503 Service Unavailable` for database connectivity problems,
- `500 Internal Server Error` for unexpected database or application failures.

## Database Connection Management

The SQLAlchemy engine is defined in:

```text
api/database.py
```

The database URL is created from environment variables.

Current connection-pool configuration:

- `pool_pre_ping=True`
- `pool_size=5`
- `max_overflow=10`

`pool_pre_ping` checks whether a pooled database connection is still valid before it is reused.

## Why PostGIS?

PostGIS extends PostgreSQL with spatial data types and geospatial operations.

In UrbanFlow it enables the application to:

- store taxi-zone geometries,
- execute spatial SQL,
- return geometries as GeoJSON,
- connect trip statistics to geographic zones,
- support future proximity, accessibility, and spatial-pattern analyses.

## Why FastAPI?

FastAPI was selected because it provides:

- automatic request validation,
- Pydantic response models,
- automatic Swagger and ReDoc documentation,
- dependency injection,
- clear route organisation,
- good performance for data APIs,
- straightforward testing with HTTPX and Pytest.

## Why Router–Service–Repository?

The layered architecture improves maintainability.

```text
Router:
Receives HTTP requests and returns HTTP responses.

Service:
Applies application rules and coordinates the operation.

Repository:
Communicates with PostgreSQL and executes SQL.
```

Benefits:

- database code does not remain inside endpoint functions,
- HTTP concerns do not leak into SQL modules,
- components can be tested independently,
- future features can be added with less duplication,
- the codebase is closer to real production application structures.

## Current Limitations

- The project currently focuses on local and Docker-based execution.
- Production deployment configuration is not yet complete.
- Database migrations are not yet managed by a migration tool.
- Authentication and authorisation are not implemented.
- Automated CI/CD is not yet configured.
- Test coverage reporting is not yet included.
- Materialized-view refresh automation can be improved.

## Planned Improvements

### Deployment and DevOps

- Add `.env.example`
- Add production-specific Compose configuration
- Add health checks for all services
- Add non-root Docker user
- Pin dependency versions
- Add GitHub Actions
- Add automated tests on every push
- Add coverage reporting
- Add reverse proxy configuration
- Add cloud deployment

### Data and Performance

- Add database indexes and query analysis
- Measure endpoint response times
- Improve materialized-view refresh strategy
- Introduce pagination where required
- Add caching
- Add larger taxi datasets
- Add asynchronous or scheduled ETL jobs

### Advanced Location Intelligence

- Spatiotemporal hotspot analysis
- Demand clustering
- Origin–destination analysis
- Accessibility analysis
- Demand forecasting
- Taxi-zone segmentation
- Location scoring
- Service-area optimisation

### User Experience

- Responsive dashboard improvements
- Advanced map legends
- Loading and error states
- More interactive filters
- Downloadable reports
- Layer controls
- Comparison mode
- Improved chart interactions

## Learning Outcomes

This project is designed as a practical GIS software-engineering learning programme.

Topics applied in the project include:

- spatial ETL,
- relational and spatial database design,
- PostGIS queries,
- REST API design,
- layered backend architecture,
- frontend-to-API communication,
- interactive web mapping,
- dashboard development,
- environment-variable management,
- automated testing,
- exception handling,
- logging,
- Docker containerisation,
- Git and GitHub workflows,
- technical documentation.

## Development Approach

UrbanFlow is developed in weekly sprints.

Each sprint includes:

1. A working software increment
2. Architectural improvement
3. Testing
4. Technical explanation
5. Documentation
6. Git commit and GitHub update

The goal is to build both a functioning location-intelligence application and a documented portfolio project that demonstrates GIS, data engineering, backend development, and software-engineering skills.

## Author

**Mertcan Polat**

Geomatics Engineer and GIS professional focusing on:

- Geographic Information Systems
- Location Intelligence
- Spatial Data Engineering
- Python
- PostGIS
- Web GIS
- Data Analytics

GitHub: [mertcanpolat](https://github.com/mertcanpolat)

## Licence

A licence has not yet been selected.

Before wider reuse or external contribution, add an appropriate licence such as MIT, Apache-2.0, or another licence that matches the intended use of the project.
