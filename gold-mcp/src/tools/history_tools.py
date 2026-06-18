from __future__ import annotations

from src.services.gold_service import GoldService
from src.utils.logging import get_logger

logger = get_logger(__name__)

VALID_PERIODS = {
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "5y": 1825,
    "10y": 3650,
}


async def get_gold_history(period: str = "90d") -> dict:
    """
    Fetch historical gold prices.

    Args:
        period: One of 30d, 90d, 1y, 5y, 10y. Defaults to 90d.
    """
    logger.info("tool_invoked", tool="get_gold_history", period=period)
    days = VALID_PERIODS.get(period)
    if days is None:
        return {
            "error": f"Invalid period '{period}'. Valid options: {list(VALID_PERIODS.keys())}",
            "source": "gold-advisor",
        }
    try:
        svc = GoldService()
        result = await svc.get_history(days)
        return result.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="get_gold_history", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
