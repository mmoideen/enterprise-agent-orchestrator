"""Audit logging middleware and utilities."""

from typing import Any, Callable
from uuid import UUID

import structlog
from fastapi import Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from packages.domain_models.audit import AuditLog


logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for auditing all API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log audit information.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response.
        """
        # Skip audit logging for health checks and non-mutating operations
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Extract user info if available
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.id

        # Log request
        logger.info(
            "api_request",
            method=request.method,
            path=request.url.path,
            user_id=str(user_id) if user_id else None,
            client_ip=request.client.host if request.client else None,
        )

        response = await call_next(request)

        # Log response
        logger.info(
            "api_response",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            user_id=str(user_id) if user_id else None,
        )

        return response


async def create_audit_log(
    session: AsyncSession,
    event_type: str,
    resource_type: str,
    resource_id: UUID,
    action: str,
    user_id: UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        session: Database session.
        event_type: Type of event (e.g., "agent.created").
        resource_type: Type of resource (e.g., "agent").
        resource_id: ID of the resource.
        action: Action performed (e.g., "create").
        user_id: Optional user ID.
        details: Optional additional details.
        ip_address: Optional client IP address.
        user_agent: Optional client user agent.

    Returns:
        Created audit log entry.
    """
    audit_log = AuditLog(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    session.add(audit_log)
    await session.commit()
    await session.refresh(audit_log)

    logger.info(
        "audit_log_created",
        event_type=event_type,
        resource_type=resource_type,
        resource_id=str(resource_id),
        action=action,
    )

    return audit_log
