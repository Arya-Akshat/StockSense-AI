from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class CompanyListResponse(BaseModel):
    """Return the supported company symbols."""

    companies: List[str]


class StockDataPoint(BaseModel):
    """Represent one processed stock data row."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    daily_return: float = Field(..., description="Daily return computed as (Close - Open) / Open.")
    moving_average_7: float | None = Field(None, description="7-day moving average of close price.")
    volatility_14: float | None = Field(
        None,
        description="14-day rolling standard deviation of daily returns.",
    )


class StockDataResponse(BaseModel):
    """Return stock data for a selected symbol and lookback window."""

    symbol: str
    metric: str
    days: int
    records: List[StockDataPoint]
    warning: str | None = None


class StockSummaryResponse(BaseModel):
    """Return summary metrics for a stock symbol."""

    symbol: str
    high_52_week: float
    low_52_week: float
    average_closing_price: float
    latest_close: float
    custom_metric_name: str
    latest_custom_metric_value: float | None


class ComparisonPoint(BaseModel):
    """Represent one normalized comparison row."""

    date: date
    normalized_close_symbol1: float
    normalized_close_symbol2: float
    daily_return_symbol1: float
    daily_return_symbol2: float


class CompareResponse(BaseModel):
    """Return a side-by-side comparison between two stocks."""

    symbol1: str
    symbol2: str
    basis: str
    records: List[ComparisonPoint]


class TopMoverItem(BaseModel):
    """Represent a gainer or loser item."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    return_value: float = Field(..., alias="return", serialization_alias="return")


class TopMoversResponse(BaseModel):
    """Return the strongest and weakest latest movers."""

    gainers: List[TopMoverItem]
    losers: List[TopMoverItem]


class PredictionPoint(BaseModel):
    """Represent one predicted price point."""

    date: date
    predicted_price: float


class PredictionResponse(BaseModel):
    """Return forward-looking linear regression predictions."""

    symbol: str
    predictions: List[PredictionPoint]


class ErrorResponse(BaseModel):
    """Return a standardized error payload."""

    error: str
    status: int
