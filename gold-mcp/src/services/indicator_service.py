from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.database import GoldIndicatorRepository, GoldPriceRepository, session_scope
from src.schemas import GoldIndicatorsResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _determine_trend(price: float, ma7: float | None, ma30: float | None, ma90: float | None) -> str:
    if ma7 is not None and ma30 is not None:
        if price > ma7 > ma30:
            return "Bullish"
        if price < ma7 < ma30:
            return "Bearish"
    if ma30 is not None:
        if price > ma30:
            return "Neutral-Bullish"
        return "Neutral-Bearish"
    return "Neutral"


class IndicatorService:
    def compute_and_store(self) -> int:
        with session_scope() as session:
            price_repo = GoldPriceRepository(session)
            records = price_repo.get_last_n_days(200)
            raw = [(r.date, r.price_usd) for r in records]

        if len(raw) < 7:
            logger.warning("indicator_service_insufficient_data", count=len(raw))
            return 0

        raw_sorted = sorted(raw, key=lambda r: r[0])
        dates = [r[0] for r in raw_sorted]
        prices = pd.Series([r[1] for r in raw_sorted], index=dates)

        ma7 = prices.rolling(7).mean()
        ma30 = prices.rolling(30).mean()
        ma90 = prices.rolling(90).mean()
        rsi14 = _compute_rsi(prices, period=14)

        stored = 0
        with session_scope() as session:
            ind_repo = GoldIndicatorRepository(session)
            for d in dates:
                ind_repo.upsert(
                    date_str=d,
                    ma7=float(ma7[d]) if not pd.isna(ma7[d]) else None,
                    ma30=float(ma30[d]) if not pd.isna(ma30[d]) else None,
                    ma90=float(ma90[d]) if not pd.isna(ma90[d]) else None,
                    rsi14=float(rsi14[d]) if not pd.isna(rsi14[d]) else None,
                )
                stored += 1

        logger.info("indicator_service_computed", stored=stored)
        return stored

    def get_latest_indicators(self) -> GoldIndicatorsResponse | None:
        with session_scope() as session:
            price_repo = GoldPriceRepository(session)
            ind_repo = GoldIndicatorRepository(session)
            latest_price = price_repo.get_latest()
            latest_ind = ind_repo.get_latest()

            if latest_price is None:
                return None

            price = latest_price.price_usd
            today = latest_price.date

            ma7 = latest_ind.ma7 if latest_ind else None
            ma30 = latest_ind.ma30 if latest_ind else None
            ma90 = latest_ind.ma90 if latest_ind else None
            rsi14 = latest_ind.rsi14 if latest_ind else None

        trend = _determine_trend(price, ma7, ma30, ma90)

        return GoldIndicatorsResponse(
            date=today,
            price_usd=price,
            ma7=ma7,
            ma30=ma30,
            ma90=ma90,
            rsi14=rsi14,
            trend=trend,
        )
