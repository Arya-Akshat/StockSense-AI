from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.utils.constants import DATABASE_PATH, DATA_DIR


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                daily_return REAL NOT NULL,
                moving_average_7 REAL,
                high_52_week REAL NOT NULL,
                low_52_week REAL NOT NULL,
                volatility_14 REAL,
                PRIMARY KEY (symbol, date)
            )
            """
        )
        connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    initialize_database()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
