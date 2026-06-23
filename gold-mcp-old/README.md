# Gold Advisor MCP Server

Gold price intelligence and buy-opportunity analysis for AI agents.

Provides real-time gold prices in multiple currencies and purities, historical data, technical indicators (MA7, MA30, MA90, RSI), and a scored buy recommendation — all via MCP tools compatible with Claude Desktop, Cursor, OpenAI Agents, and any generic MCP client.

A FastAPI HTTP server runs alongside MCP for debugging and HTTP-based integrations, with full Swagger UI at `/docs`.

---

## Features

- **Multi-currency prices** — USD, AED, INR with local market providers
- **Multi-carat support** — 24K, 22K, 21K, 18K (provider-supplied where available, purity-ratio derived otherwise)
- **AED local providers** — iGold scraper → Dubai City of Gold API → USD conversion fallback
- **INR local provider** — Metals.dev native INR prices → USD conversion fallback
- **USD providers** — FreeGoldAPI → Metals.dev → GoldAPI → Yahoo Finance (automatic fallback)
- **Historical data** — 30d / 90d / 1y / 5y / 10y
- **Technical indicators** — MA7, MA30, MA90, RSI(14), always on USD 24K
- **Buy score 0–100** — AVOID / WAIT / BUY / STRONG\_BUY
- **Telegram-ready summary** across all currencies
- **HTTP REST server** with Swagger UI (`/docs`) and ReDoc (`/redoc`)
- SQLite persistence with UPSERT deduplication
- Docker + Docker Compose support

---

## Installation

```bash
cd gold-mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in any API keys you have:

```bash
cp .env.example .env
```

API keys are **optional** — providers without keys are skipped automatically. Yahoo Finance (no key required) is always available for historical data.

`config.yaml` controls provider order, default currency/carat, scoring weights, and the HTTP server port:

```yaml
default_currency: AED
default_carat: 24K

currencies:
  USD: { enabled: true }
  AED: { enabled: true }
  INR: { enabled: true }

carats: [24K, 22K, 21K, 18K]

http:
  host: "0.0.0.0"
  port: 8080
```

---

## Database Migration

If you have an existing v1 database (single `price_usd` column), run the migration once before starting:

```bash
python scripts/migrate_db.py
```

This is idempotent — safe to run on a fresh database too.

---

## Initial Data Load

Backfill historical data to enable indicator calculation:

```bash
# Last year of data (recommended for a quick start)
python scripts/backfill_history.py --days 365

# 5 years
python scripts/backfill_history.py --days 1825

# 10 years / full
python scripts/backfill_history.py --full

# Specific currency only
python scripts/backfill_history.py --days 365 --currency USD
```

---

## Running Locally

```bash
# MCP over stdio (default — for Claude Desktop / Cursor)
python -m src.main

# HTTP REST server only (port 8080)
python -m src.main --http

# Both simultaneously — MCP stdio + HTTP server
python -m src.main --all
```

Open `http://localhost:8080/docs` for the interactive Swagger UI.

---

## Running with Docker

```bash
# MCP server
docker compose up -d

# HTTP server (port 8080)
docker compose --profile http up -d gold-http

# Run migration (one-time)
docker compose --profile tools run --rm migrate

# Run initial backfill (one-time)
docker compose --profile tools run --rm backfill
```

---

## HTTP API

Base URL: `http://localhost:8080`

Interactive docs: `http://localhost:8080/docs` (Swagger UI) · `http://localhost:8080/redoc` (ReDoc)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health and version |
| GET | `/price` | Current price (`currency`, `carat` query params) |
| GET | `/prices` | All currencies × carats in one call |
| GET | `/history` | Historical prices (`period`, `currency`, `carat`) |
| GET | `/indicators` | MA7, MA30, MA90, RSI — always USD 24K |
| GET | `/analysis` | Scored buy recommendation (`currency`, `carat`) |
| GET | `/summary` | Multi-currency Telegram summary |

### Quick examples

```bash
# AED 22K spot price (iGold provider)
curl http://localhost:8080/price?currency=AED&carat=22K

# All currencies and carats
curl http://localhost:8080/prices

# USD 24K buy analysis
curl http://localhost:8080/analysis?currency=USD

# Last 90 days of USD prices
curl http://localhost:8080/history?period=90d&currency=USD&carat=24K

# Full market summary
curl http://localhost:8080/summary
```

---

## Scheduled Refresh (optional)

```cron
# Collect current price every 15 minutes
*/15 * * * * cd /path/to/gold-mcp && .venv/bin/python scripts/collect_current_price.py

# Refresh last 90 days and recompute indicators daily at midnight
0 0 * * * cd /path/to/gold-mcp && .venv/bin/python scripts/refresh_history.py --days 90
```

---

## MCP Client Configuration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "gold-advisor": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/absolute/path/to/gold-mcp",
      "env": {
        "FREEGOLDAPI_KEY": "your_key_here"
      }
    }
  }
}
```

### Cursor / Windsurf (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "gold-advisor": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/absolute/path/to/gold-mcp"
    }
  }
}
```

### OpenAI Agents SDK

```python
from agents.mcp import MCPServerStdio

gold_server = MCPServerStdio(
    params={
        "command": "python",
        "args": ["-m", "src.main"],
        "cwd": "/absolute/path/to/gold-mcp",
    }
)
```

---

## MCP Tools

### `get_gold_price`

Fetch the current gold spot price. Defaults to `default_currency` / `default_carat` from config.

All prices are in **per gram** regardless of currency or provider.

```json
{
  "price": 509.30,
  "currency": "AED",
  "carat": "24K",
  "price_type": "local",
  "unit": "gram",
  "date": "2025-06-19",
  "source": "igold",
  "timestamp": "2025-06-19T10:00:00Z",
  "all_carats": [
    {"carat": "24K", "price": 509.30, "calculated": false},
    {"carat": "22K", "price": 471.54, "calculated": false},
    {"carat": "21K", "price": 450.09, "calculated": false},
    {"carat": "18K", "price": 385.79, "calculated": false}
  ]
}
```

### `get_gold_prices`

Fetch current prices for all enabled currencies and carats.

```json
{
  "AED": {
    "24K": {"carat": "24K", "price": 509.30, "calculated": false},
    "22K": {"carat": "22K", "price": 471.54, "calculated": false}
  },
  "USD": {
    "24K": {"carat": "24K", "price": 3325.00, "calculated": false}
  },
  "INR": {
    "24K": {"carat": "24K", "price": 278340.00, "calculated": false}
  }
}
```

### `get_gold_history`

Fetch historical prices. `period` accepts: `30d`, `90d`, `1y`, `5y`, `10y`.

```json
{
  "entries": [{"date": "2025-06-01", "price": 505.20, "currency": "AED", "carat": "24K", "price_type": "local", "source": "igold"}],
  "period_days": 90,
  "start_date": "2025-03-21",
  "end_date": "2025-06-19",
  "count": 64,
  "currency": "AED",
  "carat": "24K"
}
```

### `get_gold_indicators`

Latest MA7, MA30, MA90, RSI(14), and trend. Always computed on USD 24K.

```json
{
  "date": "2025-06-19",
  "price_usd": 3325.0,
  "ma7": 3300.0,
  "ma30": 3350.0,
  "ma90": 3400.0,
  "rsi14": 31.0,
  "trend": "Bullish"
}
```

### `analyze_buy_opportunity`

Score-based buy analysis. Score computed on USD 24K; display price in requested currency/carat.

```json
{
  "date": "2025-06-19",
  "price": 509.30,
  "currency": "AED",
  "carat": "24K",
  "price_usd": 3325.0,
  "score": 78,
  "recommendation": "BUY",
  "reasoning": [
    "Price $3325.00 is below MA30 $3350.00 (+40 pts)",
    "RSI(14) 31.0 is below 35 (oversold) (+20 pts)"
  ],
  "score_breakdown": {"price_below_ma30": 40, "price_below_ma90": 0, "rsi_below_35": 20, "ma7_above_ma30": 0, "total": 60},
  "confidence": 0.6
}
```

### `get_market_summary`

Telegram-optimised multi-currency snapshot.

```json
{
  "text": "Gold — 2025-06-19\n\nAED (iGold)\n  24K 509.30  22K 471.54  21K 450.09  18K 385.79\nUSD (freegoldapi)\n  24K 3325.00\nINR (metalsdev_inr)\n  24K 278340.00\n\nBuy Score: 78/100 — BUY\nTrend: Bullish  RSI: 31.0",
  "prices": {"AED": {"24K": {"carat": "24K", "price": 509.30, "calculated": false}}},
  "buy_score": 78,
  "recommendation": "BUY",
  "trend": "Bullish",
  "rsi14": 31.0,
  "date": "2025-06-19"
}
```

---

## Buy Score Rules

| Condition | Points |
|-----------|--------|
| Price < MA30 | +40 |
| Price < MA90 | +20 |
| RSI(14) < 35 | +20 |
| MA7 > MA30 | +20 |

| Score | Recommendation |
|-------|---------------|
| 0–30  | AVOID |
| 31–60 | WAIT |
| 61–80 | BUY |
| 81–100 | STRONG\_BUY |

---

## Running Tests

```bash
# Unit tests only (fast, no network)
pytest tests/ -v

# Include live integration tests (hits real APIs — iGold, DCOG, FX rates)
pytest tests/ -v --run-live

# Live tests only
pytest tests/test_live.py --run-live -v

# Via environment variable
PYTEST_LIVE=1 pytest tests/ -v
```

---

## Project Structure

```
gold-mcp/
├── src/
│   ├── main.py              # Entry point — MCP stdio + optional HTTP server
│   ├── config.py            # Pydantic settings + YAML config loader
│   ├── database.py          # SQLAlchemy session + repositories
│   ├── models.py            # ORM models (gold_prices, gold_indicators)
│   ├── schemas.py           # Pydantic response schemas
│   ├── http_server.py       # FastAPI REST server (Swagger at /docs)
│   ├── providers/
│   │   ├── base.py          # PriceResult, CaratPrice, derive_carat_prices()
│   │   ├── manager.py       # Currency-aware provider routing + fallback
│   │   ├── fx_rates.py      # FX rate provider (exchangerate-api → yfinance)
│   │   ├── freegoldapi.py
│   │   ├── metalsdev.py     # Supports USD and INR
│   │   ├── goldapi.py
│   │   ├── yahoofinance.py
│   │   └── currency/
│   │       ├── igold.py           # AED — iGold HTML scraper
│   │       └── dubaicityofgold.py # AED — Dubai City of Gold API
│   ├── services/
│   │   ├── gold_service.py         # get_current_price, get_history, get_all_current_prices
│   │   ├── indicator_service.py    # MA + RSI computation (USD 24K)
│   │   └── recommendation_service.py  # Buy score analysis
│   ├── tools/               # Thin MCP tool wrappers
│   │   ├── price_tools.py
│   │   ├── prices_tools.py  # get_gold_prices (all currencies)
│   │   ├── history_tools.py
│   │   ├── analysis_tools.py
│   │   └── summary_tools.py
│   └── utils/               # Structured logging
├── scripts/
│   ├── migrate_db.py            # v1 → v2 schema migration (idempotent)
│   ├── backfill_history.py      # One-time historical load
│   ├── refresh_history.py       # Incremental daily refresh
│   └── collect_current_price.py # Current price collector (all currencies)
├── tests/
├── data/                    # SQLite database (auto-created)
├── config.yaml
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Troubleshooting

**No indicator data available**
Run `python scripts/backfill_history.py --days 365` then `python scripts/refresh_history.py`.

**iGold / Dubai City of Gold returning no data**
These are scraper-based; the site structure may have changed. The server falls back to USD conversion automatically.

**All providers failed**
Yahoo Finance requires no API key and works by default. If it fails, check your network connection. Add API keys in `.env` to enable additional providers.

**SQLite locked**
Only one process should write to the database at a time. Stop the server before running backfill scripts, or use the `data/gold.db` path on a filesystem that supports concurrent access.

**IDE shows "Cannot find module" for fastapi / uvicorn / sqlalchemy**
The IDE may be using the system Python rather than your virtualenv. The code runs correctly in the activated environment (`source .venv/bin/activate` or `pyenv activate mcp`).
