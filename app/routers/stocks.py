from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.models.stock import (
    CompanyListResponse,
    CompareResponse,
    ErrorResponse,
    PredictionResponse,
    StockDataResponse,
    StockSummaryResponse,
    TopMoversResponse,
)
from app.services.stock_service import stock_service
from app.utils.constants import DEFAULT_LOOKBACK_DAYS
from app.utils.errors import error_response

router = APIRouter(tags=["Stocks"])


def raise_api_error(message: str, status_code: int) -> None:
    """Raise a standardized HTTPException payload."""
    raise HTTPException(status_code=status_code, detail=error_response(message, status_code))


@router.get(
    "/companies",
    response_model=CompanyListResponse,
    summary="List available companies",
    description="Return all stock symbols currently supported by the dashboard data pipeline.",
    response_description="A list of supported stock symbols.",
    responses={
        200: {
            "description": "Successfully returned the supported companies.",
            "content": {"application/json": {"example": {"companies": ["INFY", "TCS", "RELIANCE"]}}},
        },
        500: {"model": ErrorResponse},
    },
)
async def get_companies() -> CompanyListResponse:
    """Return all available company symbols."""
    return CompanyListResponse(companies=stock_service.get_companies())


@router.get(
    "/data/{symbol}",
    response_model=StockDataResponse,
    summary="Get stock data",
    description=(
        "Return the latest processed stock rows for a symbol.\n\n"
        "The response includes OHLCV values, daily return, the 7-day moving average, "
        "and the 14-day volatility metric."
    ),
    response_description="Processed stock data for the requested symbol and lookback period.",
    responses={
        200: {
            "description": "Successfully returned the processed stock rows.",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "INFY",
                        "metric": "Volatility (14-day rolling standard deviation)",
                        "days": 30,
                        "records": [
                            {
                                "date": "2026-03-30",
                                "open": 1498.2,
                                "high": 1512.5,
                                "low": 1488.1,
                                "close": 1507.8,
                                "volume": 12890334,
                                "daily_return": 0.006408,
                                "moving_average_7": 1492.47,
                                "volatility_14": 0.013521,
                            }
                        ],
                        "warning": None,
                    }
                }
            },
        },
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_stock_data(
    symbol: str,
    days: int = Query(DEFAULT_LOOKBACK_DAYS, description="Supported values: 7, 30, 90."),
) -> StockDataResponse:
    """Return processed stock data rows for one symbol."""
    try:
        return StockDataResponse(**stock_service.get_stock_data(symbol=symbol, days=days))
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "symbol" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise_api_error(str(exc), status_code)


@router.get(
    "/summary/{symbol}",
    response_model=StockSummaryResponse,
    summary="Get stock summary",
    description=(
        "Return summary statistics for a symbol, including 52-week range, average close, "
        "latest close, and the most recent volatility value."
    ),
    response_description="Summary metrics for the requested symbol.",
    responses={
        200: {
            "description": "Successfully returned summary statistics.",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "TCS",
                        "high_52_week": 4398.4,
                        "low_52_week": 3477.85,
                        "average_closing_price": 3921.11,
                        "latest_close": 4014.65,
                        "custom_metric_name": "Volatility",
                        "latest_custom_metric_value": 0.011245,
                    }
                }
            },
        },
        404: {"model": ErrorResponse},
    },
)
async def get_summary(symbol: str) -> StockSummaryResponse:
    """Return summary analytics for one symbol."""
    try:
        return StockSummaryResponse(**stock_service.get_summary(symbol=symbol))
    except ValueError as exc:
        raise_api_error(str(exc), status.HTTP_404_NOT_FOUND)


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare two stocks",
    description=(
        "Compare two different stock symbols over the selected lookback window. "
        "The response includes normalized price series and daily return trends."
    ),
    response_description="Normalized comparison data for two stocks.",
    responses={
        200: {
            "description": "Successfully returned normalized comparison data.",
            "content": {
                "application/json": {
                    "example": {
                        "symbol1": "INFY",
                        "symbol2": "RELIANCE",
                        "basis": "Normalized close indexed to 100 on the first overlapping day.",
                        "records": [
                            {
                                "date": "2026-03-30",
                                "normalized_close_symbol1": 101.2457,
                                "normalized_close_symbol2": 99.8872,
                                "daily_return_symbol1": 0.008734,
                                "daily_return_symbol2": -0.002418,
                            }
                        ],
                    }
                }
            },
        },
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def compare_stocks(
    symbol1: str = Query(..., description="The first stock symbol."),
    symbol2: str = Query(..., description="The second stock symbol."),
    days: int = Query(DEFAULT_LOOKBACK_DAYS, description="Supported values: 7, 30, 90."),
) -> CompareResponse:
    """Return a comparison between two different symbols."""
    try:
        return CompareResponse(**stock_service.compare_stocks(symbol1=symbol1, symbol2=symbol2, days=days))
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "symbol" in message.lower() and "different" not in message.lower() else status.HTTP_400_BAD_REQUEST
        raise_api_error(message, status_code)


@router.get(
    "/top-movers",
    response_model=TopMoversResponse,
    summary="Get top movers",
    description=(
        "Return the top gainers and losers based on the latest available daily return for each symbol. "
        "If fewer than three symbols are available, the endpoint returns all available entries."
    ),
    response_description="Top gainers and losers ranked by the latest daily return.",
    responses={
        200: {
            "description": "Successfully returned top movers.",
            "content": {
                "application/json": {
                    "example": {
                        "gainers": [{"symbol": "INFY", "return": 0.023}],
                        "losers": [{"symbol": "TCS", "return": -0.018}],
                    }
                }
            },
        },
        500: {"model": ErrorResponse},
    },
)
async def get_top_movers() -> TopMoversResponse:
    """Return the latest gainers and losers across tracked stocks."""
    return TopMoversResponse(**stock_service.get_top_movers())


@router.get(
    "/predict/{symbol}",
    response_model=PredictionResponse,
    summary="Predict future prices",
    description=(
        "Train a linear regression model on the last 90 days of closing prices, or all available data if fewer rows exist, "
        "and predict the next 7 closing prices."
    ),
    response_description="Seven forward-looking closing-price predictions.",
    responses={
        200: {
            "description": "Successfully returned linear regression price predictions.",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "INFY",
                        "predictions": [
                            {"date": "2026-03-31", "predicted_price": 1520.45},
                            {"date": "2026-04-01", "predicted_price": 1533.12},
                        ],
                    }
                }
            },
        },
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def predict_prices(symbol: str) -> PredictionResponse:
    """Return linear regression price predictions for one symbol."""
    try:
        return PredictionResponse(**stock_service.predict_prices(symbol=symbol))
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "symbol" in message.lower() and "insufficient" not in message.lower() else status.HTTP_400_BAD_REQUEST
        raise_api_error(message, status_code)
