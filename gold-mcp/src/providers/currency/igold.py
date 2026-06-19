from __future__ import annotations

import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

_IGOLD_URL = "https://igold.ae/gold-rate/"


class IgoldProvider(GoldProvider):
    """Scrapes live AED gold rates from igold.ae.

    Parses the table with 24K / 22K / 21K / 18K per troy ounce prices.
    All carat prices are provider-supplied (calculated=False).
    """

    name = "igold"

    def supports_current_price(self) -> bool:
        return True

    def supports_historical(self) -> bool:
        return False

    async def get_current_price(self) -> PriceResult:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                _IGOLD_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GoldAdvisor/2.0)"},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Multiple tables share the "table" class; find the one whose thead
        # contains carat headers (24K, 22K, …) to avoid matching other tables.
        table = next(
            (
                t
                for t in soup.find_all("table")
                if (thead := t.find("thead")) and "24K" in thead.get_text()
            ),
            None,
        )
        if table is None:
            raise ValueError("iGold: could not find carat price table on page")

        header_cells = table.find("thead").find_all("td")
        carats = [c.get_text(strip=True) for c in header_cells]

        body_cells = table.find("tbody").find_all("td")
        prices_raw = [c.get_text(strip=True) for c in body_cells]

        if len(carats) != len(prices_raw):
            raise ValueError(
                f"iGold: header/body cell count mismatch ({len(carats)} vs {len(prices_raw)})"
            )

        provider_carats: dict[str, float] = {}
        for carat_label, price_str in zip(carats, prices_raw):
            numeric = re.sub(r"[^\d.]", "", price_str)
            if numeric:
                provider_carats[carat_label] = float(numeric)

        price_24k = provider_carats.get("24K")
        if price_24k is None or price_24k <= 0:
            raise ValueError(f"iGold: missing or invalid 24K price: {provider_carats}")

        carat_prices = derive_carat_prices(price_24k, provider_carats=provider_carats)
        today = date.today().isoformat()

        logger.info("igold_price_fetched", price_24k=price_24k, currency="AED", date=today)
        return PriceResult(
            price=price_24k,
            currency="AED",
            carat="24K",
            source=self.name,
            price_type="local",
            date=today,
            carat_prices=carat_prices,
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        raise NotImplementedError("iGold does not provide historical data")
