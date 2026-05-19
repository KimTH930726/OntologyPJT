"""Centralized domain exception hierarchy.

Application services raise these; API routes translate them into HTTP errors.
Keeping a single root makes consistent error envelopes trivial.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for all domain/application errors."""

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 400


class ConflictError(DomainError):
    code = "CONFLICT"
    http_status = 409


class IntegrationError(DomainError):
    """External system (Neo4j, Qdrant, LLM) failure."""

    code = "INTEGRATION_ERROR"
    http_status = 502
