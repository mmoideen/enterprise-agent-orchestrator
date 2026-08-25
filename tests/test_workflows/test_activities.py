"""Tests for Temporal activity implementations."""

from uuid import uuid4

import pytest

from apps.worker.activities.agent_activities import (
    deploy_agent,
    health_check_agent,
    rollback_agent,
    validate_agent,
)
from apps.worker.activities.coordination_activities import (
    acquire_lock,
    aggregate_results,
    execute_agent_task,
    release_lock,
)


class TestAgentValidation:
    """Tests for the pre-deployment validation activity."""

    @pytest.mark.asyncio
    async def test_valid_configuration(self) -> None:
        """Test that a complete configuration passes validation."""
        result = await validate_agent(
            uuid4(),
            {"runtime": "python", "resources": {"memory_mb": 512, "cpu_cores": 2}},
        )

        assert result == {"valid": True, "errors": []}

    @pytest.mark.asyncio
    async def test_missing_keys_and_resource_limits(self) -> None:
        """Test that missing keys and oversized resource requests are reported."""
        result = await validate_agent(
            uuid4(),
            {"resources": {"memory_mb": 16384, "cpu_cores": 8}},
        )

        assert result["valid"] is False
        assert "Missing required configuration key: runtime" in result["errors"]
        assert "Memory limit exceeds maximum (8192 MB)" in result["errors"]
        assert "CPU cores exceed maximum (4)" in result["errors"]


class TestDeploymentActivities:
    """Tests for deployment, health check, and rollback activities."""

    @pytest.mark.asyncio
    async def test_deploy_agent_returns_endpoint(self) -> None:
        """Test that deployment reports the environment-specific endpoint."""
        deployment_id = uuid4()
        agent_id = uuid4()

        result = await deploy_agent(deployment_id, agent_id, "staging", {})

        assert result["success"] is True
        assert result["deployment_id"] == str(deployment_id)
        assert result["endpoint"] == f"https://staging.agents.example.com/{agent_id}"

    @pytest.mark.asyncio
    async def test_health_check_agent(self) -> None:
        """Test that the health check reports a healthy deployment."""
        result = await health_check_agent(uuid4())

        assert result == {"healthy": True, "issues": []}

    @pytest.mark.asyncio
    async def test_rollback_agent(self) -> None:
        """Test that rollback reports completion."""
        result = await rollback_agent(uuid4())

        assert result == {"success": True, "rolled_back": True}


class TestCoordinationActivities:
    """Tests for cross-agent coordination activities."""

    @pytest.mark.asyncio
    async def test_lock_lifecycle(self) -> None:
        """Test acquiring and releasing a resource lock."""
        acquired = await acquire_lock("payroll")
        released = await release_lock("payroll")

        assert acquired == {
            "acquired": True,
            "resource_id": "payroll",
            "lock_id": "lock-payroll",
        }
        assert released == {"released": True, "resource_id": "payroll"}

    @pytest.mark.asyncio
    async def test_execute_agent_task(self) -> None:
        """Test that task execution echoes the task identity and completes."""
        result = await execute_agent_task(
            {"id": "task-1", "agent_id": "agent-1", "action": "onboard"}
        )

        assert result["task_id"] == "task-1"
        assert result["agent_id"] == "agent-1"
        assert result["action"] == "onboard"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_aggregate_results(self) -> None:
        """Test that aggregation counts successes and computes a success rate."""
        result = await aggregate_results(
            [{"status": "completed"}, {"status": "failed"}],
        )

        assert result["total_tasks"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["summary"] == {"success_rate": 0.5}

    @pytest.mark.asyncio
    async def test_aggregate_empty_results(self) -> None:
        """Test that aggregating no results avoids dividing by zero."""
        result = await aggregate_results([])

        assert result["total_tasks"] == 0
        assert result["summary"] == {"success_rate": 0}
