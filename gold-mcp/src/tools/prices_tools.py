from __future__ import annotations

from src.services.gold_service import GoldService
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_gold_prices() -> dict:
    """Fetch current gold prices for all enabled currencies and all standard carats."""
    logger.info("tool_invoked", tool="get_gold_prices")
    try:
        svc = GoldService()
        result = await svc.get_all_current_prices()
        # Convert CaratPriceDetail objects to dicts
        return {
            currency: {
                carat: detail.model_dump()
                for carat, detail in carats.items()
            }
            for currency, carats in result.items()
        }
    except Exception as exc:
        logger.error("tool_error", tool="get_gold_prices", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
