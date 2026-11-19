"""Every error leaves the API in one shape, with a reference id and no internal details."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError

log = logging.getLogger("app.api")


def new_reference() -> str:
    return uuid.uuid4().hex[:8]


def error_body(code: str, message: str, reference: str) -> dict:
    return {"error": {"code": code, "message": message, "reference": reference}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message, new_reference()),
                            status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            error_body("invalid_request", "The request is missing fields or has wrong values.",
                       new_reference()),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        reference = new_reference()
        log.exception("Unhandled error, reference %s", reference)
        return JSONResponse(
            error_body("internal_error", "Something went wrong. Please try again.", reference),
            status_code=500,
        )
