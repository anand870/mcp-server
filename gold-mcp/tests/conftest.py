from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    sess = SessionLocal()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def gold_price_row(session):
    from src.models import GoldPrice

    row = GoldPrice(
        date="2024-06-01",
        currency="USD",
        carat="24K",
        price=85.50,
        open=85.00,
        high=86.00,
        low=84.50,
        source="test",
        price_type="local",
        calculated=False,
    )
    session.add(row)
    session.commit()
    return row


@pytest.fixture
def indicator_row(session):
    from src.models import GoldIndicator

    row = GoldIndicator(
        date="2024-06-01",
        ma7=84.0,
        ma30=87.0,
        ma90=90.0,
        rsi14=32.0,
    )
    session.add(row)
    session.commit()
    return row
