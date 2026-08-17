"""Tests for deployment management endpoints."""

import pytest
from httpx import AsyncClient

from packages.domain_models.agent import Agent


class TestDeploymentCreation:
    """Tests for creating deployments."""

    @pytest.mark.asyncio
    async def test_create_deployment_success(
        self,
        client: AsyncClient,
        developer_token: str,
        approved_agent: Agent,
    ) -> None:
        """Test successful deployment creation."""
        deployment_data = {
            "agent_id": str(approved_agent.id),
            "environment": "staging",
            "configuration": {"replicas": 1},
            "triggered_by_id": "placeholder",
        }

        response = await client.post(
            "/deployments/",
            json=deployment_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == str(approved_agent.id)
        assert data["environment"] == "staging"
        assert data["status"] in ["pending", "running"]
        assert "workflow_id" in data

    @pytest.mark.asyncio
    async def test_cannot_deploy_unapproved_agent(
        self,
        client: AsyncClient,
        developer_token: str,
        sample_agent: Agent,
    ) -> None:
        """Test that unapproved agents cannot be deployed."""
        deployment_data = {
            "agent_id": str(sample_agent.id),
            "environment": "staging",
            "configuration": {},
            "triggered_by_id": "placeholder",
        }

        response = await client.post(
            "/deployments/",
            json=deployment_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_deployment_without_authentication(
        self, client: AsyncClient, approved_agent: Agent
    ) -> None:
        """Test deployment creation without authentication."""
        deployment_data = {
            "agent_id": str(approved_agent.id),
            "environment": "staging",
            "configuration": {},
            "triggered_by_id": "placeholder",
        }

        response = await client.post("/deployments/", json=deployment_data)

        assert response.status_code == 401


class TestDeploymentListing:
    """Tests for listing deployments."""

    @pytest.mark.asyncio
    async def test_list_deployments(
        self,
        client: AsyncClient,
        admin_token: str,
    ) -> None:
        """Test listing deployments."""
        response = await client.get(
            "/deployments/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_filter_deployments_by_agent(
        self,
        client: AsyncClient,
        admin_token: str,
        approved_agent: Agent,
    ) -> None:
        """Test filtering deployments by agent ID."""
        response = await client.get(
            f"/deployments/?agent_id={approved_agent.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_filter_deployments_by_environment(
        self,
        client: AsyncClient,
        admin_token: str,
    ) -> None:
        """Test filtering deployments by environment."""
        response = await client.get(
            "/deployments/?environment=staging",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDeploymentRetrieval:
    """Tests for retrieving individual deployments."""

    @pytest.mark.asyncio
    async def test_get_deployment(
        self,
        client: AsyncClient,
        developer_token: str,
        approved_agent: Agent,
    ) -> None:
        """Test retrieving a specific deployment."""
        # First create a deployment
        deployment_data = {
            "agent_id": str(approved_agent.id),
            "environment": "staging",
            "configuration": {},
            "triggered_by_id": "placeholder",
        }

        create_response = await client.post(
            "/deployments/",
            json=deployment_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert create_response.status_code == 201
        deployment_id = create_response.json()["id"]

        # Now retrieve it
        get_response = await client.get(
            f"/deployments/{deployment_id}",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == deployment_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_deployment(
        self,
        client: AsyncClient,
        developer_token: str,
    ) -> None:
        """Test retrieving a deployment that doesn't exist."""
        from uuid import uuid4

        fake_id = str(uuid4())

        response = await client.get(
            f"/deployments/{fake_id}",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 404


class TestDeploymentRollback:
    """Tests for deployment rollback."""

    @pytest.mark.asyncio
    async def test_rollback_deployment(
        self,
        client: AsyncClient,
        admin_token: str,
        developer_token: str,
        approved_agent: Agent,
    ) -> None:
        """Test rolling back a deployment."""
        # Create a deployment
        deployment_data = {
            "agent_id": str(approved_agent.id),
            "environment": "staging",
            "configuration": {},
            "triggered_by_id": "placeholder",
        }

        create_response = await client.post(
            "/deployments/",
            json=deployment_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        deployment_id = create_response.json()["id"]

        # Rollback the deployment (requires admin)
        rollback_response = await client.post(
            f"/deployments/{deployment_id}/rollback",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert rollback_response.status_code == 200
        data = rollback_response.json()
        assert data["status"] == "rolled_back"

    @pytest.mark.asyncio
    async def test_rollback_requires_admin(
        self,
        client: AsyncClient,
        developer_token: str,
        approved_agent: Agent,
    ) -> None:
        """Test that rollback requires admin or approver role."""
        # Create a deployment
        deployment_data = {
            "agent_id": str(approved_agent.id),
            "environment": "staging",
            "configuration": {},
            "triggered_by_id": "placeholder",
        }

        create_response = await client.post(
            "/deployments/",
            json=deployment_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        deployment_id = create_response.json()["id"]

        # Try to rollback as developer (should fail)
        rollback_response = await client.post(
            f"/deployments/{deployment_id}/rollback",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert rollback_response.status_code == 403

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_deployment(
        self,
        client: AsyncClient,
        admin_token: str,
    ) -> None:
        """Test rolling back a deployment that doesn't exist."""
        from uuid import uuid4

        fake_id = str(uuid4())

        response = await client.post(
            f"/deployments/{fake_id}/rollback",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404
