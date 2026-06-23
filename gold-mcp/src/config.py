from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://gold_admin:gold_admin_password@localhost:5432/gold_db"
    default_currency: str = "AED"
    default_carat: str = "24K"
    supported_currencies: list[str] = ["USD", "AED", "INR"]
    supported_carats: list[str] = ["24K", "22K", "21K", "18K"]
    scoring_price_below_ma30: int = 40
    scoring_price_below_ma90: int = 20
    scoring_rsi_below_35: int = 20
    scoring_ma7_above_ma30: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
