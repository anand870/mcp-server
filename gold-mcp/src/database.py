from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_config
from src.models import Base, GoldIndicator, GoldPrice, RecommendationHistory


def get_engine(db_path: str | None = None):
    config = get_config()
    path = db_path or config.database.path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    return engine


_engine = None
_SessionLocal = None


def init_db(db_path: str | None = None) -> None:
    global _engine, _SessionLocal
    _engine = get_engine(db_path)
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Session:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class GoldPriceRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, date_str: str, price_usd: float, source: str,
               open_usd: float | None = None, high_usd: float | None = None,
               low_usd: float | None = None) -> GoldPrice:
        existing = self.session.query(GoldPrice).filter_by(date=date_str).first()
        if existing:
            existing.price_usd = price_usd
            existing.source = source
            if open_usd is not None:
                existing.open_usd = open_usd
            if high_usd is not None:
                existing.high_usd = high_usd
            if low_usd is not None:
                existing.low_usd = low_usd
            return existing
        record = GoldPrice(
            date=date_str,
            price_usd=price_usd,
            open_usd=open_usd,
            high_usd=high_usd,
            low_usd=low_usd,
            source=source,
        )
        self.session.add(record)
        return record

    def get_latest(self) -> GoldPrice | None:
        return (
            self.session.query(GoldPrice)
            .order_by(GoldPrice.date.desc())
            .first()
        )

    def get_range(self, start_date: str, end_date: str) -> list[GoldPrice]:
        return (
            self.session.query(GoldPrice)
            .filter(GoldPrice.date >= start_date, GoldPrice.date <= end_date)
            .order_by(GoldPrice.date.asc())
            .all()
        )

    def get_last_n_days(self, n: int) -> list[GoldPrice]:
        return (
            self.session.query(GoldPrice)
            .order_by(GoldPrice.date.desc())
            .limit(n)
            .all()
        )

    def count(self) -> int:
        return self.session.query(GoldPrice).count()


class GoldIndicatorRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, date_str: str, ma7: float | None, ma30: float | None,
               ma90: float | None, rsi14: float | None) -> GoldIndicator:
        existing = self.session.query(GoldIndicator).filter_by(date=date_str).first()
        if existing:
            existing.ma7 = ma7
            existing.ma30 = ma30
            existing.ma90 = ma90
            existing.rsi14 = rsi14
            return existing
        record = GoldIndicator(date=date_str, ma7=ma7, ma30=ma30, ma90=ma90, rsi14=rsi14)
        self.session.add(record)
        return record

    def get_latest(self) -> GoldIndicator | None:
        return (
            self.session.query(GoldIndicator)
            .order_by(GoldIndicator.date.desc())
            .first()
        )

    def get_range(self, start_date: str, end_date: str) -> list[GoldIndicator]:
        return (
            self.session.query(GoldIndicator)
            .filter(GoldIndicator.date >= start_date, GoldIndicator.date <= end_date)
            .order_by(GoldIndicator.date.asc())
            .all()
        )


class RecommendationRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, date_str: str, price_usd: float, score: int,
             recommendation: str, reasoning: str, score_breakdown: dict) -> RecommendationHistory:
        record = RecommendationHistory(
            date=date_str,
            price_usd=price_usd,
            score=score,
            recommendation=recommendation,
            reasoning=reasoning,
            score_breakdown=json.dumps(score_breakdown),
        )
        self.session.add(record)
        return record

    def get_recent(self, limit: int = 10) -> list[RecommendationHistory]:
        return (
            self.session.query(RecommendationHistory)
            .order_by(RecommendationHistory.created_at.desc())
            .limit(limit)
            .all()
        )
