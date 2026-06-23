# gold-mcp-v2

Read-only MCP server for gold price data, historical trends, technical indicators, and buy recommendations. Reads exclusively from a shared PostgreSQL database — no external API calls at request time.

## Tools

| Tool | Params | Description |
|------|--------|-------------|
| `get_gold_price` | `currency="AED"`, `carat="24K"` | Current price for one currency/carat + all carats on same date |
| `get_gold_prices` | — | Latest prices for all currencies × carats |
| `get_gold_history` | `period="30d"`, `currency="USD"`, `carat="24K"` | Historical OHLC prices (`30d` / `90d` / `1y` / `5y` / `10y`) |
| `get_gold_indicators` | — | MA7 / MA30 / MA90 / RSI14 + trend direction |
| `analyze_buy_opportunity` | `currency="AED"`, `carat="24K"` | Score (0–100) + recommendation + saves to DB |
| `get_market_summary` | — | Full summary as Telegram markdown + structured data |
| `get_recommendation_accuracy` | `horizon_days=30` | Hit-rate and return analysis of past recommendations |

## Installation

```bash
cd gold-mcp-v2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env to set DATABASE_URL
```

## Running locally

```bash
# MCP stdio (for Claude Desktop / agent clients)
python -m src.main

# HTTP only — Swagger at http://localhost:8080/docs
python -m src.main --http

# Both simultaneously
python -m src.main --all
```

## Running with Docker

```bash
# Start PostgreSQL + MCP server
docker compose up

# Include HTTP server
docker compose --profile http up
```

The `gold-mcp-v2` container waits for the `postgres` healthcheck before starting. `create_all()` runs at startup so the schema is created automatically.

## MCP client integration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "gold-advisor-v2": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/gold-mcp-v2",
      "env": {
        "DATABASE_URL": "postgresql://gold_admin:gold_admin_password@localhost:5432/gold_db"
      }
    }
  }
}
```

### Hermes / generic stdio client

```json
{
  "command": "python",
  "args": ["-m", "src.main"],
  "cwd": "/path/to/gold-mcp-v2"
}
```

## Configuration

All settings are read from environment variables (or `.env`):

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql://gold_admin:gold_admin_password@localhost:5432/gold_db` |
| `DEFAULT_CURRENCY` | `AED` |
| `DEFAULT_CARAT` | `24K` |
| `SCORING_PRICE_BELOW_MA30` | `40` |
| `SCORING_PRICE_BELOW_MA90` | `20` |
| `SCORING_RSI_BELOW_35` | `20` |
| `SCORING_MA7_ABOVE_MA30` | `20` |

## Running tests

```bash
pytest
```

Tests use an in-memory SQLite database and monkeypatching — no live PostgreSQL needed.

## Scoring logic

| Condition | Points |
|-----------|--------|
| USD 24K price < MA30 | +40 |
| USD 24K price < MA90 | +20 |
| RSI(14) < 35 | +20 |
| MA7 > MA30 | +20 |

| Score | Recommendation |
|-------|---------------|
| 0–30 | AVOID |
| 31–60 | WAIT |
| 61–80 | BUY |
| 81–100 | STRONG_BUY |

## Recommendation accuracy

`get_recommendation_accuracy(horizon_days=30)` (also `GET /accuracy?horizon_days=30`) evaluates past recommendations by joining `recommendation_history` with `gold_prices` at `horizon_days` after each recommendation date:

| Recommendation | Counted as correct if… |
|----------------|------------------------|
| BUY / STRONG_BUY | USD 24K price was **higher** at the horizon date |
| AVOID | USD 24K price was **lower** at the horizon date |
| WAIT | Not evaluated — no directional claim |

Returns overall hit rate, average return for BUY/STRONG_BUY signals, per-label breakdown, and a full per-recommendation entry list. Only recommendations where `date ≤ today − horizon_days` are evaluated; newer ones are counted in `pending_count`.

## Troubleshooting

**`No data found for currency AED`** — The database has no rows in `gold_prices`. Run the data collector from the gold-mcp project first, pointing it at the same PostgreSQL instance.

**`No indicator data in database`** — Run `scripts/refresh_history.py` from the gold-mcp project to compute and store indicators.

**MCP client sees no output** — All logs go to `stderr` and `data/gold-advisor-v2.log`. Nothing is written to `stdout` (MCP transport channel).
