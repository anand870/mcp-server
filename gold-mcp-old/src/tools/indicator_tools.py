from __future__ import annotations

from src.services.indicator_service import IndicatorService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_gold_indicators() -> dict:
    """
    Return the latest computed technical indicators for gold:
    MA7, MA30, MA90, RSI(14) and trend direction.
    """
    logger.info("tool_invoked", tool="get_gold_indicators")
    try:
        svc = IndicatorService()
        result = svc.get_latest_indicators()
        if result is None:
            return {
                "error": "No indicator data available. Run scripts/refresh_history.py to populate.",
                "source": "gold-advisor",
            }
        return result.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="get_gold_indicators", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
