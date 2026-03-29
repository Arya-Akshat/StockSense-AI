from __future__ import annotations


def error_response(message: str, status: int) -> dict[str, int | str]:
    """Build a consistent API error payload."""
    return {"error": message, "status": status}
