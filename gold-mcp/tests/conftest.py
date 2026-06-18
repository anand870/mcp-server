from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_gold.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)

    import src.config as cfg_module
    cfg_module._config = None

    init_db(db_path)
    yield
    cfg_module._config = None
