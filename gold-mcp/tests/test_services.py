from __future__ import annotations

import pytest

from src.schemas import GoldIndicatorsResponse
from src.services.indicator_service import _determine_trend


def test_trend_bullish():
    assert _determine_trend(price=90.0, ma7=88.0, ma30=85.0) == "Bullish"


def test_trend_bearish():
    assert _determine_trend(price=80.0, ma7=83.0, ma30=86.0) == "Bearish"


def test_trend_neutral_bullish():
    assert _determine_trend(price=88.0, ma7=90.0, ma30=85.0) == "Neutral-Bullish"


def test_trend_neutral_bearish():
    assert _determine_trend(price=82.0, ma7=80.0, ma30=85.0) == "Neutral-Bearish"


def test_trend_no_ma30():
    assert _determine_trend(price=85.0, ma7=None, ma30=None) == "Neutral"


def test_recommendation_scoring(monkeypatch):
    from src.services import recommendation_service
    from src.schemas import GoldIndicatorsResponse

    fake_indicators = GoldIndicatorsResponse(
        date="2024-06-01",
        price_usd_gram=85.0,
        ma7=84.0,
        ma30=87.0,
        ma90=90.0,
        rsi14=32.0,
        trend="Neutral-Bearish",
    )

    class FakePriceRow:
        price = 85.0
        date = "2024-06-01"
        source = "test"
        price_type = "local"

    class FakeRepo:
        def get_latest(self, currency=None, carat=None):
            return FakePriceRow()

    class FakeRecRepo:
        def save(self, **kwargs):
            pass

    monkeypatch.setattr(recommendation_service, "get_latest_indicators", lambda: fake_indicators)

    from contextlib import contextmanager

    @contextmanager
    def fake_scope():
        class FakeSession:
            def add(self, obj): pass
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
            def query(self, *a): ...
        yield FakeSession()

    monkeypatch.setattr(recommendation_service, "session_scope", fake_scope)
    monkeypatch.setattr(recommendation_service, "GoldPriceRepository", lambda s: FakeRepo())
    monkeypatch.setattr(recommendation_service, "RecommendationRepository", lambda s: FakeRecRepo())

    result = recommendation_service.analyze_buy_opportunity(currency="USD", carat="24K")

    # price < ma30 (+40), price < ma90 (+20), rsi < 35 (+20), ma7 < ma30 so no ma7_above_ma30
    assert result.score == 80
    assert result.recommendation == "BUY"
    assert result.confidence == 0.8


def test_recommendation_strong_buy(monkeypatch):
    from src.services import recommendation_service
    from src.schemas import GoldIndicatorsResponse

    fake_indicators = GoldIndicatorsResponse(
        date="2024-06-01",
        price_usd_gram=80.0,
        ma7=86.0,
        ma30=87.0,
        ma90=90.0,
        rsi14=30.0,
        trend="Neutral-Bearish",
    )

    class FakePriceRow:
        price = 80.0
        date = "2024-06-01"
        source = "test"
        price_type = "local"

    class FakeRepo:
        def get_latest(self, currency=None, carat=None):
            return FakePriceRow()

    class FakeRecRepo:
        def save(self, **kwargs): pass

    monkeypatch.setattr(recommendation_service, "get_latest_indicators", lambda: fake_indicators)

    from contextlib import contextmanager

    @contextmanager
    def fake_scope():
        class FakeSession:
            def add(self, obj): pass
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
        yield FakeSession()

    monkeypatch.setattr(recommendation_service, "session_scope", fake_scope)
    monkeypatch.setattr(recommendation_service, "GoldPriceRepository", lambda s: FakeRepo())
    monkeypatch.setattr(recommendation_service, "RecommendationRepository", lambda s: FakeRecRepo())

    result = recommendation_service.analyze_buy_opportunity(currency="USD", carat="24K")

    # price < ma30 (+40), price < ma90 (+20), rsi < 35 (+20), ma7 < ma30 (+0)
    assert result.score == 80
    assert result.recommendation == "BUY"


def test_recommendation_avoid(monkeypatch):
    from src.services import recommendation_service
    from src.schemas import GoldIndicatorsResponse

    fake_indicators = GoldIndicatorsResponse(
        date="2024-06-01",
        price_usd_gram=95.0,
        ma7=90.0,
        ma30=85.0,
        ma90=80.0,
        rsi14=65.0,
        trend="Bullish",
    )

    class FakePriceRow:
        price = 95.0
        date = "2024-06-01"
        source = "test"
        price_type = "local"

    class FakeRepo:
        def get_latest(self, currency=None, carat=None):
            return FakePriceRow()

    class FakeRecRepo:
        def save(self, **kwargs): pass

    monkeypatch.setattr(recommendation_service, "get_latest_indicators", lambda: fake_indicators)

    from contextlib import contextmanager

    @contextmanager
    def fake_scope():
        class FakeSession:
            def add(self, obj): pass
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
        yield FakeSession()

    monkeypatch.setattr(recommendation_service, "session_scope", fake_scope)
    monkeypatch.setattr(recommendation_service, "GoldPriceRepository", lambda s: FakeRepo())
    monkeypatch.setattr(recommendation_service, "RecommendationRepository", lambda s: FakeRecRepo())

    result = recommendation_service.analyze_buy_opportunity(currency="USD", carat="24K")

    assert result.score == 0
    assert result.recommendation == "AVOID"
