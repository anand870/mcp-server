from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.providers.base import TROY_OZ_PER_GRAM, GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

GOLD_TICKER = "GC=F"


class YahooFinanceProvider(GoldProvider):
    name = "yahoofinance"

    def supports_current_price(self) -> bool:
        return True

    def supports_historical(self) -> bool:
        return True

    async def get_current_price(self) -> PriceResult:
        ticker = yf.Ticker(GOLD_TICKER)
        info = ticker.fast_info
        price_toz = float(info.last_price or 0)

        if price_toz <= 0:
            hist = ticker.history(period="1d", interval="1d")
            if hist.empty:
                raise ValueError("Yahoo Finance returned no data for GC=F")
            price_toz = float(hist["Close"].iloc[-1])

        price = round(price_toz / TROY_OZ_PER_GRAM, 4)
        today = date.today().isoformat()
        logger.info("yahoofinance_current_price_fetched", price=price, date=today)
        return PriceResult(
            price=price,
            currency="USD",
            carat="24K",
            source=self.name,
            price_type="local",
            date=today,
            carat_prices=derive_carat_prices(price),
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        end = date.today()
        start = end - timedelta(days=days + 10)

        ticker = yf.Ticker(GOLD_TICKER)
        hist = ticker.history(start=start.isoformat(), end=end.isoformat(), interval="1d")

        if hist.empty:
            raise ValueError("Yahoo Finance returned empty historical data for GC=F")

        entries: list[HistoricalEntry] = []
        for idx, row in hist.iterrows():
            d = pd.Timestamp(idx).date().isoformat()
            close = float(row["Close"])
            if close > 0:
                def _g(v):
                    f = float(v) if v else 0.0
                    return round(f / TROY_OZ_PER_GRAM, 4) if f > 0 else None
                entries.append(HistoricalEntry(
                    date=d,
                    price=round(close / TROY_OZ_PER_GRAM, 4),
                    currency="USD",
                    carat="24K",
                    price_type="local",
                    calculated=False,
                    source=self.name,
                    open=_g(row.get("Open")),
                    high=_g(row.get("High")),
                    low=_g(row.get("Low")),
                ))

        logger.info("yahoofinance_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
