from __future__ import annotations

from src.services.indicator_service import get_latest_indicators
from src.services.recommendation_service import analyze_buy_opportunity as _analyze
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_gold_indicators() -> dict:
    logger.info("tool_get_gold_indicators")
    indicators = get_latest_indicators()
    if indicators is None:
        return {"error": "No indicator data found in database."}
    return indicators.model_dump()


def analyze_buy_opportunity(currency: str = "AED", carat: str = "24K") -> dict:
    logger.info("tool_analyze_buy_opportunity", currency=currency, carat=carat)
    try:
        result = _analyze(currency=currency.upper(), carat=carat.upper())
        return result.model_dump()
    except RuntimeError as e:
        logger.warning("tool_analyze_buy_opportunity_error", error=str(e))
        return {"error": str(e)}
