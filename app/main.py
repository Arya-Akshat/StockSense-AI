from __future__ import annotations

import logging
import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers.stocks import router as stock_router
from app.services.data_service import data_service
from app.utils.constants import DEFAULT_HOST, DEFAULT_PORT, GENERIC_API_ERROR_MESSAGE
from app.utils.errors import error_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = os.getenv("HOST", DEFAULT_HOST)
PORT = int(os.getenv("PORT", DEFAULT_PORT))


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load stock data before the application starts serving traffic."""
    data_service.initialize_data()
    yield


app = FastAPI(
    title="Stock Data Intelligence Platform",
    version="1.1.0",
    description=(
        "Production-ready FastAPI service for ingesting NSE stock data, enriching it with analytics, "
        "serving documented APIs, and powering a Chart.js dashboard."
    ),
    contact={"name": "Internship Project Maintainer", "email": "maintainer@example.com"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Return standardized JSON for HTTP exceptions."""
    detail = exc.detail if isinstance(exc.detail, dict) else error_response(str(exc.detail), exc.status_code)
    logger.error("HTTPException encountered: %s", detail)
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return standardized JSON for unhandled exceptions."""
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(GENERIC_API_ERROR_MESSAGE, status.HTTP_500_INTERNAL_SERVER_ERROR),
    )


@app.get("/", include_in_schema=False)
async def serve_dashboard() -> FileResponse:
    """Serve the dashboard single page application."""
    return FileResponse(STATIC_DIR / "index.html")
