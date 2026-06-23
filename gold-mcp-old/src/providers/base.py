from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

TROY_OZ_PER_GRAM: float = 31.1035

PURITY_RATIOS: dict[str, float] = {
    "24K": 1.0,
    "22K": 22 / 24,
    "21K": 21 / 24,
    "18K": 18 / 24,
}


@dataclass
class CaratPrice:
    carat: str
    price: float
    calculated: bool


@dataclass
class PriceResult:
    price: float
    currency: str
    source: str
    date: str
    price_type: str = "local"
    carat: str = "24K"
    carat_prices: list[CaratPrice] = field(default_factory=list)
    open: float | None = None
    high: float | None = None
    low: float | None = None


@dataclass
class HistoricalEntry:
    date: str
    price: float
    currency: str = "USD"
    carat: str = "24K"
    price_type: str = "local"
    calculated: bool = False
    source: str = ""
    open: float | None = None
    high: float | None = None
    low: float | None = None


def derive_carat_prices(price_24k: float, provider_carats: dict[str, float] | None = None) -> list[CaratPrice]:
    """Build a CaratPrice list for all standard carats.

    provider_carats: mapping of carat -> price as supplied by the provider (not calculated).
    Any carat not in provider_carats is derived from the 24K price using purity ratios.
    """
    result: list[CaratPrice] = []
    supplied = provider_carats or {}
    for carat, ratio in PURITY_RATIOS.items():
        if carat in supplied:
            result.append(CaratPrice(carat=carat, price=supplied[carat], calculated=False))
        elif carat == "24K":
            # price_24k is the provider-supplied base price — never derived
            result.append(CaratPrice(carat="24K", price=price_24k, calculated=False))
        else:
            result.append(CaratPrice(carat=carat, price=round(price_24k * ratio, 4), calculated=True))
    return result


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
