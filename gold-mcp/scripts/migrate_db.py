#!/usr/bin/env python3
"""
Migrate the gold.db SQLite database from v1 schema (price_usd, single date unique key)
to v2 schema (price, currency, carat columns with composite unique key).

Safe to run multiple times — detects schema version before acting.

Usage:
    python scripts/migrate_db.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


def migrate(db_path: str) -> None:
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        if not _table_exists(conn, "gold_prices"):
            print("  gold_prices table does not exist — nothing to migrate.")
            return

        cols = _column_names(conn, "gold_prices")

        if "currency" in cols and "carat" in cols and "price" in cols:
            print("  gold_prices already at v2 schema — skipping migration.")
            return

        if "price_usd" not in cols:
            print("  ERROR: Unexpected schema — neither v1 nor v2. Aborting.")
            sys.exit(1)

        print("  Detected v1 schema (price_usd). Migrating to v2...")

        # Step 1: Create the new table with v2 schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_prices_v2 (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT    NOT NULL,
                currency   TEXT    NOT NULL DEFAULT 'USD',
                carat      TEXT    NOT NULL DEFAULT '24K',
                price      REAL    NOT NULL,
                open       REAL,
                high       REAL,
                low        REAL,
                source     TEXT    NOT NULL,
                price_type TEXT    NOT NULL DEFAULT 'local',
                calculated INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    DEFAULT (datetime('now')),
                updated_at TEXT    DEFAULT (datetime('now')),
                UNIQUE (date, currency, carat)
            )
        """)

        # Step 2: Copy existing USD 24K data
        conn.execute("""
            INSERT OR IGNORE INTO gold_prices_v2
                (date, currency, carat, price, open, high, low, source, price_type, calculated, created_at, updated_at)
            SELECT
                date,
                'USD',
                '24K',
                price_usd,
                open_usd,
                high_usd,
                low_usd,
                source,
                'local',
                0,
                created_at,
                updated_at
            FROM gold_prices
        """)

        row = conn.execute("SELECT COUNT(*) FROM gold_prices_v2").fetchone()
        migrated = row[0]

        # Step 3: Swap tables
        conn.execute("DROP TABLE gold_prices")
        conn.execute("ALTER TABLE gold_prices_v2 RENAME TO gold_prices")

        # Step 4: Recreate indexes
        conn.execute("CREATE INDEX IF NOT EXISTS ix_gold_prices_date ON gold_prices (date)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_gold_prices_currency_carat ON gold_prices (currency, carat)"
        )

        conn.commit()
        print(f"  Migration complete: {migrated} records migrated to v2 schema.")

    except Exception as exc:
        conn.rollback()
        print(f"  ERROR during migration: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main() -> None:
    config = get_config()
    db_path = config.database.path

    if not Path(db_path).exists():
        print(f"Database not found at {db_path} — no migration needed.")
        return

    migrate(db_path)


if __name__ == "__main__":
    main()
