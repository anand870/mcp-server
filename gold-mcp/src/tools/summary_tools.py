from __future__ import annotations

from src.config import get_settings
from src.database import GoldPriceRepository, session_scope
from src.schemas import CaratPriceDetail, MarketSummaryResponse
from src.services.indicator_service import get_latest_indicators
from src.services.recommendation_service import analyze_buy_opportunity as _analyze
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_market_summary() -> dict:
    settings = get_settings()
    logger.info("tool_get_market_summary")

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
    ).model_dump()
