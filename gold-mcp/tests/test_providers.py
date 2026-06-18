from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.providers.base import PriceResult, HistoricalEntry
from src.providers.freegoldapi import FreeGoldAPIProvider
from src.providers.yahoofinance import YahooFinanceProvider
from src.providers.metalsdev import MetalsDevProvider
from src.providers.goldapi import GoldAPIProvider


@pytest.mark.asyncio
async def test_freegoldapi_get_current_price():
    provider = FreeGoldAPIProvider(api_key="test_key")
    mock_response = MagicMock()
    mock_response.json.return_value = {"price": 2050.75, "open": 2040.0, "high": 2060.0, "low": 2035.0}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd == 2050.75
    assert result.source == "freegoldapi"


@pytest.mark.asyncio
async def test_freegoldapi_invalid_price_raises():
    provider = FreeGoldAPIProvider()
    mock_response = MagicMock()
    mock_response.json.return_value = {"price": 0}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError):
            await provider.get_current_price()


def test_metalsdev_no_key_unsupported():
    provider = MetalsDevProvider(api_key="")
    assert provider.supports_current_price() is False
    assert provider.supports_historical() is False


def test_metalsdev_with_key_supported():
    provider = MetalsDevProvider(api_key="somekey")
    assert provider.supports_current_price() is True
    assert provider.supports_historical() is True


def test_goldapi_no_key_unsupported():
    provider = GoldAPIProvider(api_key="")
    assert provider.supports_current_price() is False
    assert provider.supports_historical() is False


def test_freegoldapi_supports_all():
    provider = FreeGoldAPIProvider()
    assert provider.supports_current_price() is True
    assert provider.supports_historical() is True


@pytest.mark.asyncio
async def test_metalsdev_no_key_raises():
    provider = MetalsDevProvider(api_key="")
    with pytest.raises(ValueError, match="requires an API key"):
        await provider.get_current_price()


@pytest.mark.asyncio
async def test_goldapi_no_key_raises():
    provider = GoldAPIProvider(api_key="")
    with pytest.raises(ValueError, match="requires an API key"):
        await provider.get_current_price()


@pytest.mark.asyncio
async def test_yahoofinance_historical_structure():
    provider = YahooFinanceProvider()
    import pandas as pd
    from datetime import date, timedelta

    mock_data = {}
    for i in range(10):
        d = date(2024, 1, 1) + timedelta(days=i)
        mock_data[pd.Timestamp(d)] = {
            "Close": 2000 + i * 5,
            "Open": 1998 + i * 5,
            "High": 2010 + i * 5,
            "Low": 1990 + i * 5,
        }
    df = pd.DataFrame.from_dict(mock_data, orient="index")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df

    with patch("yfinance.Ticker", return_value=mock_ticker):
        entries = await provider.get_historical(10)

    assert len(entries) == 10
    assert all(isinstance(e, HistoricalEntry) for e in entries)
    assert entries[0].source == "yahoofinance"


# Integration tests for real API calls
@pytest.mark.integration
@pytest.mark.asyncio
async def test_goldapi_get_current_price_real():
    """Test GoldAPI current price with real API call"""
    from src.config import get_settings
    settings = get_settings()

    if not settings.goldapi_key:
        pytest.skip("GOLDAPI_KEY not set in .env")

    provider = GoldAPIProvider(api_key=settings.goldapi_key)
    result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd > 0
    assert result.source == "goldapi"
    assert result.date is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_goldapi_get_historical_real():
    """Test GoldAPI historical data with real API call"""
    from src.config import get_settings
    settings = get_settings()

    if not settings.goldapi_key:
        pytest.skip("GOLDAPI_KEY not set in .env")

    provider = GoldAPIProvider(api_key=settings.goldapi_key)
    results = await provider.get_historical(days=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(e, HistoricalEntry) for e in results)
    assert all(e.source == "goldapi" for e in results)
    assert all(e.price_usd > 0 for e in results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_freegoldapi_get_current_price_real():
    """Test FreeGoldAPI current price with real API call"""
    provider = FreeGoldAPIProvider()
    result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd > 0
    assert result.source == "freegoldapi"
    assert result.date is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_freegoldapi_get_historical_real():
    """Test FreeGoldAPI historical data with real API call"""
    provider = FreeGoldAPIProvider()
    results = await provider.get_historical(days=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(e, HistoricalEntry) for e in results)
    assert all(e.source == "freegoldapi" for e in results)
    assert all(e.price_usd > 0 for e in results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metalsdev_get_current_price_real():
    """Test MetalsDev current price with real API call"""
    from src.config import get_settings
    settings = get_settings()

    if not settings.metalsdev_key:
        pytest.skip("METALSDEV_KEY not set in .env")

    provider = MetalsDevProvider(api_key=settings.metalsdev_key)
    result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd > 0
    assert result.source == "metalsdev"
    assert result.date is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metalsdev_get_historical_real():
    """Test MetalsDev historical data with real API call"""
    from src.config import get_settings
    settings = get_settings()

    if not settings.metalsdev_key:
        pytest.skip("METALSDEV_KEY not set in .env")

    provider = MetalsDevProvider(api_key=settings.metalsdev_key)
    results = await provider.get_historical(days=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(e, HistoricalEntry) for e in results)
    assert all(e.source == "metalsdev" for e in results)
    assert all(e.price_usd > 0 for e in results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_yahoofinance_get_current_price_real():
    """Test YahooFinance current price with real API call"""
    provider = YahooFinanceProvider()
    result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd > 0
    assert result.source == "yahoofinance"
    assert result.date is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_yahoofinance_get_historical_real():
    """Test YahooFinance historical data with real API call"""
    provider = YahooFinanceProvider()
    results = await provider.get_historical(days=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(e, HistoricalEntry) for e in results)
    assert all(e.source == "yahoofinance" for e in results)
    assert all(e.price_usd > 0 for e in results)


@pytest.mark.asyncio
async def test_goldapi_get_current_price_mock():
    """Test GoldAPI current price with mocked response"""
    provider = GoldAPIProvider(api_key="test_key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "price": 2150.50,
        "open_price": 2140.0,
        "high_price": 2160.0,
        "low_price": 2135.0,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd == 2150.50
    assert result.source == "goldapi"
    assert result.open_usd == 2140.0


@pytest.mark.asyncio
async def test_metalsdev_get_current_price_mock():
    """Test MetalsDev current price with mocked response"""
    provider = MetalsDevProvider(api_key="test_key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "metals": {
            "gold": 2100.75,
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await provider.get_current_price()

    assert isinstance(result, PriceResult)
    assert result.price_usd == 2100.75
    assert result.source == "metalsdev"
