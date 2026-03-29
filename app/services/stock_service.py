from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.linear_model import LinearRegression

from app.services.data_service import data_service
from app.utils.constants import (
    ALLOWED_LOOKBACK_DAYS,
    DEFAULT_LOOKBACK_DAYS,
    MIN_PREDICTION_POINTS,
    PREDICTION_FORECAST_DAYS,
    PREDICTION_TRAINING_WINDOW,
    TOP_MOVERS_LIMIT,
)


class StockService:
    """Provide stock analytics operations for router handlers."""

    def get_companies(self) -> list[str]:
        """Return the supported stock symbols."""
        return data_service.list_companies()

    def get_stock_data(self, symbol: str, days: int = DEFAULT_LOOKBACK_DAYS) -> dict[str, Any]:
        """Return processed stock rows for the requested lookback window."""
        validated_days = self._validate_days(days)
        normalized_symbol, frame = self._load_symbol_frame(symbol)
        records = frame.tail(validated_days).copy()
        warning = None
        if records.empty:
            warning = "No data for this period"

        return {
            "symbol": normalized_symbol,
            "metric": f"{data_service.metadata.custom_metric_name} (14-day rolling standard deviation)",
            "days": validated_days,
            "records": [] if records.empty else [
                {
                    "date": row["date"].date(),
                    "open": round(float(row["open"]), 2),
                    "high": round(float(row["high"]), 2),
                    "low": round(float(row["low"]), 2),
                    "close": round(float(row["close"]), 2),
                    "volume": int(row["volume"]),
                    "daily_return": round(float(row["daily_return"]), 6),
                    "moving_average_7": self._optional_round(row["moving_average_7"]),
                    "volatility_14": self._optional_round(row["volatility_14"], 6),
                }
                for _, row in records.iterrows()
            ],
            "warning": warning,
        }

    def get_summary(self, symbol: str) -> dict[str, Any]:
        """Return high-level stock summary metrics."""
        normalized_symbol, frame = self._load_symbol_frame(symbol)
        latest_row = frame.iloc[-1]

        return {
            "symbol": normalized_symbol,
            "high_52_week": round(float(frame["high_52_week"].max()), 2),
            "low_52_week": round(float(frame["low_52_week"].min()), 2),
            "average_closing_price": round(float(frame["close"].mean()), 2),
            "latest_close": round(float(latest_row["close"]), 2),
            "custom_metric_name": data_service.metadata.custom_metric_name,
            "latest_custom_metric_value": self._optional_round(latest_row["volatility_14"], 6),
        }

    def compare_stocks(self, symbol1: str, symbol2: str, days: int = DEFAULT_LOOKBACK_DAYS) -> dict[str, Any]:
        """Return normalized side-by-side stock comparison data."""
        if symbol1.upper() == symbol2.upper():
            raise ValueError("symbol1 and symbol2 must be different")
        validated_days = self._validate_days(days)
        normalized_symbol1, left_frame = self._load_symbol_frame(symbol1)
        normalized_symbol2, right_frame = self._load_symbol_frame(symbol2)
        left = left_frame.tail(validated_days).copy()
        right = right_frame.tail(validated_days).copy()

        comparison = pd.merge(
            left[["date", "close", "daily_return"]],
            right[["date", "close", "daily_return"]],
            on="date",
            how="inner",
            suffixes=("_symbol1", "_symbol2"),
        )
        if comparison.empty:
            raise ValueError("No overlapping comparison data found for the selected symbols.")

        comparison["normalized_close_symbol1"] = (
            comparison["close_symbol1"] / comparison["close_symbol1"].iloc[0]
        ) * 100
        comparison["normalized_close_symbol2"] = (
            comparison["close_symbol2"] / comparison["close_symbol2"].iloc[0]
        ) * 100

        return {
            "symbol1": normalized_symbol1,
            "symbol2": normalized_symbol2,
            "basis": "Normalized close indexed to 100 on the first overlapping day.",
            "records": [
                {
                    "date": row["date"].date(),
                    "normalized_close_symbol1": round(float(row["normalized_close_symbol1"]), 4),
                    "normalized_close_symbol2": round(float(row["normalized_close_symbol2"]), 4),
                    "daily_return_symbol1": round(float(row["daily_return_symbol1"]), 6),
                    "daily_return_symbol2": round(float(row["daily_return_symbol2"]), 6),
                }
                for _, row in comparison.iterrows()
            ],
        }

    def get_top_movers(self) -> dict[str, Any]:
        """Return the latest top gainers and losers across loaded symbols."""
        rows: list[dict[str, Any]] = []
        for symbol in self.get_companies():
            _, frame = self._load_symbol_frame(symbol)
            latest_row = frame.iloc[-1]
            rows.append(
                {
                    "symbol": symbol,
                    "return": round(float(latest_row["daily_return"]), 6),
                }
            )

        mover_frame = pd.DataFrame(rows)
        gainers = mover_frame.sort_values("return", ascending=False).head(TOP_MOVERS_LIMIT)
        losers = mover_frame.sort_values("return", ascending=True).head(TOP_MOVERS_LIMIT)
        return {
            "gainers": gainers.to_dict(orient="records"),
            "losers": losers.to_dict(orient="records"),
        }

    def predict_prices(self, symbol: str) -> dict[str, Any]:
        """Predict the next closing prices using linear regression."""
        normalized_symbol, frame = self._load_symbol_frame(symbol)
        training_frame = frame.tail(PREDICTION_TRAINING_WINDOW).copy()
        if len(training_frame) < MIN_PREDICTION_POINTS:
            raise ValueError("Insufficient data for prediction")

        indices = list(range(len(training_frame)))
        model = LinearRegression()
        model.fit(pd.DataFrame({"day_index": indices}), training_frame["close"])

        future_indices = list(range(len(training_frame), len(training_frame) + PREDICTION_FORECAST_DAYS))
        predictions = model.predict(pd.DataFrame({"day_index": future_indices}))
        last_date = training_frame["date"].iloc[-1]
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=PREDICTION_FORECAST_DAYS)

        return {
            "symbol": normalized_symbol,
            "predictions": [
                {
                    "date": forecast_date.date(),
                    "predicted_price": round(float(prediction), 2),
                }
                for forecast_date, prediction in zip(future_dates, predictions)
            ],
        }

    def _load_symbol_frame(self, symbol: str) -> tuple[str, pd.DataFrame]:
        """Load and validate a symbol-specific DataFrame."""
        normalized_symbol = symbol.upper()
        if normalized_symbol not in self.get_companies():
            raise ValueError(f"Symbol '{normalized_symbol}' was not found in loaded data.")
        frame = data_service.get_stock_frame(normalized_symbol)
        if frame.empty:
            raise ValueError(f"No data available for symbol '{normalized_symbol}'.")
        return normalized_symbol, frame

    def _validate_days(self, days: int) -> int:
        """Validate supported dashboard day filters."""
        if days not in ALLOWED_LOOKBACK_DAYS:
            raise ValueError(
                f"Unsupported day filter '{days}'. Allowed values: {sorted(ALLOWED_LOOKBACK_DAYS)}."
            )
        return days

    @staticmethod
    def _optional_round(value: Any, digits: int = 2) -> float | None:
        """Round optional numeric values while preserving nulls."""
        if pd.isna(value):
            return None
        return round(float(value), digits)


stock_service = StockService()
