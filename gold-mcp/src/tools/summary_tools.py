from __future__ import annotations

from datetime import datetime

from src.schemas import MarketSummaryResponse
from src.services.recommendation_service import RecommendationService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_market_summary() -> dict:
    """
    Return a concise market summary suitable for Telegram or quick AI agent consumption.

    Includes current price, trend, RSI, buy score, and recommendation in a human-readable format.
    """
    logger.info("tool_invoked", tool="get_market_summary")
    try:
        svc = RecommendationService()
        analysis = await svc.analyze_buy_opportunity()

        price = analysis.price_usd
        rsi = analysis.indicators.rsi14
        trend = analysis.indicators.trend
        score = analysis.score
        recommendation = analysis.recommendation

        rsi_str = f"{rsi:.0f}" if rsi is not None else "N/A"
        text = (
            f"Gold Price: ${price:,.0f}\n"
            f"Trend: {trend}\n"
            f"RSI: {rsi_str}\n"
            f"Buy Score: {score}/100\n"
            f"Recommendation: {recommendation}"
        )

        summary = MarketSummaryResponse(
            text=text,
            price_usd=price,
            trend=trend,
            rsi14=rsi,
            buy_score=score,
            recommendation=recommendation,
            date=analysis.date,
        )
        return summary.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="get_market_summary", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
