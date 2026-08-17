"""Tests for agent management endpoints."""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.domain_models.agent import Agent, AgentStatus


class TestAgentCreation:
    """Tests for creating agents."""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, client: AsyncClient, developer_token: str) -> None:
        """Test successful agent creation."""
        response = await client.post(
            "/agents/",
            json={
                "name": "Test Agent",
                "description": "A test agent",
                "agent_type": "hr",
                "capabilities": {"actions": ["test"]},
                "configuration": {"runtime": "python", "resources": {"memory_mb": 256}},
                "version": "1.0.0",
                "owner_id": "00000000-0000-0000-0000-000000000000",  # Will be overridden
                "tags": ["test"],
            },
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Agent"
        assert data["status"] == "draft"
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_create_agent_unauthorized(self, client: AsyncClient) -> None:
        """Test agent creation without authentication."""
        response = await client.post(
            "/agents/",
            json={
                "name": "Test Agent",
                "description": "A test agent",
                "agent_type": "hr",
                "capabilities": {},
                "configuration": {},
                "version": "1.0.0",
                "owner_id": "00000000-0000-0000-0000-000000000000",
                "tags": [],
            },
        )

        assert response.status_code == 401


class TestAgentListing:
    """Tests for listing agents."""

    @pytest.mark.asyncio
    async def test_list_agents_as_admin(
        self, client: AsyncClient, admin_token: str, sample_agent: Agent
    ) -> None:
        """Test admin can list all agents."""
        response = await client.get("/agents/", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_agents_filter_by_status(
        self, client: AsyncClient, admin_token: str, sample_agent: Agent
    ) -> None:
        """Test filtering agents by status."""
        response = await client.get(
            "/agents/?status_filter=draft",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for agent in data:
            assert agent["status"] == "draft"


class TestAgentApproval:
    """Tests for agent approval workflow."""

    @pytest.mark.asyncio
    async def test_submit_for_approval(
        self,
        client: AsyncClient,
        developer_token: str,
        sample_agent: Agent,
    ) -> None:
        """Test submitting agent for approval."""
        response = await client.post(
            f"/agents/{sample_agent.id}/submit-approval",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"

    @pytest.mark.asyncio
    async def test_approve_agent(
        self, client: AsyncClient, admin_token: str, session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test agent approval by admin."""
        # First submit for approval
        sample_agent.status = AgentStatus.PENDING_APPROVAL
        session.add(sample_agent)
        await session.commit()

        response = await client.post(
            f"/agents/{sample_agent.id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by_id"] is not None

    @pytest.mark.asyncio
    async def test_approve_agent_insufficient_permissions(
        self, client: AsyncClient, developer_token: str, session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test non-admin cannot approve agents."""
        sample_agent.status = AgentStatus.PENDING_APPROVAL
        session.add(sample_agent)
        await session.commit()

        response = await client.post(
            f"/agents/{sample_agent.id}/approve",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 403


class TestAgentUpdate:
    """Tests for updating agents."""

    @pytest.mark.asyncio
    async def test_update_draft_agent(
        self, client: AsyncClient, developer_token: str, sample_agent: Agent
    ) -> None:
        """Test updating a draft agent."""
        response = await client.patch(
            f"/agents/{sample_agent.id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_cannot_update_deployed_agent(
        self, client: AsyncClient, developer_token: str, session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test cannot update deployed agents."""
        sample_agent.status = AgentStatus.DEPLOYED
        session.add(sample_agent)
        await session.commit()

        response = await client.patch(
            f"/agents/{sample_agent.id}",
            json={"description": "Should fail"},
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 400


class TestAgentDeletion:
    """Tests for archiving agents."""

    @pytest.mark.asyncio
    async def test_archive_agent(
        self, client: AsyncClient, developer_token: str, sample_agent: Agent
    ) -> None:
        """Test archiving an agent."""
        response = await client.delete(
            f"/agents/{sample_agent.id}",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_cannot_delete_deployed_agent(
        self, client: AsyncClient, developer_token: str, session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test cannot delete deployed agents."""
        sample_agent.status = AgentStatus.DEPLOYED
        session.add(sample_agent)
        await session.commit()

        response = await client.delete(
            f"/agents/{sample_agent.id}",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 400
