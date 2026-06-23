from __future__ import annotations

from pydantic import BaseModel, Field


class CaratPriceDetail(BaseModel):
    carat: str
    price: float
    calculated: bool


class GoldPriceResponse(BaseModel):
    price: float
    currency: str
    carat: str
    price_type: str
    unit: str = "gram"
    date: str
    source: str
    timestamp: str
    all_carats: list[CaratPriceDetail] = []
    open: float | None = None
    high: float | None = None
    low: float | None = None


class GoldHistoryEntry(BaseModel):
    date: str
    price: float
    currency: str
    carat: str
    price_type: str
    unit: str = "gram"
    source: str
    open: float | None = None
    high: float | None = None
    low: float | None = None


class GoldHistoryResponse(BaseModel):
    entries: list[GoldHistoryEntry]
    period_days: int
    start_date: str
    end_date: str
    count: int
    currency: str
    carat: str
    unit: str = "gram"
    source: str = "database"


class GoldIndicatorsResponse(BaseModel):
    date: str
    price_usd_gram: float = Field(description="USD 24K spot price in per-gram units")
    unit: str = "gram"
    ma7: float | None = None
    ma30: float | None = None
    ma90: float | None = None
    rsi14: float | None = None
    trend: str
    source: str = "calculated"


class ScoreBreakdown(BaseModel):
    price_below_ma30: int = Field(description="Points awarded if price < MA30")
    price_below_ma90: int = Field(description="Points awarded if price < MA90")
    rsi_below_35: int = Field(description="Points awarded if RSI < 35")
    ma7_above_ma30: int = Field(description="Points awarded if MA7 > MA30")
    total: int


class BuyOpportunityResponse(BaseModel):
    date: str
    price: float
    currency: str
    carat: str
    unit: str = "gram"
    price_usd_gram: float = Field(description="USD 24K spot price in per-gram units used for scoring")
    score: int
    recommendation: str
    reasoning: list[str]
    score_breakdown: ScoreBreakdown
    indicators: GoldIndicatorsResponse
    confidence: float


class MarketSummaryResponse(BaseModel):
    text: str
    prices: dict[str, dict[str, CaratPriceDetail]]
    buy_score: int
    recommendation: str
    trend: str
    rsi14: float | None
    date: str
    source: str = "gold-advisor"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    source: str = "gold-advisor"
