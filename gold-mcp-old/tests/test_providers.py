from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class _MockResponse:
    def __init__(self, json_data: dict | list, status_code: int = 200, text: str = ""):
        self._json = json_data
        self.status_code = status_code
        self._text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    @property
    def text(self):
        return self._text


# ------------------------------------------------------------------ #
# iGold provider
# ------------------------------------------------------------------ #

_IGOLD_HTML = """
<html><body>
<!-- Two decoy tables that also have "table" in their class list — mirrors the
     real igold.ae page which has three tables sharing the "table" class.
     The old selector (find("table", class_="table")) would match Table 0
     which has no thead, causing AttributeError. -->
<table class="table text-center mb-1">
  <th scope="col">Metal</th><th scope="col">Gram</th>
</table>
<table class="table mobile text-center mb-1">
  <th scope="col">Metal</th><th scope="col">Gram</th>
</table>
<table class="table">
  <thead><tr><td>24K</td><td>22K</td><td>21K</td><td>18K</td></tr></thead>
  <tbody><tr>
    <td>509.30 AED</td><td>471.54 AED</td><td>450.09 AED</td><td>385.79 AED</td>
  </tr></tbody>
  <tfoot><tr><td colspan="4"><small>Prices updated: 19/06/2026 00:05:01</small></td></tr></tfoot>
</table>
</body></html>
"""


@pytest.mark.asyncio
async def test_igold_parses_all_carats():
    from src.providers.currency.igold import IgoldProvider

    provider = IgoldProvider()
    mock_resp = _MockResponse({}, text=_IGOLD_HTML)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await provider.get_current_price()

    assert result.currency == "AED"
    assert result.price_type == "local"
    assert result.price == pytest.approx(509.30)
    carats = {cp.carat: cp for cp in result.carat_prices}
    assert "24K" in carats and "22K" in carats
    assert carats["22K"].price == pytest.approx(471.54)
    assert carats["22K"].calculated is False
    assert carats["24K"].calculated is False


@pytest.mark.asyncio
async def test_igold_missing_table_raises():
    from src.providers.currency.igold import IgoldProvider

    provider = IgoldProvider()
    mock_resp = _MockResponse({}, text="<html><body>no table here</body></html>")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        with pytest.raises(ValueError, match="price table"):
            await provider.get_current_price()


# ------------------------------------------------------------------ #
# Dubai City of Gold provider
# ------------------------------------------------------------------ #

_DCOG_RESPONSE = {
    "status": "1",
    "msg": "Subscription Valid",
    "gold_rate_date": "2026-06-18",
    "gold_rate_24k": "509.25",
    "gold_rate_22k": "471.50",
    "gold_rate_21k": "452.00",
    "gold_rate_18k": "387.50",
    "gold_rate_14k": "302.25",
}


@pytest.mark.asyncio
async def test_dcog_parses_all_carats():
    from src.providers.currency.dubaicityofgold import DubaiCityOfGoldProvider

    provider = DubaiCityOfGoldProvider()
    mock_resp = _MockResponse(_DCOG_RESPONSE)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await provider.get_current_price()

    assert result.currency == "AED"
    assert result.price == pytest.approx(509.25)
    assert result.date == "2026-06-18"
    carats = {cp.carat: cp for cp in result.carat_prices}
    assert carats["22K"].price == pytest.approx(471.50)
    assert carats["22K"].calculated is False


@pytest.mark.asyncio
async def test_dcog_api_error_raises():
    from src.providers.currency.dubaicityofgold import DubaiCityOfGoldProvider

    provider = DubaiCityOfGoldProvider()
    mock_resp = _MockResponse({"status": "0", "msg": "Invalid vendor key"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(ValueError, match="Invalid vendor key"):
            await provider.get_current_price()


# ------------------------------------------------------------------ #
# FX rate provider
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fx_rate_provider_exchangerate_api():
    from src.providers.fx_rates import FXRateProvider

    provider = FXRateProvider(cache_ttl_seconds=60)
    mock_resp = _MockResponse({"rates": {"AED": 3.6725, "INR": 83.5}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        rate = await provider.get_rate("USD", "AED")

    assert rate == pytest.approx(3.6725)


@pytest.mark.asyncio
async def test_fx_rate_same_currency_is_one():
    from src.providers.fx_rates import FXRateProvider

    provider = FXRateProvider()
    rate = await provider.get_rate("USD", "USD")
    assert rate == 1.0


@pytest.mark.asyncio
async def test_fx_rate_caches_result():
    from src.providers.fx_rates import FXRateProvider

    provider = FXRateProvider(cache_ttl_seconds=3600)
    mock_resp = _MockResponse({"rates": {"AED": 3.6725}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        rate1 = await provider.get_rate("USD", "AED")
        rate2 = await provider.get_rate("USD", "AED")

    assert rate1 == rate2
    assert mock_client.get.call_count == 1  # second call served from cache


# ------------------------------------------------------------------ #
# derive_carat_prices utility
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# Khaleej Times provider
# ------------------------------------------------------------------ #

_KT_RESPONSE = {
    "date": "June 19, 2026 01:30:11",
    "rates": [
        {"type": "Type", "morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "yesterday": "Yesterday"},
        {"type": "Ounce", "morning": "465,028", "afternoon": "", "evening": "", "yesterday": "465,028"},
        {"type": "24K", "morning": "14,951.00", "afternoon": "14,960.00", "evening": "14,970.00", "yesterday": "14,951.00"},
        {"type": "22K", "morning": "13,705.00", "afternoon": "13,714.00", "evening": "", "yesterday": "13,705.00"},
        {"type": "21K", "morning": "0.00", "afternoon": "", "evening": "", "yesterday": "0.00"},
        {"type": "18K", "morning": "11,213.00", "afternoon": "", "evening": "", "yesterday": "11,213.00"},
    ],
}


@pytest.mark.asyncio
async def test_khaleejtimes_parses_latest_slot():
    from src.providers.currency.khaleejtimes import KhaleejTimesProvider

    provider = KhaleejTimesProvider()
    mock_resp = _MockResponse(_KT_RESPONSE)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await provider.get_current_price()

    assert result.currency == "INR"
    assert result.price_type == "local"
    assert result.source == "khaleejtimes"
    # 24K: evening slot (14,970.00) — most recent non-empty
    assert result.price == pytest.approx(14970.0)

    carats = {cp.carat: cp for cp in result.carat_prices}
    # 22K: afternoon slot (no evening), calculated=False
    assert carats["22K"].price == pytest.approx(13714.0)
    assert carats["22K"].calculated is False
    # 18K: morning slot only, calculated=False
    assert carats["18K"].price == pytest.approx(11213.0)
    assert carats["18K"].calculated is False
    # 21K: all slots are 0 → derived from purity ratio
    assert carats["21K"].calculated is True
    # 24K should not be calculated
    assert carats["24K"].calculated is False


@pytest.mark.asyncio
async def test_khaleejtimes_missing_24k_raises():
    from src.providers.currency.khaleejtimes import KhaleejTimesProvider

    provider = KhaleejTimesProvider()
    bad_response = {"date": "June 19, 2026", "rates": [
        {"type": "22K", "morning": "13,705.00", "afternoon": "", "evening": "", "yesterday": ""},
    ]}
    mock_resp = _MockResponse(bad_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        with pytest.raises(ValueError, match="24K"):
            await provider.get_current_price()


# ------------------------------------------------------------------ #
# derive_carat_prices utility
# ------------------------------------------------------------------ #

def test_derive_carat_prices_all_calculated():
    from src.providers.base import derive_carat_prices

    result = derive_carat_prices(3000.0)
    by_carat = {cp.carat: cp for cp in result}

    assert by_carat["24K"].price == pytest.approx(3000.0)
    assert by_carat["24K"].calculated is False
    assert by_carat["22K"].calculated is True
    assert by_carat["22K"].price == pytest.approx(3000.0 * 22 / 24)
    assert by_carat["18K"].price == pytest.approx(3000.0 * 18 / 24)


def test_derive_carat_prices_with_provider_values():
    from src.providers.base import derive_carat_prices

    provider_carats = {"24K": 509.30, "22K": 471.54, "21K": 450.09, "18K": 385.79}
    result = derive_carat_prices(509.30, provider_carats=provider_carats)
    by_carat = {cp.carat: cp for cp in result}

    for carat in ["24K", "22K", "21K", "18K"]:
        assert by_carat[carat].calculated is False

    assert by_carat["22K"].price == pytest.approx(471.54)
