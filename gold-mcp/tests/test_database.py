from __future__ import annotations

import pytest

from src.database import GoldIndicatorRepository, GoldPriceRepository


def test_get_latest_returns_most_recent(session):
    from src.models import GoldPrice

    session.add(GoldPrice(date="2024-05-01", currency="USD", carat="24K", price=80.0, source="t", price_type="local", calculated=False))
    session.add(GoldPrice(date="2024-06-01", currency="USD", carat="24K", price=85.5, source="t", price_type="local", calculated=False))
    session.commit()

    repo = GoldPriceRepository(session)
    latest = repo.get_latest(currency="USD", carat="24K")
    assert latest is not None
    assert latest.date == "2024-06-01"
    assert latest.price == 85.5


def test_get_latest_date_for_currency(session, gold_price_row):
    repo = GoldPriceRepository(session)
    date = repo.get_latest_date_for_currency("USD")
    assert date is not None


def test_get_by_date_and_currency(session, gold_price_row):
    repo = GoldPriceRepository(session)
    rows = repo.get_by_date_and_currency("2024-06-01", "USD")
    assert any(r.carat == "24K" for r in rows)


def test_get_range(session):
    from src.models import GoldPrice

    for i, d in enumerate(["2024-06-01", "2024-06-02", "2024-06-03"]):
        session.add(GoldPrice(date=d, currency="AED", carat="24K", price=300.0 + i, source="t", price_type="local", calculated=False))
    session.commit()

    repo = GoldPriceRepository(session)
    rows = repo.get_range("2024-06-01", "2024-06-02", currency="AED", carat="24K")
    assert len(rows) == 2


def test_get_latest_indicator(session, indicator_row):
    repo = GoldIndicatorRepository(session)
    ind = repo.get_latest()
    assert ind is not None
    assert ind.ma7 == 84.0
    assert ind.rsi14 == 32.0


def test_get_latest_returns_none_when_empty(session):
    repo = GoldIndicatorRepository(session)
    # Use a fresh session with no indicator data
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models import Base

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    fresh = sessionmaker(bind=eng)()
    ind = GoldIndicatorRepository(fresh).get_latest()
    assert ind is None
    fresh.close()
