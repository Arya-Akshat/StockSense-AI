from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf

from app.utils.constants import (
    CACHE_TTL_SECONDS,
    DATA_DIR,
    MOVING_AVERAGE_WINDOW,
    STOCK_SYMBOLS,
    TRADING_YEAR_WINDOW,
    VOLATILITY_WINDOW,
)
from app.utils.database import get_connection, initialize_database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetMetadata:
    custom_metric_name: str = "Volatility"
    custom_metric_reason: str = (
        "Volatility captures how unstable a stock's recent returns are, which makes the "
        "dashboard more analytical without adding heavy model complexity."
    )


class DataService:
    def __init__(self) -> None:
        """Initialize dataset metadata and cache containers."""
        self.metadata = DatasetMetadata()
        self._cache: dict[str, pd.DataFrame] = {}
        self._cache_time: dict[str, float] = {}

    def initialize_data(self) -> None:
        """Load all supported symbols into SQLite and in-memory cache."""
        initialize_database()
        yf.set_tz_cache_location(str(DATA_DIR / "yfinance-cache"))
        for symbol in STOCK_SYMBOLS:
            self._refresh_symbol_cache(symbol=symbol)
        self.clear_caches()

    def clear_caches(self) -> None:
        """Clear memoized helper caches."""
        self.list_companies.cache_clear()

    @lru_cache(maxsize=1)
    def list_companies(self) -> list[str]:
        """Return the supported company symbols."""
        return list(STOCK_SYMBOLS.keys())

    def get_stock_frame(self, symbol: str) -> pd.DataFrame:
        """Return a stock frame, refreshing it when the TTL expires."""
        validated_symbol = self._validate_symbol(symbol)
        if self._is_cache_fresh(validated_symbol):
            return self._cache[validated_symbol].copy()

        try:
            return self._refresh_symbol_cache(symbol=validated_symbol).copy()
        except Exception as exc:
            logger.warning(
                "Unable to refresh %s from source, falling back to SQLite snapshot: %s",
                validated_symbol,
                exc,
            )

        with get_connection() as connection:
            frame = pd.read_sql_query(
                """
                SELECT symbol, date, open, high, low, close, volume, daily_return,
                       moving_average_7, high_52_week, low_52_week, volatility_14
                FROM stock_prices
                WHERE symbol = ?
                ORDER BY date ASC
                """,
                connection,
                params=(validated_symbol,),
                parse_dates=["date"],
            )

        if frame.empty:
            raise ValueError(f"No data available for symbol '{validated_symbol}'.")

        frame["date"] = pd.to_datetime(frame["date"])
        self._cache[validated_symbol] = frame
        self._cache_time[validated_symbol] = time.time()
        return frame.copy()

    def _validate_symbol(self, symbol: str) -> str:
        """Validate and normalize a requested stock symbol."""
        normalized_symbol = symbol.upper()
        if normalized_symbol not in STOCK_SYMBOLS:
            raise ValueError(
                f"Unsupported symbol '{symbol}'. Available symbols: {', '.join(STOCK_SYMBOLS.keys())}."
            )
        return normalized_symbol

    def _is_cache_fresh(self, symbol: str) -> bool:
        """Return whether a symbol is still within the configured cache TTL."""
        cached_at = self._cache_time.get(symbol)
        return symbol in self._cache and cached_at is not None and (time.time() - cached_at) <= CACHE_TTL_SECONDS

    def _refresh_symbol_cache(self, symbol: str) -> pd.DataFrame:
        """Fetch, process, persist, and cache one symbol."""
        yf_symbol = STOCK_SYMBOLS[symbol]
        frame = self._fetch_history(symbol=symbol, yf_symbol=yf_symbol)
        try:
            processed_frame = self._process_frame(symbol=symbol, frame=frame)
        except ValueError as exc:
            logger.warning("Processing failed for %s, retrying with mock data: %s", symbol, exc)
            processed_frame = self._process_frame(
                symbol=symbol,
                frame=self._build_mock_history(symbol=symbol, end_date=datetime.utcnow().date()),
            )
        self._persist_frame(symbol=symbol, frame=processed_frame)
        normalized = self._normalize_for_service(processed_frame)
        self._cache[symbol] = normalized
        self._cache_time[symbol] = time.time()
        return normalized

    def _fetch_history(self, symbol: str, yf_symbol: str) -> pd.DataFrame:
        """Fetch historical market data or fall back to deterministic mock data."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=730)

        try:
            history = yf.download(
                yf_symbol,
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                progress=False,
                auto_adjust=False,
                actions=False,
                threads=False,
            )
            if history.empty:
                logger.warning("yfinance returned an empty DataFrame for %s. Using fallback data.", symbol)
                raise ValueError("Received empty dataset from yfinance.")
            logger.info("Fetched %s rows for %s from yfinance.", len(history), symbol)
            return self._prepare_downloaded_history(history.reset_index())
        except Exception as exc:
            logger.warning(
                "Falling back to generated sample data for %s because fetching failed: %s",
                symbol,
                exc,
            )
            return self._build_mock_history(symbol=symbol, end_date=end_date)

    def _build_mock_history(self, symbol: str, end_date: datetime.date) -> pd.DataFrame:
        """Build deterministic fallback price history for offline use."""
        rng = np.random.default_rng(sum(ord(char) for char in symbol))
        dates = pd.bdate_range(end=end_date, periods=520)
        base_price = {"INFY": 1480.0, "TCS": 3920.0, "RELIANCE": 2875.0}[symbol]

        records: list[dict[str, float | int | pd.Timestamp]] = []
        last_close = base_price
        for current_date in dates:
            daily_move = rng.normal(loc=0.0012, scale=0.018)
            open_price = max(last_close * (1 + rng.normal(0.0, 0.004)), 1.0)
            close_price = max(open_price * (1 + daily_move), 1.0)
            high_price = max(open_price, close_price) * (1 + abs(rng.normal(0.003, 0.004)))
            low_price = min(open_price, close_price) * (1 - abs(rng.normal(0.003, 0.004)))
            volume = int(abs(rng.normal(3_000_000, 750_000)))

            records.append(
                {
                    "Date": current_date,
                    "Open": round(open_price, 2),
                    "High": round(high_price, 2),
                    "Low": round(max(low_price, 1.0), 2),
                    "Close": round(close_price, 2),
                    "Volume": volume,
                }
            )
            last_close = close_price

        return pd.DataFrame.from_records(records)

    @staticmethod
    def _prepare_downloaded_history(frame: pd.DataFrame) -> pd.DataFrame:
        """Flatten yfinance output into a predictable single-level schema."""
        prepared = frame.copy()
        if isinstance(prepared.columns, pd.MultiIndex):
            prepared.columns = [
                level_0 if level_0 == "Date" else str(level_0)
                for level_0, _ in prepared.columns.to_flat_index()
            ]
        else:
            prepared.columns = [str(column) for column in prepared.columns]

        if "Adj Close" in prepared.columns and "Close" in prepared.columns:
            prepared = prepared.drop(columns=["Adj Close"])

        return prepared

    def _process_frame(self, symbol: str, frame: pd.DataFrame) -> pd.DataFrame:
        """Clean and enrich raw stock history into the service schema."""
        processed = frame.rename(columns=str.title).copy()
        if "Date" not in processed.columns:
            raise ValueError(f"Missing Date column for {symbol}.")
        processed["Date"] = pd.to_datetime(processed["Date"], errors="coerce")
        processed = processed.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

        numeric_columns = ["Open", "High", "Low", "Close", "Volume"]
        for column in numeric_columns:
            processed[column] = pd.to_numeric(processed[column], errors="coerce")

        # Forward-filling preserves continuity for technical indicators when a source row has gaps.
        processed[numeric_columns] = processed[numeric_columns].ffill()
        processed = self._drop_empty_columns(processed, numeric_columns)
        missing_required = [column for column in numeric_columns if column not in processed.columns]
        if missing_required:
            raise ValueError(f"Missing required numeric columns after cleaning: {', '.join(missing_required)}.")
        processed = processed.dropna(subset=numeric_columns)

        processed["Daily Return"] = np.where(
            processed["Open"] != 0,
            (processed["Close"] - processed["Open"]) / processed["Open"],
            0.0,
        )
        processed["7-Day Moving Average"] = (
            processed["Close"].rolling(window=MOVING_AVERAGE_WINDOW, min_periods=1).mean()
        )
        processed["52-Week High"] = (
            processed["Close"].rolling(window=TRADING_YEAR_WINDOW, min_periods=1).max()
        )
        processed["52-Week Low"] = (
            processed["Close"].rolling(window=TRADING_YEAR_WINDOW, min_periods=1).min()
        )
        processed["Volatility 14"] = (
            processed["Daily Return"].rolling(window=VOLATILITY_WINDOW, min_periods=2).std()
        )

        processed["Symbol"] = symbol
        processed["Volume"] = processed["Volume"].astype(int)

        return processed[
            [
                "Symbol",
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Daily Return",
                "7-Day Moving Average",
                "52-Week High",
                "52-Week Low",
                "Volatility 14",
            ]
        ].reset_index(drop=True)

    def _drop_empty_columns(self, frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Drop columns that remain fully null after forward-fill and log the change."""
        cleaned = frame.copy()
        for column in columns:
            if column in cleaned.columns and cleaned[column].isna().all():
                logger.warning("Dropping entirely empty column '%s' after forward-fill.", column)
                cleaned = cleaned.drop(columns=[column])
        return cleaned

    def _persist_frame(self, symbol: str, frame: pd.DataFrame) -> None:
        """Persist a processed stock frame into SQLite."""
        database_frame = self._normalize_for_service(frame)
        database_frame["date"] = database_frame["date"].dt.strftime("%Y-%m-%d")

        with get_connection() as connection:
            connection.execute("DELETE FROM stock_prices WHERE symbol = ?", (symbol,))
            database_frame.to_sql("stock_prices", connection, if_exists="append", index=False)
            connection.commit()

    @staticmethod
    def _normalize_for_service(frame: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to the API service convention."""
        return frame.rename(
            columns={
                "Symbol": "symbol",
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Daily Return": "daily_return",
                "7-Day Moving Average": "moving_average_7",
                "52-Week High": "high_52_week",
                "52-Week Low": "low_52_week",
                "Volatility 14": "volatility_14",
            }
        ).copy()


data_service = DataService()
