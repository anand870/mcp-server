from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from src.config import get_config
from src.schemas import (
    BuyOpportunityResponse,
    ErrorResponse,
    GoldHistoryResponse,
    GoldIndicatorsResponse,
    GoldPriceResponse,
    MarketSummaryResponse,
)
from src.services.gold_service import GoldService
from src.services.indicator_service import IndicatorService
from src.services.recommendation_service import RecommendationService
from src.utils.logging import get_logger

logger = get_logger(__name__)

config = get_config()

_DESCRIPTION = """
Gold price intelligence and buy-opportunity analysis — REST API.

## Prices
Fetch real-time gold prices in **USD**, **AED**, or **INR** for any purity (24K, 22K, 21K, 18K).
Local market providers are used where available (iGold / Dubai City of Gold for AED;
Metals.dev for INR); USD conversion is the fallback.

## Analysis
Technical indicators (MA7, MA30, MA90, RSI) and a scored buy recommendation
are always computed on **USD 24K** data for consistency. The requested
currency/carat price is displayed alongside the score.

## History
Prices are persisted in SQLite. Run `scripts/backfill_history.py` to seed
historical data before using the `/history` and `/indicators` endpoints.
"""

app = FastAPI(
    title="Gold Advisor API",
    version=config.server.version,
    description=_DESCRIPTION,
    contact={"name": "Gold Advisor", "url": "https://github.com/"},
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "prices", "description": "Real-time gold price data"},
        {"name": "history", "description": "Historical price records"},
        {"name": "analysis", "description": "Technical indicators and buy recommendations"},
        {"name": "meta", "description": "Health and server information"},
    ],
)


def _err(msg: str, status: int = 500) -> JSONResponse:
    return JSONResponse(
        ErrorResponse(error=msg).model_dump(),
        status_code=status,
    )


@app.get(
    "/health",
    tags=["meta"],
    summary="Server health check",
    response_description="Service status and version",
)
async def health():
    """Returns `ok` when the server is running."""
    return {"status": "ok", "version": config.server.version, "source": "gold-advisor"}


@app.get(
    "/price",
    tags=["prices"],
    summary="Current gold price",
    response_model=GoldPriceResponse,
    responses={500: {"model": ErrorResponse}},
    response_description="Spot price for the requested currency and carat",
)
async def price(
    currency: str | None = Query(
        default=None,
        description=f"Target currency. Defaults to `{config.default_currency}`. Supported: USD, AED, INR.",
        examples={"AED": {"value": "AED"}, "USD": {"value": "USD"}, "INR": {"value": "INR"}},
    ),
    carat: str | None = Query(
        default=None,
        description=f"Gold purity. Defaults to `{config.default_carat}`. Supported: 24K, 22K, 21K, 18K.",
        examples={"24K": {"value": "24K"}, "22K": {"value": "22K"}},
    ),
):
    """
    Fetch the current gold spot price.

    - **currency**: USD (freegoldapi / metalsdev), AED (iGold / Dubai City of Gold), INR (Metals.dev)
    - **carat**: 24K is always provider-supplied; lower carats may be derived via purity ratios
    - **price_type**: `local` (native provider) or `converted` (FX-derived from USD)
    - **all_carats**: prices for all purities returned in a single call
    """
    try:
        result = await GoldService().get_current_price(currency=currency, carat=carat)
        return result
    except Exception as exc:
        logger.error("http_error", endpoint="/price", error=str(exc))
        return _err(str(exc))


@app.get(
    "/prices",
    tags=["prices"],
    summary="All currencies and carats",
    response_description="Nested map of currency → carat → price detail",
    responses={500: {"model": ErrorResponse}},
)
async def prices():
    """
    Fetch current prices for **all** enabled currencies and carats in one call.

    Returns a nested object: `{ "AED": { "24K": {...}, "22K": {...} }, "USD": { ... } }`.
    """
    try:
        result = await GoldService().get_all_current_prices()
        return {
            currency: {carat: detail.model_dump() for carat, detail in carats.items()}
            for currency, carats in result.items()
        }
    except Exception as exc:
        logger.error("http_error", endpoint="/prices", error=str(exc))
        return _err(str(exc))


@app.get(
    "/history",
    tags=["history"],
    summary="Historical gold prices",
    response_model=GoldHistoryResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    response_description="Daily price records for the requested period",
)
async def history(
    period: str = Query(
        default="90d",
        description="Lookback window. One of: `30d`, `90d`, `1y`, `5y`, `10y`.",
        examples={
            "90d": {"value": "90d"},
            "1y": {"value": "1y"},
            "5y": {"value": "5y"},
        },
    ),
    currency: str | None = Query(
        default=None,
        description=f"Currency filter. Defaults to `{config.default_currency}`.",
    ),
    carat: str | None = Query(
        default=None,
        description=f"Carat filter. Defaults to `{config.default_carat}`.",
    ),
):
    """
    Return daily closing prices from the local SQLite database.

    Seed data first with `python scripts/backfill_history.py --days 365`.
    """
    from src.tools.history_tools import VALID_PERIODS

    days = VALID_PERIODS.get(period)
    if days is None:
        return _err(f"Invalid period '{period}'. Valid: {list(VALID_PERIODS.keys())}", status=400)
    try:
        result = await GoldService().get_history(days, currency=currency, carat=carat)
        return result
    except Exception as exc:
        logger.error("http_error", endpoint="/history", error=str(exc))
        return _err(str(exc))


@app.get(
    "/indicators",
    tags=["analysis"],
    summary="Technical indicators",
    response_model=GoldIndicatorsResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    response_description="MA7, MA30, MA90, RSI(14), and trend — always USD 24K",
)
async def indicators():
    """
    Return the latest computed technical indicators.

    Indicators are always computed on **USD 24K** data regardless of your
    `default_currency` config. Run `python scripts/refresh_history.py` to
    recompute after loading new price data.
    """
    try:
        result = IndicatorService().get_latest_indicators()
        if result is None:
            return _err("No indicator data. Run scripts/refresh_history.py first.", status=404)
        return result
    except Exception as exc:
        logger.error("http_error", endpoint="/indicators", error=str(exc))
        return _err(str(exc))


@app.get(
    "/analysis",
    tags=["analysis"],
    summary="Buy opportunity analysis",
    response_model=BuyOpportunityResponse,
    responses={500: {"model": ErrorResponse}},
    response_description="Scored buy recommendation with full reasoning",
)
async def analysis(
    currency: str | None = Query(
        default=None,
        description=f"Display currency. Defaults to `{config.default_currency}`. Score is always USD 24K based.",
    ),
    carat: str | None = Query(
        default=None,
        description=f"Display carat. Defaults to `{config.default_carat}`.",
    ),
):
    """
    Score-based buy opportunity analysis (0–100).

    | Score | Recommendation |
    |-------|---------------|
    | 0–30  | AVOID |
    | 31–60 | WAIT |
    | 61–80 | BUY |
    | 81–100 | STRONG_BUY |

    The **score** and **indicators** are always computed on USD 24K. The
    `price` and `currency` fields in the response reflect your requested display currency/carat.
    """
    try:
        result = await RecommendationService().analyze_buy_opportunity(
            currency=currency, carat=carat
        )
        return result
    except Exception as exc:
        logger.error("http_error", endpoint="/analysis", error=str(exc))
        return _err(str(exc))


@app.get(
    "/summary",
    tags=["prices"],
    summary="Multi-currency market summary",
    response_model=MarketSummaryResponse,
    responses={500: {"model": ErrorResponse}},
    response_description="Concise summary across all currencies, suitable for Telegram",
)
async def summary():
    """
    One-shot market snapshot across all enabled currencies.

    Returns a `text` field formatted for Telegram/Slack alongside structured
    price data and the current buy score.
    """
    from src.tools.summary_tools import get_market_summary

    result = await get_market_summary()
    if "error" in result:
        return _err(result["error"])
    return result
