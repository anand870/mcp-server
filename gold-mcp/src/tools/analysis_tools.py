from __future__ import annotations

from src.services.recommendation_service import RecommendationService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def analyze_buy_opportunity() -> dict:
    """
    Analyze whether now is a good time to buy gold.

    Returns a score (0-100), recommendation (AVOID/WAIT/BUY/STRONG_BUY),
    score breakdown, and reasoning for each component.
    """
    logger.info("tool_invoked", tool="analyze_buy_opportunity")
    try:
        svc = RecommendationService()
        result = await svc.analyze_buy_opportunity()
        return result.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="analyze_buy_opportunity", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
