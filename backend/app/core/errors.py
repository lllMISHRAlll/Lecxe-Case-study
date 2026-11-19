"""Errors the app raises on purpose. The API turns them into the standard error shape."""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    message = "The request could not be processed."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class Unauthenticated(AppError):
    status_code = 401
    code = "unauthenticated"
    message = "Please sign in."


class InvalidCredentials(AppError):
    status_code = 401
    code = "invalid_credentials"
    message = "Email or password is incorrect."


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    message = "Your role can't do that."


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    message = "Not found."


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please wait a moment and try again."
