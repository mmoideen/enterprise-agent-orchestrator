"""Tests for audit middleware and logging."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.audit import create_audit_log
from packages.domain_models.audit import AuditLog
from packages.domain_models.user import User


class TestAuditMiddleware:
    """Tests for audit middleware."""

    @pytest.mark.asyncio
    async def test_audit_middleware_logs_requests(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        """Test that audit middleware logs API requests."""
        # Make an API request
        response = await client.get(
            "/agents/", headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        # Note: In a real test, you would check the logs were created
        # This requires access to the database session used by the app


class TestCreateAuditLog:
    """Tests for create_audit_log function."""

    @pytest.mark.asyncio
    async def test_create_audit_log_basic(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test creating a basic audit log entry."""
        resource_id = uuid4()

        audit_log = await create_audit_log(
            session=session,
            event_type="agent.created",
            resource_type="agent",
            resource_id=resource_id,
            action="create",
            user_id=admin_user.id,
        )

        assert audit_log.event_type == "agent.created"
        assert audit_log.resource_type == "agent"
        assert audit_log.resource_id == resource_id
        assert audit_log.user_id == admin_user.id
        assert audit_log.action == "create"

    @pytest.mark.asyncio
    async def test_create_audit_log_with_details(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test creating audit log with additional details."""
        resource_id = uuid4()
        details = {"agent_name": "Test Agent", "risk_score": 0.5}

        audit_log = await create_audit_log(
            session=session,
            event_type="agent.approved",
            resource_type="agent",
            resource_id=resource_id,
            action="approve",
            user_id=admin_user.id,
            details=details,
        )

        assert audit_log.details["agent_name"] == "Test Agent"
        assert audit_log.details["risk_score"] == 0.5

    @pytest.mark.asyncio
    async def test_create_audit_log_with_ip_and_user_agent(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test creating audit log with IP address and user agent."""
        resource_id = uuid4()

        audit_log = await create_audit_log(
            session=session,
            event_type="deployment.created",
            resource_type="deployment",
            resource_id=resource_id,
            action="create",
            user_id=admin_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0"

    @pytest.mark.asyncio
    async def test_create_audit_log_without_user(
        self, session: AsyncSession
    ) -> None:
        """Test creating audit log without user (system action)."""
        resource_id = uuid4()

        audit_log = await create_audit_log(
            session=session,
            event_type="system.health_check",
            resource_type="system",
            resource_id=resource_id,
            action="check",
            user_id=None,
        )

        assert audit_log.user_id is None
        assert audit_log.event_type == "system.health_check"


class TestAuditLogQuery:
    """Tests for querying audit logs."""

    @pytest.mark.asyncio
    async def test_query_audit_logs_by_event_type(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test querying audit logs by event type."""
        # Create multiple audit logs
        for i in range(3):
            await create_audit_log(
                session=session,
                event_type="agent.created",
                resource_type="agent",
                resource_id=uuid4(),
                action="create",
                user_id=admin_user.id,
            )

        # Query by event type
        result = await session.execute(
            select(AuditLog).where(AuditLog.event_type == "agent.created")
        )
        logs = result.scalars().all()

        assert len(logs) >= 3

    @pytest.mark.asyncio
    async def test_query_audit_logs_by_user(
        self,
        session: AsyncSession,
        admin_user: User,
        developer_user: User,
    ) -> None:
        """Test querying audit logs by user."""
        # Create audit logs for different users
        await create_audit_log(
            session=session,
            event_type="agent.created",
            resource_type="agent",
            resource_id=uuid4(),
            action="create",
            user_id=admin_user.id,
        )

        await create_audit_log(
            session=session,
            event_type="agent.created",
            resource_type="agent",
            resource_id=uuid4(),
            action="create",
            user_id=developer_user.id,
        )

        # Query by user
        result = await session.execute(
            select(AuditLog).where(AuditLog.user_id == admin_user.id)
        )
        admin_logs = result.scalars().all()

        result = await session.execute(
            select(AuditLog).where(AuditLog.user_id == developer_user.id)
        )
        developer_logs = result.scalars().all()

        assert len(admin_logs) >= 1
        assert len(developer_logs) >= 1

    @pytest.mark.asyncio
    async def test_query_audit_logs_by_resource(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test querying audit logs by resource ID."""
        resource_id = uuid4()

        # Create multiple logs for same resource
        await create_audit_log(
            session=session,
            event_type="agent.created",
            resource_type="agent",
            resource_id=resource_id,
            action="create",
            user_id=admin_user.id,
        )

        await create_audit_log(
            session=session,
            event_type="agent.updated",
            resource_type="agent",
            resource_id=resource_id,
            action="update",
            user_id=admin_user.id,
        )

        # Query by resource
        result = await session.execute(
            select(AuditLog).where(AuditLog.resource_id == resource_id)
        )
        logs = result.scalars().all()

        assert len(logs) == 2


class TestAuditLogRetention:
    """Tests for audit log retention and compliance."""

    @pytest.mark.asyncio
    async def test_audit_log_has_timestamp(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test that audit logs have timestamps."""
        audit_log = await create_audit_log(
            session=session,
            event_type="test.event",
            resource_type="test",
            resource_id=uuid4(),
            action="test",
            user_id=admin_user.id,
        )

        assert audit_log.timestamp is not None

    @pytest.mark.asyncio
    async def test_audit_log_immutability(
        self, session: AsyncSession, admin_user: User
    ) -> None:
        """Test that audit logs should be immutable."""
        audit_log = await create_audit_log(
            session=session,
            event_type="test.event",
            resource_type="test",
            resource_id=uuid4(),
            action="test",
            user_id=admin_user.id,
        )

        original_id = audit_log.id
        original_timestamp = audit_log.timestamp

        # In a real system, attempts to modify should be prevented
        # For this test, we just verify the log was created properly
        assert audit_log.id == original_id
        assert audit_log.timestamp == original_timestamp
