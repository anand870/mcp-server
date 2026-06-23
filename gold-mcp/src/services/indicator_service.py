from __future__ import annotations

from src.database import GoldIndicatorRepository, GoldPriceRepository, session_scope
from src.schemas import GoldIndicatorsResponse


def _determine_trend(price: float, ma7: float | None, ma30: float | None) -> str:
    if ma7 is not None and ma30 is not None:
        if price > ma7 > ma30:
            return "Bullish"
        if price < ma7 < ma30:
            return "Bearish"
    if ma30 is not None:
        return "Neutral-Bullish" if price > ma30 else "Neutral-Bearish"
    return "Neutral"


def get_latest_indicators() -> GoldIndicatorsResponse | None:
    with session_scope() as session:
        price_repo = GoldPriceRepository(session)
        ind_repo = GoldIndicatorRepository(session)
        latest_price = price_repo.get_latest(currency="USD", carat="24K")
        latest_ind = ind_repo.get_latest()

        if latest_price is None:
            return None

        price = latest_price.price
        today = latest_price.date
        ma7 = latest_ind.ma7 if latest_ind else None
        ma30 = latest_ind.ma30 if latest_ind else None
        ma90 = latest_ind.ma90 if latest_ind else None
        rsi14 = latest_ind.rsi14 if latest_ind else None
        ind_date = latest_ind.date if latest_ind else today

    trend = _determine_trend(price, ma7, ma30)

    return GoldIndicatorsResponse(
        date=ind_date,
        price_usd_gram=price,
        ma7=ma7,
        ma30=ma30,
        ma90=ma90,
        rsi14=rsi14,
        trend=trend,
    )
