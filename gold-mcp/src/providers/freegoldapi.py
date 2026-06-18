from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult
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

        price = float(data.get("price") or data.get("price_gram_24k") or data.get("price_troy_oz", 0))
        if price <= 0:
            raise ValueError(f"FreeGoldAPI returned invalid price: {data}")

        today = date.today().isoformat()
        logger.info("freegoldapi_current_price_fetched", price=price, date=today)
        return PriceResult(
            price_usd=price,
            date=today,
            source=self.name,
            open_usd=data.get("open"),
            high_usd=data.get("high"),
            low_usd=data.get("low"),
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
                    price_usd=p,
                    open_usd=item.get("open"),
                    high_usd=item.get("high"),
                    low_usd=item.get("low"),
                    source=self.name,
                ))

        logger.info("freegoldapi_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
