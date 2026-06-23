from __future__ import annotations

from src.services.recommendation_service import RecommendationService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def analyze_buy_opportunity(
    currency: str | None = None, carat: str | None = None
) -> dict:
    """
    Analyze whether now is a good time to buy gold.

    Scoring is always based on USD 24K technical indicators.
    The price field in the response reflects the requested currency/carat.

    Args:
        currency: Currency code (USD, AED, INR). Defaults to configured default.
        carat: Gold purity (24K, 22K, 21K, 18K). Defaults to configured default.
    """
    logger.info("tool_invoked", tool="analyze_buy_opportunity", currency=currency, carat=carat)
    try:
        svc = RecommendationService()
        result = await svc.analyze_buy_opportunity(currency=currency, carat=carat)
        return result.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="analyze_buy_opportunity", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
