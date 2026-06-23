from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run tests marked with @pytest.mark.live (hits real external APIs)",
    )


def pytest_collection_modifyitems(config, items):
    run_live = config.getoption("--run-live") or os.getenv("PYTEST_LIVE") == "1"
    if not run_live:
        skip = pytest.mark.skip(reason="Live network test — run with --run-live or PYTEST_LIVE=1")
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip)


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_gold.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)

    import src.config as cfg_module
    cfg_module._config = None

    init_db(db_path)
    yield
    cfg_module._config = None
