from __future__ import annotations

from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetryConfig(BaseModel):
    attempts: int = 3
    wait_min: float = 1.0
    wait_max: float = 5.0
    wait_multiplier: float = 1.5


class CurrencyConfig(BaseModel):
    enabled: bool = True


class ProvidersConfig(BaseModel):
    currency_order: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "USD": ["freegoldapi", "metalsdev", "goldapi", "yahoofinance"],
            "AED": ["igold", "dubaicityofgold", "usd_conversion"],
            "INR": ["metalsdev_inr", "usd_conversion"],
        }
    )
    historical_order: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "USD": ["yahoofinance", "freegoldapi", "metalsdev", "goldapi"],
            "AED": ["usd_conversion"],
            "INR": ["metalsdev_inr", "usd_conversion"],
        }
    )
    retry: RetryConfig = RetryConfig()


class FXConfig(BaseModel):
    cache_ttl_seconds: int = 3600


class IndicatorsConfig(BaseModel):
    ma_periods: list[int] = [7, 30, 90]
    rsi_period: int = 14


class ScoringRules(BaseModel):
    price_below_ma30: int = 40
    price_below_ma90: int = 20
    rsi_below_35: int = 20
    ma7_above_ma30: int = 20


class ScoringThresholds(BaseModel):
    avoid_max: int = 30
    wait_max: int = 60
    buy_max: int = 80
    strong_buy_max: int = 100


class ScoringConfig(BaseModel):
    rules: ScoringRules = ScoringRules()
    thresholds: ScoringThresholds = ScoringThresholds()


class CacheConfig(BaseModel):
    price_ttl_seconds: int = 300
    indicators_ttl_seconds: int = 3600


class DatabaseConfig(BaseModel):
    path: str = str(_PROJECT_ROOT / "data" / "gold.db")


class ServerConfig(BaseModel):
    name: str = "gold-advisor"
    version: str = "2.0.0"
    description: str = "Gold price intelligence and buy-opportunity analysis MCP server"


class HTTPConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    log_file: str = str(_PROJECT_ROOT / "data" / "gold-mcp.log")
    log_file_max_bytes: int = 5_000_000
    log_file_backup_count: int = 3


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    default_currency: str = "AED"
    default_carat: str = "24K"
    currencies: dict[str, CurrencyConfig] = Field(
        default_factory=lambda: {
            "USD": CurrencyConfig(),
            "AED": CurrencyConfig(),
            "INR": CurrencyConfig(),
        }
    )
    carats: list[str] = ["24K", "22K", "21K", "18K"]
    providers: ProvidersConfig = ProvidersConfig()
    fx: FXConfig = FXConfig()
    indicators: IndicatorsConfig = IndicatorsConfig()
    scoring: ScoringConfig = ScoringConfig()
    cache: CacheConfig = CacheConfig()
    http: HTTPConfig = HTTPConfig()
    logging: LoggingConfig = LoggingConfig()

    def enabled_currencies(self) -> list[str]:
        return [c for c, cfg in self.currencies.items() if cfg.enabled]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    freegoldapi_key: str = ""
    metalsdev_key: str = ""
    goldapi_key: str = ""
    database_path: str = ""
    config_path: str = "config.yaml"
    log_level: str = ""


def load_config(config_path: str | None = None) -> AppConfig:
    settings = Settings()
    path = config_path or settings.config_path

    raw: dict[str, Any] = {}
    if Path(path).exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

    config = AppConfig.model_validate(raw)

    if settings.database_path:
        config.database.path = settings.database_path
    if settings.log_level:
        config.logging.level = settings.log_level

    return config


def get_settings() -> Settings:
    return Settings()


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config
