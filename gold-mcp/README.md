# Gold Advisor MCP Server

Gold price intelligence and buy-opportunity analysis for AI agents.

Provides real-time gold prices, historical data, technical indicators (MA7, MA30, MA90, RSI), and a scored buy recommendation — all via MCP tools compatible with Claude Desktop, Cursor, OpenAI Agents, Hermes Agent, and any generic MCP client.

---

## Features

- **Live price** from FreeGoldAPI → Metals.dev → Yahoo Finance → GoldAPI (automatic fallback)
- **Historical data** for 30d / 90d / 1y / 5y / 10y
- **Technical indicators**: MA7, MA30, MA90, RSI(14)
- **Buy score 0–100** with AVOID / WAIT / BUY / STRONG\_BUY recommendation
- **Telegram-ready summary** tool
- SQLite persistence with UPSERT deduplication
- Structured JSON responses for all tools
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

Edit `config.yaml` to change provider order, scoring weights, or database path.

---

## Initial Data Load

Before starting the server, backfill historical data to enable indicator calculation:

```bash
# Last year of data (recommended for a quick start)
python scripts/backfill_history.py --days 365

# 5 years
python scripts/backfill_history.py --days 1825

# 10 years
python scripts/backfill_history.py --days 3650

# Full 10 years (alias)
python scripts/backfill_history.py --full
```

---

## Running Locally

```bash
python -m src.main
```

The server runs over stdio (standard MCP transport).

---

## Running with Docker

```bash
# Build and start the MCP server
docker compose up -d

# Run initial backfill (one-time)
docker compose --profile tools run --rm backfill
```

---

## Scheduled Refresh (optional)

Add a cron entry to keep prices and indicators current:

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

### `tool_get_gold_price`

Fetch the current gold spot price.

```json
{
  "price_usd": 3325.0,
  "currency": "USD",
  "unit": "troy_oz",
  "date": "2024-06-17",
  "source": "freegoldapi",
  "timestamp": "2024-06-17T10:00:00Z"
}
```

### `tool_get_gold_history`

Fetch historical prices. `period` accepts: `30d`, `90d`, `1y`, `5y`, `10y`.

```json
{
  "entries": [{"date": "2024-06-01", "price_usd": 3280.0, "source": "yahoofinance"}],
  "period_days": 90,
  "start_date": "2024-03-18",
  "end_date": "2024-06-17",
  "count": 64
}
```

### `tool_get_gold_indicators`

Return the latest MA7, MA30, MA90, RSI(14), and trend.

```json
{
  "date": "2024-06-17",
  "price_usd": 3325.0,
  "ma7": 3300.0,
  "ma30": 3350.0,
  "ma90": 3400.0,
  "rsi14": 31.0,
  "trend": "Bullish"
}
```

### `tool_analyze_buy_opportunity`

Score-based buy analysis with full reasoning.

```json
{
  "date": "2024-06-17",
  "price_usd": 3325.0,
  "score": 78,
  "recommendation": "BUY",
  "reasoning": [
    "Price $3325.00 is below MA30 $3350.00 (+40 pts)",
    "RSI(14) 31.0 is below 35 (oversold) (+20 pts)"
  ],
  "score_breakdown": {
    "price_below_ma30": 40,
    "price_below_ma90": 0,
    "rsi_below_35": 20,
    "ma7_above_ma30": 0,
    "total": 60
  },
  "confidence": 0.6
}
```

### `tool_get_market_summary`

Telegram-optimised one-shot summary.

```json
{
  "text": "Gold Price: $3,325\nTrend: Bullish\nRSI: 31\nBuy Score: 78/100\nRecommendation: BUY",
  "price_usd": 3325.0,
  "trend": "Bullish",
  "rsi14": 31.0,
  "buy_score": 78,
  "recommendation": "BUY",
  "date": "2024-06-17"
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
pytest tests/ -v
```

---

## Project Structure

```
gold-mcp/
├── src/
│   ├── main.py              # FastMCP server entry point
│   ├── config.py            # Pydantic settings + YAML config loader
│   ├── database.py          # SQLAlchemy session + repositories
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic response schemas
│   ├── providers/           # Data provider abstraction + fallback manager
│   ├── services/            # Business logic (gold, indicators, recommendations)
│   ├── tools/               # Thin MCP tool wrappers
│   └── utils/               # Structured logging
├── scripts/
│   ├── backfill_history.py  # One-time historical load
│   ├── refresh_history.py   # Incremental daily refresh
│   └── collect_current_price.py  # Current price collector
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
Run `python scripts/backfill_history.py --days 365` before starting the server.

**All providers failed**
Yahoo Finance requires no API key and works by default. If it fails, check your network connection. Add API keys in `.env` to enable additional providers.

**SQLite locked**
Only one process should write to the database at a time. Stop the server before running backfill scripts, or use the `data/gold.db` path on a filesystem that supports concurrent access.
