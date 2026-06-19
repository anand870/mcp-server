from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from src.database import GoldPriceRepository, session_scope
from src.services.indicator_service import IndicatorService, _compute_rsi, _determine_trend


def test_rsi_range():
    prices = pd.Series([1800 + i * 5 for i in range(30)])
    rsi = _compute_rsi(prices, period=14)
    valid = rsi.dropna()
    assert (valid >= 0).all()
    assert (valid <= 100).all()


def test_rsi_overbought():
    prices = pd.Series([1800 + i * 20 for i in range(30)])
    rsi = _compute_rsi(prices, period=14)
    last = rsi.dropna().iloc[-1]
    assert last > 70


def test_rsi_oversold():
    prices = pd.Series([2000 - i * 20 for i in range(30)])
    rsi = _compute_rsi(prices, period=14)
    last = rsi.dropna().iloc[-1]
    assert last < 30


def test_determine_trend_bullish():
    trend = _determine_trend(price=2100, ma7=2080, ma30=2060, ma90=2000)
    assert trend == "Bullish"


def test_determine_trend_bearish():
    trend = _determine_trend(price=1950, ma7=1980, ma30=2000, ma90=2050)
    assert trend == "Bearish"


def test_determine_trend_neutral():
    trend = _determine_trend(price=2050, ma7=None, ma30=None, ma90=None)
    assert trend == "Neutral"


def test_compute_and_store_requires_data():
    svc = IndicatorService()
    count = svc.compute_and_store()
    assert count == 0


def test_compute_and_store_with_sufficient_data():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        from datetime import date, timedelta
        for i in range(100):
            d = (date(2024, 1, 1) + timedelta(days=i)).isoformat()
            repo.upsert(d, 2000.0 + i * 0.5, "USD", "24K", "test")

    svc = IndicatorService()
    count = svc.compute_and_store()
    assert count == 100

    result = svc.get_latest_indicators()
    assert result is not None
    assert result.ma7 is not None
    assert result.ma30 is not None
    assert result.rsi14 is not None
