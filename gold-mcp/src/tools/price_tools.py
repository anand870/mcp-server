from __future__ import annotations

from src.services.gold_service import GoldService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_gold_price() -> dict:
    """Fetch the current gold spot price in USD per troy ounce."""
    logger.info("tool_invoked", tool="get_gold_price")
    try:
        svc = GoldService()
        result = await svc.get_current_price()
        return result.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="get_gold_price", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
