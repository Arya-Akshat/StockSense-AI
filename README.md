# Stock Data Intelligence Dashboard

## Live Deployment

Deployment Link: `INSERT_DEPLOYMENT_LINK_HERE`

## Project Overview

Stock Data Intelligence Dashboard is a full-stack fintech analytics project built to demonstrate practical engineering skills across data ingestion, backend API design, analytical feature engineering, frontend visualization, and deployment readiness.

The project fetches historical stock market data for `INFY`, `TCS`, and `RELIANCE`, processes and enriches it with useful financial indicators, stores it in SQLite, and exposes it through a documented FastAPI backend. A lightweight dashboard built with HTML, CSS, JavaScript, and Chart.js then turns that data into an interactive visual experience.

This project is strong for internship evaluation and portfolio use because it shows:

- real-world API integration with `yfinance`
- clean layered backend architecture
- meaningful feature engineering on stock data
- practical error handling and caching
- a functional analytical dashboard instead of a static UI
- complete API documentation with Swagger and OpenAPI
- deployment readiness with Render and Docker support

## What This Project Does

At a high level, the platform works like this:

1. Fetch stock history from Yahoo Finance for NSE symbols.
2. Clean and normalize the raw data.
3. Compute derived analytics such as moving averages, returns, volatility, and price summaries.
4. Save the processed dataset in SQLite for local persistence.
5. Serve the data through FastAPI endpoints.
6. Display the insights in an interactive dashboard with charts, comparisons, movers, and prediction output.

The result is a mini stock analytics platform that is simple to run, realistic enough to discuss in interviews, and structured well enough to extend later.

## Why This Project Is Good

This project is a strong technical showcase because it combines several important engineering ideas in one coherent product:

- It uses real financial data instead of mock-only UI content.
- It follows a maintainable backend architecture: router -> service -> data layer.
- It includes both analytical metrics and user-facing visualization.
- It handles operational realities such as caching, startup ingestion, and deployment constraints.
- It includes thoughtful edge-case handling for unavailable data, invalid symbols, and prediction constraints.
- It is documented clearly enough for another developer or reviewer to understand quickly.

## Core Features

### Data Pipeline

- Fetches stock data for `INFY`, `TCS`, and `RELIANCE`
- Uses Yahoo Finance NSE tickers:
  - `INFY.NS`
  - `TCS.NS`
  - `RELIANCE.NS`
- Cleans and normalizes incoming data
- Converts dates and numeric columns safely
- Handles missing values with forward-fill and fallback logic
- Stores processed data in SQLite
- Maintains in-memory DataFrame caching with TTL refresh
- Falls back to deterministic mock data when external fetch fails

### Analytics

- Daily Return
- 7-Day Moving Average
- 52-Week High
- 52-Week Low
- Volatility:
  - 14-day rolling standard deviation of daily returns
- Top movers:
  - top gainers
  - top losers
- Linear regression next-price prediction:
  - trained on up to 90 days of close prices
  - predicts next 7 business days

### Backend API

- `GET /companies`
- `GET /data/{symbol}`
- `GET /summary/{symbol}`
- `GET /compare`
- `GET /top-movers`
- `GET /predict/{symbol}`
- Swagger docs with endpoint summaries, descriptions, and examples
- OpenAPI schema through `/openapi.json`
- Standardized JSON error responses
- Global exception handling with structured JSON error payloads

### Documentation and engineering improvements

- Interactive Swagger UI at `/docs`
- OpenAPI JSON specification at `/openapi.json`
- Detailed route summaries, descriptions, and example responses
- Deployment-ready configuration with Render and Docker
- Full project README with architecture, setup, screenshots, and design decisions
- Regression verification across backend endpoints, docs, and frontend assets

### Dashboard

- Sidebar symbol selector
- Date filters:
  - 7 days
  - 30 days
  - 90 days
- Closing price chart
- 7-day moving average overlay
- Prediction overlay for longer windows
- Normalized comparison chart
- Top movers panel
- Loading and inline error states

## Architecture Overview

The project follows a clean layered architecture so each part has a focused responsibility.

```text
Frontend Dashboard (Chart.js)
        |
        v
FastAPI Router Layer
        |
        v
StockService
        |
        +--> In-memory TTL Cache
        |
        v
DataService
        |
        +--> yfinance
        |
        v
SQLite Database
```

Explicit data flow:

`yfinance -> DataService -> SQLite -> StockService -> FastAPI Router -> Frontend (Chart.js)`

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.13 | Main application language |
| Backend | FastAPI | REST API and automatic docs |
| Data Processing | Pandas, NumPy | Cleaning, transformation, analytics |
| Data Source | yfinance | Historical market data |
| Database | SQLite | Local persistence |
| Machine Learning | scikit-learn | Linear regression prediction |
| Frontend | HTML, CSS, JavaScript | Dashboard interface |
| Visualization | Chart.js | Interactive charts |
| Deployment | Render | Cloud deployment |
| Containerization | Docker, docker-compose | Portable local and hosted setup |

## Folder Structure

```text
project/
|-- app/
|   |-- main.py
|   |-- models/
|   |-- routers/
|   |-- services/
|   |-- static/
|   `-- utils/
|-- data/
|-- images/
|-- Dockerfile
|-- docker-compose.yml
|-- render.yaml
|-- requirements.txt
`-- README.md
```

## Setup Instructions

### Prerequisites

- Python `3.13`
- `pip`
- optional: Docker Desktop

Important:

- Use Python `3.13`
- Do not use Python `3.14` for this project because `pydantic-core` may fail during dependency installation

### Local Setup

```bash
cd project
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Dashboard: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI schema: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### Docker Setup

```bash
docker-compose up --build
```

Open:

- [http://localhost:8000](http://localhost:8000)

### Render Deployment

This project is designed for Render deployment.

- Use `render.yaml`
- Python version is pinned to `3.13.5`
- Startup ingestion is already handled by the FastAPI lifespan hook
- Note that Render is stateless, so SQLite data in `data/` can reset between deploys

## API Documentation

The backend includes built-in interactive documentation so anyone reviewing the project can understand and test the API without reading the code first.

Available documentation:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

The API documentation was improved with:

- endpoint summaries
- multi-line endpoint descriptions
- response descriptions
- example payloads
- consistent endpoint tagging under `Stocks`

### `GET /companies`

Returns all supported company symbols.

Sample:

```bash
curl http://127.0.0.1:8000/companies
```

### `GET /data/{symbol}`

Returns processed stock rows for a given symbol and date window.

Supported `days`:

- `7`
- `30`
- `90`

Sample:

```bash
curl "http://127.0.0.1:8000/data/INFY?days=30"
```

### `GET /summary/{symbol}`

Returns summary metrics:

- 52-week high
- 52-week low
- average closing price
- latest close
- latest volatility

Sample:

```bash
curl http://127.0.0.1:8000/summary/TCS
```

### `GET /compare`

Compares two symbols with normalized price data and return trends.

Sample:

```bash
curl "http://127.0.0.1:8000/compare?symbol1=INFY&symbol2=RELIANCE&days=30"
```

### `GET /top-movers`

Returns the latest top gainers and losers.

Sample:

```bash
curl http://127.0.0.1:8000/top-movers
```

### `GET /predict/{symbol}`

Returns 7 future business-day predictions using linear regression.

Sample:

```bash
curl http://127.0.0.1:8000/predict/INFY
```

## Screenshots

### Dashboard View

![Dashboard View](images/Screenshot%202026-03-30%20at%202.21.19%E2%80%AFAM.png)

### Overview and Main Layout

![Overview Layout](images/Screenshot%202026-03-30%20at%202.21.27%E2%80%AFAM.png)

### Price Trend Chart

![Price Trend Chart](images/Screenshot%202026-03-30%20at%202.21.36%E2%80%AFAM.png)

### Comparison Chart

![Comparison Chart](images/Screenshot%202026-03-30%20at%202.21.43%E2%80%AFAM.png)

### Top Movers Panel

![Top Movers Panel](images/Screenshot%202026-03-30%20at%202.21.50%E2%80%AFAM.png)

### Swagger Documentation

![Swagger Docs](images/Screenshot%202026-03-30%20at%202.23.14%E2%80%AFAM.png)

### Additional App View

![Additional App View](images/Screenshot%202026-03-30%20at%202.23.16%E2%80%AFAM.png)

## Custom Metric Explanation

The chosen custom metric is **Volatility**.

Volatility is calculated as the rolling standard deviation of daily returns over a 14-day window.

Why this metric was chosen:

- it adds real analytical value beyond simple price plotting
- it helps measure short-term instability
- it is easy to explain in interviews and project reviews
- it fits naturally into both API output and dashboard storytelling

How to interpret it:

- high volatility means prices have been moving more sharply day to day
- low volatility means price action has been relatively stable

Where it appears:

- `/data/{symbol}` as `volatility_14`
- `/summary/{symbol}` as `latest_custom_metric_value`

## Caching Strategy

The app uses in-memory caching inside `DataService`.

- Cached item:
  - processed Pandas DataFrame per symbol
- TTL:
  - 10 minutes
- Why it matters:
  - reduces repeated `yfinance` calls
  - improves responsiveness
  - limits upstream dependency pressure

## Challenges Faced and Solutions

### 1. `yfinance` MultiIndex columns

Problem:

- Yahoo Finance returned MultiIndex columns such as `('Close', 'INFY.NS')`

Solution:

- flattened the columns before the processing pipeline

### 2. Python 3.14 dependency issue

Problem:

- `pydantic-core` failed to build on Python `3.14`

Solution:

- pinned the project to Python `3.13`
- updated deployment configuration accordingly

### 3. Empty or unavailable upstream data

Problem:

- `yfinance` may fail, return empty data, or be blocked in restricted environments

Solution:

- added deterministic fallback mock-data generation

### 4. Chart rendering issues

Problem:

- frontend chart date formatting caused rendering failures

Solution:

- stabilized chart label formatting and chart frame sizing

### 5. Documentation and deployment readiness

Problem:

- a technically good project can still feel incomplete if docs, deployment setup, and reviewer guidance are weak

Solution:

- improved Swagger docs
- rewrote the README
- added Docker support
- added Render deployment configuration
- verified endpoints, docs, and frontend assets through regression testing

## Design Decisions

### Why SQLite?

SQLite is ideal for this project because it is lightweight, local-first, easy to inspect, and avoids unnecessary infrastructure for an internship scope.

### Why Chart.js?

Chart.js keeps the frontend simple, browser-native, and easy to maintain, while still giving enough power for strong analytical visualizations.

### Why linear regression for prediction?

Linear regression is fast, explainable, and realistic for a lightweight forecasting feature. It is much more appropriate here than heavy models like LSTM or ARIMA.

### Why in-memory cache instead of Redis?

For a single-app portfolio project, in-memory caching gives most of the benefit with almost no infrastructure cost.

## Future Improvements

- Add WebSocket-based live market refresh
- Add user watchlists and saved views
- Integrate news sentiment APIs
- Add portfolio allocation and return simulation
- Support more exchanges and symbols
- Add authentication and multi-user support
- Add scheduled background refresh jobs

## Final Notes

This project is not just a CRUD dashboard. It demonstrates:

- data engineering
- backend architecture
- analytical thinking
- dashboard product design
- API documentation quality
- deployment preparation
- testing and regression verification
- deployment awareness

That combination makes it a strong internship submission and a solid portfolio project.
