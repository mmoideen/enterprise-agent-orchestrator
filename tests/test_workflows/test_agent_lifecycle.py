"""Tests for AgentLifecycleWorkflow."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.workflows.agent_lifecycle import (
    AgentLifecycleInput,
    AgentLifecycleResult,
    AgentLifecycleWorkflow,
)
from apps.worker.activities.agent_activities import (
    deploy_agent,
    health_check_agent,
    rollback_agent,
    validate_agent,
)


class TestAgentLifecycleWorkflow:
    """Tests for agent lifecycle workflow."""

    @pytest.mark.asyncio
    async def test_successful_lifecycle(self) -> None:
        """Test complete successful agent lifecycle."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_validate(agent_id: Any, config: Any) -> dict[str, Any]:
                return {"valid": True, "errors": []}

            async def mock_deploy(
                deployment_id: Any, agent_id: Any, environment: str, config: Any
            ) -> dict[str, Any]:
                return {"success": True}

            async def mock_health_check(deployment_id: Any) -> dict[str, Any]:
                return {"healthy": True, "issues": []}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[AgentLifecycleWorkflow],
                activities=[mock_validate, mock_deploy, mock_health_check],
            ):
                # Execute workflow
                result = await env.client.execute_workflow(
                    AgentLifecycleWorkflow.run,
                    AgentLifecycleInput(
                        deployment_id=uuid4(),
                        agent_id=uuid4(),
                        environment="staging",
                        configuration={"replicas": 1},
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is True
                assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_validation_failure(self) -> None:
        """Test workflow handles validation failure."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_validate(agent_id: Any, config: Any) -> dict[str, Any]:
                return {"valid": False, "errors": ["Invalid configuration"]}

            async def mock_rollback(deployment_id: Any) -> dict[str, Any]:
                return {"success": True, "rolled_back": True}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[AgentLifecycleWorkflow],
                activities=[mock_validate, mock_rollback],
            ):
                # Execute workflow
                result = await env.client.execute_workflow(
                    AgentLifecycleWorkflow.run,
                    AgentLifecycleInput(
                        deployment_id=uuid4(),
                        agent_id=uuid4(),
                        environment="staging",
                        configuration={},
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is False
                assert "validation failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_deployment_failure_triggers_rollback(self) -> None:
        """Test that deployment failure triggers rollback."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_validate(agent_id: Any, config: Any) -> dict[str, Any]:
                return {"valid": True, "errors": []}

            async def mock_deploy(
                deployment_id: Any, agent_id: Any, environment: str, config: Any
            ) -> dict[str, Any]:
                return {"success": False, "error": "Deployment failed"}

            rollback_called = False

            async def mock_rollback(deployment_id: Any) -> dict[str, Any]:
                nonlocal rollback_called
                rollback_called = True
                return {"success": True, "rolled_back": True}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[AgentLifecycleWorkflow],
                activities=[mock_validate, mock_deploy, mock_rollback],
            ):
                # Execute workflow
                result = await env.client.execute_workflow(
                    AgentLifecycleWorkflow.run,
                    AgentLifecycleInput(
                        deployment_id=uuid4(),
                        agent_id=uuid4(),
                        environment="staging",
                        configuration={},
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is False
                assert rollback_called is True

    @pytest.mark.asyncio
    async def test_health_check_failure_triggers_rollback(self) -> None:
        """Test that health check failure triggers rollback."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_validate(agent_id: Any, config: Any) -> dict[str, Any]:
                return {"valid": True, "errors": []}

            async def mock_deploy(
                deployment_id: Any, agent_id: Any, environment: str, config: Any
            ) -> dict[str, Any]:
                return {"success": True}

            async def mock_health_check(deployment_id: Any) -> dict[str, Any]:
                return {"healthy": False, "issues": ["Service not responding"]}

            rollback_called = False

            async def mock_rollback(deployment_id: Any) -> dict[str, Any]:
                nonlocal rollback_called
                rollback_called = True
                return {"success": True, "rolled_back": True}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[AgentLifecycleWorkflow],
                activities=[
                    mock_validate,
                    mock_deploy,
                    mock_health_check,
                    mock_rollback,
                ],
            ):
                # Execute workflow
                result = await env.client.execute_workflow(
                    AgentLifecycleWorkflow.run,
                    AgentLifecycleInput(
                        deployment_id=uuid4(),
                        agent_id=uuid4(),
                        environment="staging",
                        configuration={},
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is False
                assert rollback_called is True


class TestAgentLifecycleInput:
    """Tests for workflow input validation."""

    def test_input_structure(self) -> None:
        """Test AgentLifecycleInput structure."""
        deployment_id = uuid4()
        agent_id = uuid4()

        input_data = AgentLifecycleInput(
            deployment_id=deployment_id,
            agent_id=agent_id,
            environment="production",
            configuration={"replicas": 3},
        )

        assert input_data.deployment_id == deployment_id
        assert input_data.agent_id == agent_id
        assert input_data.environment == "production"
        assert input_data.configuration["replicas"] == 3


class TestAgentLifecycleResult:
    """Tests for workflow result structure."""

    def test_success_result(self) -> None:
        """Test successful result structure."""
        deployment_id = uuid4()

        result = AgentLifecycleResult(
            success=True,
            deployment_id=deployment_id,
            status="completed",
            message="Deployment successful",
        )

        assert result.success is True
        assert result.deployment_id == deployment_id
        assert result.status == "completed"
        assert "successful" in result.message

    def test_failure_result(self) -> None:
        """Test failure result structure."""
        deployment_id = uuid4()

        result = AgentLifecycleResult(
            success=False,
            deployment_id=deployment_id,
            status="failed",
            message="Deployment failed: validation error",
        )

        assert result.success is False
        assert result.status == "failed"
        assert "failed" in result.message
