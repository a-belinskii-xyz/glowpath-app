from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class AppError(Exception):
    """Domain error with a stable machine-readable code for API clients."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 400,
        params: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.params = dict(params) if params else {}


def error_detail(exc: AppError) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.params:
        detail["params"] = exc.params
    return detail


def structured_detail(
    *,
    code: str,
    message: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if params:
        detail["params"] = params
    return detail


def raise_http_error(exc: AppError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=error_detail(exc)) from exc
