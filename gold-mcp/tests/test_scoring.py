from __future__ import annotations

import pytest

from src.config import get_config
from src.services.recommendation_service import _map_recommendation


def test_map_recommendation_avoid():
    config = get_config()
    thresholds = config.scoring.thresholds
    assert _map_recommendation(0, thresholds) == "AVOID"
    assert _map_recommendation(30, thresholds) == "AVOID"


def test_map_recommendation_wait():
    config = get_config()
    thresholds = config.scoring.thresholds
    assert _map_recommendation(31, thresholds) == "WAIT"
    assert _map_recommendation(60, thresholds) == "WAIT"


def test_map_recommendation_buy():
    config = get_config()
    thresholds = config.scoring.thresholds
    assert _map_recommendation(61, thresholds) == "BUY"
    assert _map_recommendation(80, thresholds) == "BUY"


def test_map_recommendation_strong_buy():
    config = get_config()
    thresholds = config.scoring.thresholds
    assert _map_recommendation(81, thresholds) == "STRONG_BUY"
    assert _map_recommendation(100, thresholds) == "STRONG_BUY"


def test_score_rules_sum_to_100():
    config = get_config()
    rules = config.scoring.rules
    total = (
        rules.price_below_ma30
        + rules.price_below_ma90
        + rules.rsi_below_35
        + rules.ma7_above_ma30
    )
    assert total == 100


def test_scoring_thresholds_ordered():
    config = get_config()
    t = config.scoring.thresholds
    assert t.avoid_max < t.wait_max < t.buy_max <= t.strong_buy_max
