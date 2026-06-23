from __future__ import annotations

from datetime import datetime, timedelta

from src.database import GoldPriceRepository, session_scope
from src.schemas import GoldHistoryEntry, GoldHistoryResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)

PERIOD_DAYS: dict[str, int] = {
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "5y": 1825,
    "10y": 3650,
}


def get_gold_history(period: str = "30d", currency: str = "USD", carat: str = "24K") -> dict:
    currency = currency.upper()
    carat = carat.upper()
    days = PERIOD_DAYS.get(period, 30)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    logger.info("tool_get_gold_history", period=period, currency=currency, carat=carat, days=days)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        rows = repo.get_range(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            currency=currency,
            carat=carat,
        )

    if not rows:
        return {"error": f"No history found for {currency} {carat} in period {period}"}

    entries = [
        GoldHistoryEntry(
            date=r.date,
            price=r.price,
            currency=r.currency,
            carat=r.carat,
            price_type=r.price_type,
            source=r.source,
            open=r.open,
            high=r.high,
            low=r.low,
        )
        for r in rows
    ]

    return GoldHistoryResponse(
        entries=entries,
        period_days=days,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        count=len(entries),
        currency=currency,
        carat=carat,
    ).model_dump()
