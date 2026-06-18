from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult
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
        price = float(info.last_price or 0)

        if price <= 0:
            hist = ticker.history(period="1d", interval="1d")
            if hist.empty:
                raise ValueError("Yahoo Finance returned no data for GC=F")
            price = float(hist["Close"].iloc[-1])

        today = date.today().isoformat()
        logger.info("yahoofinance_current_price_fetched", price=price, date=today)
        return PriceResult(
            price_usd=price,
            date=today,
            source=self.name,
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
                entries.append(HistoricalEntry(
                    date=d,
                    price_usd=close,
                    open_usd=float(row.get("Open", 0)) or None,
                    high_usd=float(row.get("High", 0)) or None,
                    low_usd=float(row.get("Low", 0)) or None,
                    source=self.name,
                ))

        logger.info("yahoofinance_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
