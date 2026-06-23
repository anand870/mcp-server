from __future__ import annotations

from src.database import (
    GoldIndicatorRepository,
    GoldPriceRepository,
    RecommendationRepository,
    session_scope,
)


def test_upsert_gold_price_creates_record():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2050.50, "USD", "24K", "test", open=2040.0, high=2060.0, low=2035.0)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        record = repo.get_latest(currency="USD", carat="24K")
        assert record is not None
        assert record.price == 2050.50
        assert record.date == "2024-01-15"
        assert record.source == "test"
        assert record.currency == "USD"
        assert record.carat == "24K"
        assert record.open == 2040.0


def test_upsert_gold_price_updates_existing():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2050.50, "USD", "24K", "test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2075.00, "USD", "24K", "updated_test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        assert repo.count(currency="USD", carat="24K") == 1
        record = repo.get_latest(currency="USD", carat="24K")
        assert record.price == 2075.00
        assert record.source == "updated_test"


def test_composite_unique_key_allows_different_currencies():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 2050.50, "USD", "24K", "test")
        repo.upsert("2024-01-15", 7524.00, "AED", "24K", "igold")
        repo.upsert("2024-01-15", 171000.0, "INR", "24K", "metalsdev_inr")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        assert repo.count() == 3
        usd = repo.get_latest(currency="USD", carat="24K")
        aed = repo.get_latest(currency="AED", carat="24K")
        inr = repo.get_latest(currency="INR", carat="24K")
        assert usd.price == 2050.50
        assert aed.price == 7524.00
        assert inr.price == 171000.0


def test_composite_unique_key_allows_different_carats():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 509.30, "AED", "24K", "igold", price_type="local", calculated=False)
        repo.upsert("2024-01-15", 471.54, "AED", "22K", "igold", price_type="local", calculated=False)
        repo.upsert("2024-01-15", 450.09, "AED", "21K", "igold", price_type="local", calculated=False)
        repo.upsert("2024-01-15", 385.79, "AED", "18K", "igold", price_type="local", calculated=False)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        assert repo.count(currency="AED") == 4
        record_22k = repo.get_latest(currency="AED", carat="22K")
        assert record_22k.price == 471.54
        assert record_22k.calculated is False
        assert record_22k.price_type == "local"


def test_upsert_marks_calculated():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-15", 1700.0, "INR", "22K", "usd_conversion",
                    price_type="converted", calculated=True)

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        record = repo.get_latest(currency="INR", carat="22K")
        assert record.calculated is True
        assert record.price_type == "converted"


def test_get_range_filters_by_currency_and_carat():
    with session_scope() as session:
        repo = GoldPriceRepository(session)
        repo.upsert("2024-01-10", 2000.0, "USD", "24K", "test")
        repo.upsert("2024-01-15", 2050.0, "USD", "24K", "test")
        repo.upsert("2024-01-15", 7500.0, "AED", "24K", "igold")
        repo.upsert("2024-01-20", 2100.0, "USD", "24K", "test")

    with session_scope() as session:
        repo = GoldPriceRepository(session)
        records = repo.get_range("2024-01-12", "2024-01-18", currency="USD", carat="24K")
        assert len(records) == 1
        assert records[0].date == "2024-01-15"
        assert records[0].currency == "USD"


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
