from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class PriceResult:
    price_usd: float
    date: str
    source: str
    open_usd: float | None = None
    high_usd: float | None = None
    low_usd: float | None = None


@dataclass
class HistoricalEntry:
    date: str
    price_usd: float
    open_usd: float | None = None
    high_usd: float | None = None
    low_usd: float | None = None
    source: str = ""


class GoldProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def get_current_price(self) -> PriceResult:
        """Fetch the current gold spot price."""

    @abstractmethod
    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        """Fetch historical daily prices for the given number of days."""

    @abstractmethod
    def supports_current_price(self) -> bool:
        """Return True if the provider can supply current price."""

    @abstractmethod
    def supports_historical(self) -> bool:
        """Return True if the provider can supply historical data."""
