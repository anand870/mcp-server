You are a senior Python architect.

Generate the project incrementally file-by-file.

For each file:
1. Show the path.
2. Show the complete file contents.
3. Ensure imports are correct.
4. Ensure the project runs without modification.

Do not summarize.
Do not skip files.
Do not use placeholders.


Use the MCP Server Generator skill.

Create a Gold Advisor MCP Server with gold-mcp as root folder.

Purpose:
Provide gold price intelligence and buy-opportunity analysis for AI agents such as Hermes Agent, Claude Desktop, OpenAI Agents, Cursor, and generic MCP clients.

Requirements:

## Data Providers

Implement provider abstraction with configurable provider selection.

Supported providers:

1. FreeGoldAPI (default)
2. Yahoo Finance (GC=F)
3. Metals.dev
4. GoldAPI

Provider selection must be configurable through config.yaml.

Implement automatic retry and fallback between providers.

Preferred order:

Current Price:

1. FreeGoldAPI
2. Metals.dev
3. Yahoo Finance
4. GoldAPI

Historical Data:

1. Yahoo Finance
2. FreeGoldAPI
3. Metals.dev
4. GoldAPI

## Storage

Use SQLite by default.

Persist:

* historical gold prices
* calculated indicators
* recommendation history

Support UPSERT operations and duplicate prevention.

## Historical Data

Support:

* 30 days
* 90 days
* 1 year
* 5 years
* 10 years

Generate scripts:

* backfill_history.py
* refresh_history.py
* collect_current_price.py

Backfill script should support:

```bash
python scripts/backfill_history.py --days 365
python scripts/backfill_history.py --days 1825
python scripts/backfill_history.py --days 3650
python scripts/backfill_history.py --full
```

## Indicators

Calculate:

* MA7
* MA30
* MA90
* RSI(14)

Store indicators in SQLite after refresh.

## Buy Score

Generate a score from 0-100.

Rules:

* Price below MA30 = +40
* Price below MA90 = +20
* RSI below 35 = +20
* MA7 above MA30 = +20

Recommendation mapping:

* 0-30 = AVOID
* 31-60 = WAIT
* 61-80 = BUY
* 81-100 = STRONG_BUY

Include reasoning and score breakdown.

## MCP Tools

Generate:

* get_gold_price
* get_gold_history
* get_gold_indicators
* analyze_buy_opportunity
* get_market_summary

All tools should return structured JSON suitable for AI agents.

## Telegram Optimization

The get_market_summary tool should return a concise summary suitable for Telegram chat.

Example:

Gold Price: $3325

Trend: Bullish

RSI: 31

Buy Score: 78/100

Recommendation: BUY

## Production Requirements

Generate:

* complete source code
* tests
* Dockerfile
* docker-compose.yml
* README
* configuration files
* database schema
* MCP configuration examples

Do not use TODOs or placeholder implementations.

Generate every file completely.
