from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import TROY_OZ_PER_GRAM, GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

FREEGOLDAPI_BASE = "https://freegoldapi.com/api"


class FreeGoldAPIProvider(GoldProvider):
    name = "freegoldapi"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._headers = {}
        if api_key:
            self._headers["x-api-key"] = api_key

    def supports_current_price(self) -> bool:
        return True

    def supports_historical(self) -> bool:
        return True

    async def get_current_price(self) -> PriceResult:
        url = f"{FREEGOLDAPI_BASE}/XAU/USD"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            data = response.json()

        # Prefer the native per-gram field; fall back to troy oz fields and convert
        price_gram = data.get("price_gram_24k")
        if price_gram:
            price = float(price_gram)
        else:
            price_toz = float(data.get("price") or data.get("price_troy_oz", 0))
            if price_toz <= 0:
                raise ValueError(f"FreeGoldAPI returned invalid price: {data}")
            price = price_toz / TROY_OZ_PER_GRAM

        price = round(price, 4)

        def _to_gram(v):
            return round(float(v) / TROY_OZ_PER_GRAM, 4) if v else None

        today = date.today().isoformat()
        logger.info("freegoldapi_current_price_fetched", price=price, date=today)
        return PriceResult(
            price=price,
            currency="USD",
            carat="24K",
            source=self.name,
            price_type="local",
            date=today,
            carat_prices=derive_carat_prices(price),
            open=_to_gram(data.get("open")),
            high=_to_gram(data.get("high")),
            low=_to_gram(data.get("low")),
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        entries: list[HistoricalEntry] = []
        end = date.today()
        start = end - timedelta(days=days)

        url = f"{FREEGOLDAPI_BASE}/XAU/USD/history"
        params = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            data = response.json()

        raw_list = data if isinstance(data, list) else data.get("data", data.get("history", []))
        for item in raw_list:
            d = item.get("date") or item.get("timestamp", "")
            if len(d) > 10:
                d = d[:10]
            p = float(item.get("price") or item.get("close") or item.get("price_troy_oz", 0))
            if d and p > 0:
                entries.append(HistoricalEntry(
                    date=d,
                    price=p,
                    currency="USD",
                    carat="24K",
                    price_type="local",
                    calculated=False,
                    source=self.name,
                    open=item.get("open"),
                    high=item.get("high"),
                    low=item.get("low"),
                ))

        logger.info("freegoldapi_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
