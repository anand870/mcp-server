You are implementing a new Python project called gold-mcp-v2. This is a read-only MCP (Model Context Protocol) server that exposes gold price data, historical trends, technical indicators, and buy recommendations via MCP tools. It reads exclusively from a shared PostgreSQL database — it never fetches data from external APIs or providers.

gold-mcp-v2 owns the database schema: it defines the ORM models and runs create_all() at startup.

## What gold-mcp-v2 is NOT

- Not a data collector — no HTTP requests to gold price APIs, no web scraping
- Not a scheduler — no cron, no periodic tasks
- Not the existing gold-mcp project — this is a new project from scratch

## Project Location

Create a new project at `/Users/rohitanand/workspace/personal/gold-mcp-v2/`

## Reference: Existing gold-mcp (read for context, do not copy wholesale)

The existing project at `/Users/rohitanand/workspace/personal/mcp-server/gold-mcp/` has:
- `src/models.py` — ORM models to replicate (same schema)
- `src/database.py` — repository pattern to adapt for PostgreSQL
- `src/services/recommendation_service.py` — scoring and recommendation logic to port
- `src/services/indicator_service.py` — MA/RSI computation to port
- `src/schemas.py` — Pydantic response schemas to reuse as-is
- `src/main.py` — MCP tool definitions and wiring to adapt

Use these as reference implementations. Modernize where sensible (e.g., use asyncpg or psycopg2, clean up SQLite-specific code).

## Database

PostgreSQL running on the host machine. Connection URL from env var `DATABASE_URL`.

Default: `postgresql://gold_admin:gold_admin_password@localhost:5432/gold_db`

Use `gold_admin` credentials (schema owner) so that `create_all()` has DDL rights.

## Project Structure

```
gold-mcp-v2/
  src/
    main.py           # MCP server entry point, tool registration
    database.py       # PostgreSQL engine, session factory, repositories
    models.py         # SQLAlchemy ORM (same schema as defined below)
    schemas.py        # Pydantic response models
    config.py         # Settings (DATABASE_URL, supported currencies/carats)
    services/
      indicator_service.py      # MA7/MA30/MA90/RSI14 (reads from DB only)
      recommendation_service.py # Buy scoring logic (reads indicators from DB)
  pyproject.toml      # or requirements.txt
  .env                # DATABASE_URL and other secrets
  Dockerfile          # Optional
```

## Database Schema (gold-mcp-v2 owns this — define in models.py and create at startup)

```python
class GoldPrice(Base):
    __tablename__ = "gold_prices"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    date       = Column(String(10), nullable=False)        # YYYY-MM-DD
    currency   = Column(String(10), nullable=False)        # USD, AED, INR
    carat      = Column(String(5),  nullable=False)        # 24K, 22K, 21K, 18K
    price      = Column(Float,      nullable=False)        # per gram
    open       = Column(Float,      nullable=True)
    high       = Column(Float,      nullable=True)
    low        = Column(Float,      nullable=True)
    source     = Column(String(50), nullable=False)
    price_type = Column(String(20), nullable=False)        # 'local' or 'converted'
    calculated = Column(Boolean,    nullable=False, default=False)
    created_at = Column(DateTime,   server_default=func.now())
    updated_at = Column(DateTime,   server_default=func.now())
    __table_args__ = (
        UniqueConstraint("date", "currency", "carat", name="uq_gold_prices_date_currency_carat"),
        Index("ix_gold_prices_date", "date"),
        Index("ix_gold_prices_currency_carat", "currency", "carat"),
    )

class GoldIndicator(Base):
    __tablename__ = "gold_indicators"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    date       = Column(String(10), nullable=False)
    ma7        = Column(Float, nullable=True)
    ma30       = Column(Float, nullable=True)
    ma90       = Column(Float, nullable=True)
    rsi14      = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("date", name="uq_gold_indicators_date"),
        Index("ix_gold_indicators_date", "date"),
    )

class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    date           = Column(String(10), nullable=False)
    price_usd      = Column(Float,   nullable=False)
    score          = Column(Integer, nullable=False)
    recommendation = Column(String(20), nullable=False)
    reasoning      = Column(Text, nullable=False)
    score_breakdown= Column(Text, nullable=False)   # JSON string
    created_at     = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_recommendation_history_date", "date"),)
```

In `database.py`, run `Base.metadata.create_all(engine)` at startup (idempotent).
Engine: `create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)`

## MCP Tools to Implement (src/main.py)

Use the `fastmcp` or `mcp` library. Register 6 tools:

### 1. `get_gold_price`
Params: `currency: str = "AED"`, `carat: str = "24K"`
- Query latest date in gold_prices for the given currency
- Return all 4 carats for that date + metadata (source, price_type, calculated, date)
- Response schema: GoldPriceResponse (see existing schemas.py for reference)

### 2. `get_gold_prices`
No params.
- Return latest price for all currencies × all carats
- Nested dict: `{currency: {carat: {price, calculated, source, date}}}`

### 3. `get_gold_history`
Params: `period: str = "30d"` (options: 30d, 90d, 1y, 5y, 10y), `currency: str = "USD"`, `carat: str = "24K"`
- Map period to days: 30d=30, 90d=90, 1y=365, 5y=1825, 10y=3650
- Query gold_prices for the date range, order by date DESC
- Response: GoldHistoryResponse with list of {date, price, open, high, low, source}

### 4. `get_gold_indicators`
No params.
- Query latest row from gold_indicators
- Return ma7, ma30, ma90, rsi14, date
- Also derive trend:
  - Bullish: latest USD 24K price > ma7 > ma30
  - Bearish: latest USD 24K price < ma7 < ma30
  - Neutral-Bullish: price > ma30
  - Neutral-Bearish: price < ma30

### 5. `analyze_buy_opportunity`
Params: `currency: str = "AED"`, `carat: str = "24K"`
- Load latest indicators from gold_indicators
- Load latest USD 24K price from gold_prices
- Compute score (0-100) using these rules (configurable in config.py):
  - +40 if price < ma30
  - +20 if price < ma90
  - +20 if rsi14 < 35
  - +20 if ma7 > ma30
- Map score → recommendation: ≤30 AVOID, 31-60 WAIT, 61-80 BUY, 81-100 STRONG_BUY
- Save to recommendation_history table
- Return score, recommendation, reasoning (list of applied rules), score_breakdown (dict), confidence (score/100)

### 6. `get_market_summary`
No params.
- Combines latest prices for all currencies + current indicators + buy score
- Format as Telegram-ready text summary (markdown)
- Also return structured data dict

## What NOT to include

- No provider classes (FreeGoldAPI, iGold, Khaleejtimes, Yahoo Finance, etc.)
- No FX rate fetching
- No HTTP requests to external APIs
- No web scraping (BeautifulSoup, requests for gold sites)
- No scheduler, cron, or background tasks
- No `collect_current_price.py` or `refresh_history.py` scripts

## Configuration (src/config.py)

```python
class Settings(BaseSettings):
    database_url: str = "postgresql://gold_admin:gold_admin_password@localhost:5432/gold_db"
    default_currency: str = "AED"
    default_carat: str = "24K"
    supported_currencies: list[str] = ["USD", "AED", "INR"]
    supported_carats: list[str] = ["24K", "22K", "21K", "18K"]
    scoring_price_below_ma30: int = 40
    scoring_price_below_ma90: int = 20
    scoring_rsi_below_35: int = 20
    scoring_ma7_above_ma30: int = 20
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```