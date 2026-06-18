from __future__ import annotations

import pytest

from src.database import (
    GoldIndicatorRepository,
    GoldPriceRepository,
    RecommendationRepository,
    session_scope,
)


def test_upsert_gold_price_creates_record():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2050.50, "test", open_usd=2040.0, high_usd=2060.0, low_usd=2035.0)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        record = repo.get_latest()
        assert record is not None
        assert record.price_usd == 2050.50
        assert record.date == "2024-01-15"
        assert record.source == "test"
        assert record.open_usd == 2040.0


def test_upsert_gold_price_updates_existing():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2050.50, "test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2075.00, "updated_test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        assert repo.count() == 1
        record = repo.get_latest()
        assert record.price_usd == 2075.00
        assert record.source == "updated_test"


def test_get_range():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-10", 2000.0, "test")
        repo.upsert("2024-01-15", 2050.0, "test")
        repo.upsert("2024-01-20", 2100.0, "test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        records = repo.get_range("2024-01-12", "2024-01-18")
        assert len(records) == 1
        assert records[0].date == "2024-01-15"


def test_upsert_indicator():
    with session_scope() as session:
        repo = GoldIndicatorRepository(session)
        repo.upsert("2024-01-15", ma7=2045.0, ma30=2030.0, ma90=1990.0, rsi14=42.5)

    with session_scope() as session:
        repo = GoldIndicatorRepository(session)
        ind = repo.get_latest()
        assert ind is not None
        assert ind.ma7 == 2045.0
        assert ind.ma30 == 2030.0
        assert ind.rsi14 == 42.5


def test_upsert_indicator_updates_existing():
    with session_scope() as session:
        repo = GoldIndicatorRepository(session)
        repo.upsert("2024-01-15", ma7=2045.0, ma30=2030.0, ma90=1990.0, rsi14=42.5)

    with session_scope() as session:
        repo = GoldIndicatorRepository(session)
        repo.upsert("2024-01-15", ma7=2050.0, ma30=2035.0, ma90=1995.0, rsi14=45.0)

    with session_scope() as session:
        repo = GoldIndicatorRepository(session)
        ind = repo.get_latest()
        assert ind.ma7 == 2050.0
        assert ind.rsi14 == 45.0


def test_save_recommendation():
    with session_scope() as session:
        repo = RecommendationRepository(session)
        repo.save(
            date_str="2024-01-15",
            price_usd=2050.0,
            score=75,
            recommendation="BUY",
            reasoning="Price below MA30; RSI oversold",
            score_breakdown={"price_below_ma30": 40, "rsi_below_35": 20, "total": 60},
        )

    with session_scope() as session:
        repo = RecommendationRepository(session)
        records = repo.get_recent(5)
        assert len(records) == 1
        assert records[0].recommendation == "BUY"
        assert records[0].score == 75
