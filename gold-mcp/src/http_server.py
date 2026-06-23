from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query

from src.config import get_settings
from src.database import GoldPriceRepository, session_scope
from src.schemas import (
    BuyOpportunityResponse,
    CaratPriceDetail,
    ErrorResponse,
    GoldHistoryEntry,
    GoldHistoryResponse,
    GoldIndicatorsResponse,
    GoldPriceResponse,
    MarketSummaryResponse,
    RecommendationAccuracyResponse,
)
from src.services.indicator_service import get_latest_indicators
from src.services.recommendation_service import analyze_buy_opportunity as _analyze
from src.tools.accuracy_tools import get_recommendation_accuracy
from src.utils.logging import get_logger

logger = get_logger(__name__)

PERIOD_DAYS: dict[str, int] = {
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "5y": 1825,
    "10y": 3650,
}

_ERR = {
    404: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}

app = FastAPI(
    title="Gold Advisor API v2",
    description=(
        "Read-only REST API for gold prices, historical trends, "
        "technical indicators, and buy recommendations.\n\n"
        "All data is served from a shared PostgreSQL database. "
        "No external API calls are made at request time."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["Meta"], summary="Health check")
def health() -> dict:
    """Returns `{"status": "ok"}` when the server is running."""
    return {"status": "ok"}


@app.get(
    "/price",
    response_model=GoldPriceResponse,
    responses=_ERR,
    tags=["Prices"],
    summary="Current gold price for one currency and carat",
)
def get_gold_price(
    currency: str = Query(
        default="AED",
        description="Currency code",
        examples={"AED": {"value": "AED"}, "USD": {"value": "USD"}, "INR": {"value": "INR"}},
    ),
    carat: str = Query(
        default="24K",
        description="Gold purity",
        examples={"24K": {"value": "24K"}, "22K": {"value": "22K"}, "18K": {"value": "18K"}},
    ),
) -> GoldPriceResponse:
    """
    Returns the latest price for the requested `currency`/`carat` pair,
    plus prices for all other carats on the same date.

    | Field        | Description                          |
    |--------------|--------------------------------------|
    | `price`      | Price per gram in requested currency |
    | `all_carats` | All 4 carats available on that date  |
    | `calculated` | `true` if derived via FX conversion  |
    """
    settings = get_settings()
    currency = (currency or settings.default_currency).upper()
    carat = (carat or settings.default_carat).upper()

    logger.info("http_get_gold_price", currency=currency, carat=carat)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        latest_date = repo.get_latest_date_for_currency(currency)
        if latest_date is None:
            raise HTTPException(status_code=404, detail=f"No data for currency {currency}")
        rows = repo.get_by_date_and_currency(latest_date, currency)

    primary = next((r for r in rows if r.carat == carat), None)
    if primary is None:
        raise HTTPException(status_code=404, detail=f"No data for {currency} {carat} on {latest_date}")

    all_carats = [CaratPriceDetail(carat=r.carat, price=r.price, calculated=r.calculated) for r in rows]
    return GoldPriceResponse(
        price=primary.price,
        currency=primary.currency,
        carat=primary.carat,
        price_type=primary.price_type,
        date=primary.date,
        source=primary.source,
        timestamp=datetime.utcnow().isoformat() + "Z",
        all_carats=all_carats,
        open=primary.open,
        high=primary.high,
        low=primary.low,
    )


@app.get(
    "/prices",
    response_model=dict,
    responses=_ERR,
    tags=["Prices"],
    summary="Latest prices for all currencies and carats",
)
def get_gold_prices() -> dict:
    """
    Returns the most recent price for every `currency × carat` combination.

    Shape: `{ "USD": { "24K": { price, calculated, source, date }, ... }, ... }`
    """
    settings = get_settings()
    logger.info("http_get_gold_prices")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        rows = repo.get_latest_per_currency_carat(settings.supported_currencies, settings.supported_carats)

    result: dict = {}
    for row in rows:
        result.setdefault(row.currency, {})[row.carat] = {
            "price": row.price,
            "calculated": row.calculated,
            "source": row.source,
            "date": row.date,
        }
    return result


@app.get(
    "/history",
    response_model=GoldHistoryResponse,
    responses=_ERR,
    tags=["Prices"],
    summary="Historical gold prices for a given period",
)
def get_gold_history(
    period: str = Query(
        default="30d",
        description="Lookback window",
        examples={
            "30d": {"value": "30d"},
            "90d": {"value": "90d"},
            "1y": {"value": "1y"},
            "5y": {"value": "5y"},
            "10y": {"value": "10y"},
        },
    ),
    currency: str = Query(
        default="USD",
        description="Currency code",
        examples={"USD": {"value": "USD"}, "AED": {"value": "AED"}, "INR": {"value": "INR"}},
    ),
    carat: str = Query(
        default="24K",
        description="Gold purity",
        examples={"24K": {"value": "24K"}, "22K": {"value": "22K"}},
    ),
) -> GoldHistoryResponse:
    """
    Returns daily OHLC-style records for the given `currency`/`carat` over `period`.

    | Period | Days  |
    |--------|-------|
    | 30d    | 30    |
    | 90d    | 90    |
    | 1y     | 365   |
    | 5y     | 1 825 |
    | 10y    | 3 650 |
    """
    currency = currency.upper()
    carat = carat.upper()
    days = PERIOD_DAYS.get(period, 30)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    logger.info("http_get_gold_history", period=period, currency=currency, carat=carat)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        rows = repo.get_range(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            currency=currency,
            carat=carat,
        )

    if not rows:
        raise HTTPException(status_code=404, detail=f"No history for {currency} {carat} in {period}")

    entries = [
        GoldHistoryEntry(
            date=r.date, price=r.price, currency=r.currency, carat=r.carat,
            price_type=r.price_type, source=r.source,
            open=r.open, high=r.high, low=r.low,
        )
        for r in rows
    ]
    return GoldHistoryResponse(
        entries=entries,
        period_days=days,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        count=len(entries),
        currency=currency,
        carat=carat,
    )


@app.get(
    "/indicators",
    response_model=GoldIndicatorsResponse,
    responses=_ERR,
    tags=["Analysis"],
    summary="Latest technical indicators (MA7 / MA30 / MA90 / RSI14)",
)
def get_gold_indicators() -> GoldIndicatorsResponse:
    """
    Returns the most recently computed indicators derived from USD 24K prices.

    | Indicator | Description                        |
    |-----------|------------------------------------|
    | `ma7`     | 7-day simple moving average        |
    | `ma30`    | 30-day simple moving average       |
    | `ma90`    | 90-day simple moving average       |
    | `rsi14`   | 14-period RSI (Wilder smoothing)   |
    | `trend`   | Bullish / Bearish / Neutral-*      |
    """
    logger.info("http_get_gold_indicators")
    indicators = get_latest_indicators()
    if indicators is None:
        raise HTTPException(status_code=404, detail="No indicator data in database")
    return indicators


@app.get(
    "/buy",
    response_model=BuyOpportunityResponse,
    responses=_ERR,
    tags=["Analysis"],
    summary="Analyze buy opportunity and return a scored recommendation",
)
def analyze_buy_opportunity(
    currency: str = Query(
        default="AED",
        description="Currency for the display price in the response",
        examples={"AED": {"value": "AED"}, "USD": {"value": "USD"}, "INR": {"value": "INR"}},
    ),
    carat: str = Query(
        default="24K",
        description="Carat for the display price in the response",
        examples={"24K": {"value": "24K"}, "22K": {"value": "22K"}},
    ),
) -> BuyOpportunityResponse:
    """
    Scores the current market conditions on a 0-100 scale using USD 24K indicators.

    | Score  | Recommendation |
    |--------|---------------|
    | 0–30   | AVOID         |
    | 31–60  | WAIT          |
    | 61–80  | BUY           |
    | 81–100 | STRONG_BUY    |

    The result is persisted to `recommendation_history`.
    """
    logger.info("http_analyze_buy_opportunity", currency=currency, carat=carat)
    try:
        return _analyze(currency=currency.upper(), carat=carat.upper())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get(
    "/summary",
    response_model=MarketSummaryResponse,
    responses=_ERR,
    tags=["Analysis"],
    summary="Full market summary (Telegram-ready markdown + structured data)",
)
def get_market_summary() -> MarketSummaryResponse:
    """
    Combines latest prices for all currencies, current indicators,
    and a buy score into a single response.

    The `text` field is formatted as Telegram-compatible markdown.
    """
    settings = get_settings()
    logger.info("http_get_market_summary")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        rows = repo.get_latest_per_currency_carat(settings.supported_currencies, settings.supported_carats)

    prices: dict[str, dict[str, CaratPriceDetail]] = {}
    latest_date = ""
    for row in rows:
        prices.setdefault(row.currency, {})[row.carat] = CaratPriceDetail(
            carat=row.carat, price=row.price, calculated=row.calculated
        )
        if row.date > latest_date:
            latest_date = row.date

    indicators = get_latest_indicators()
    trend = indicators.trend if indicators else "Unknown"
    rsi14 = indicators.rsi14 if indicators else None

    try:
        rec = _analyze(currency=settings.default_currency, carat=settings.default_carat)
        buy_score = rec.score
        recommendation = rec.recommendation
    except RuntimeError:
        buy_score = 0
        recommendation = "UNKNOWN"

    lines = [f"*Gold Market Summary* — {latest_date}", ""]
    for currency in settings.supported_currencies:
        if currency not in prices:
            continue
        lines.append(f"*{currency}*")
        for carat in settings.supported_carats:
            if carat not in prices[currency]:
                continue
            d = prices[currency][carat]
            calc_tag = " _(calc)_" if d.calculated else ""
            lines.append(f"  {carat}: {d.price:,.2f}{calc_tag}")
        lines.append("")
    lines.append(f"*Trend:* {trend}")
    if rsi14 is not None:
        lines.append(f"*RSI(14):* {rsi14:.1f}")
    lines.append(f"*Buy Score:* {buy_score}/100 → *{recommendation}*")

    return MarketSummaryResponse(
        text="\n".join(lines),
        prices={c: {k: v.model_dump() for k, v in carats.items()} for c, carats in prices.items()},
        buy_score=buy_score,
        recommendation=recommendation,
        trend=trend,
        rsi14=rsi14,
        date=latest_date,
    )


@app.get(
    "/accuracy",
    response_model=RecommendationAccuracyResponse,
    responses=_ERR,
    tags=["Analysis"],
    summary="Evaluate accuracy of past buy/avoid recommendations",
)
def accuracy(horizon_days: int = Query(default=30, ge=1, description="Days after recommendation to check outcome")) -> RecommendationAccuracyResponse:
    """
    For each past recommendation whose horizon has elapsed, looks up the actual
    gold price (USD 24K) at `horizon_days` after the recommendation date and
    determines whether it was correct.

    | Recommendation | Correct if...           |
    |----------------|-------------------------|
    | BUY / STRONG_BUY | price went up        |
    | AVOID          | price went down         |
    | WAIT           | not evaluated (no direction) |

    Returns per-type hit rates, average return for BUY signals, and full entry list.
    """
    logger.info("http_get_recommendation_accuracy", horizon_days=horizon_days)
    return get_recommendation_accuracy(horizon_days=horizon_days)
