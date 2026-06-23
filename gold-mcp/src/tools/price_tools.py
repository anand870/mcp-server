from __future__ import annotations

from datetime import datetime

from src.config import get_settings
from src.database import GoldPriceRepository, session_scope
from src.schemas import CaratPriceDetail, GoldPriceResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_gold_price(currency: str = "AED", carat: str = "24K") -> dict:
    settings = get_settings()
    currency = (currency or settings.default_currency).upper()
    carat = (carat or settings.default_carat).upper()

    logger.info("tool_get_gold_price", currency=currency, carat=carat)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        latest_date = repo.get_latest_date_for_currency(currency)
        if latest_date is None:
            return {"error": f"No data found for currency {currency}"}
        rows = repo.get_by_date_and_currency(latest_date, currency)

    primary = next((r for r in rows if r.carat == carat), None)
    if primary is None:
        return {"error": f"No data found for {currency} {carat} on {latest_date}"}

    all_carats = [CaratPriceDetail(carat=r.carat, price=r.price, calculated=r.calculated) for r in rows]

    return GoldPriceResponse(
        price=primary.price,
        currency=primary.currency,
        carat=primary.carat,
        price_type=primary.price_type,
        date=primary.date,
        source=primary.source,
        timestamp=datetime.utcnow().isoformat() + "Z",
        all_carats=all_carats,
        open=primary.open,
        high=primary.high,
        low=primary.low,
    ).model_dump()


def get_gold_prices() -> dict:
    settings = get_settings()
    logger.info("tool_get_gold_prices")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        rows = repo.get_latest_per_currency_carat(settings.supported_currencies, settings.supported_carats)

    result: dict = {}
    for row in rows:
        result.setdefault(row.currency, {})[row.carat] = {
            "price": row.price,
            "calculated": row.calculated,
            "source": row.source,
            "date": row.date,
        }
    return result
