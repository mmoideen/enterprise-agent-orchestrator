"""Tests for CrossAgentCoordinationWorkflow."""

from typing import Any
from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.worker.workflows.cross_agent_coordination import (
    CoordinationInput,
    CoordinationResult,
    CrossAgentCoordinationWorkflow,
)


class TestCrossAgentCoordinationWorkflow:
    """Tests for cross-agent coordination workflow."""

    @pytest.mark.asyncio
    async def test_parallel_task_execution(self) -> None:
        """Test parallel execution of agent tasks."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_acquire_lock(resource_id: str) -> dict[str, Any]:
                return {"acquired": True, "resource_id": resource_id}

            async def mock_release_lock(resource_id: str) -> dict[str, Any]:
                return {"released": True, "resource_id": resource_id}

            async def mock_execute_task(task: dict[str, Any]) -> dict[str, Any]:
                return {
                    "task_id": task.get("id"),
                    "agent_id": task.get("agent_id"),
                    "status": "completed",
                    "result": {"success": True},
                }

            async def mock_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
                return {
                    "total_tasks": len(results),
                    "successful": len(results),
                    "failed": 0,
                    "results": results,
                }

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[CrossAgentCoordinationWorkflow],
                activities=[
                    mock_acquire_lock,
                    mock_release_lock,
                    mock_execute_task,
                    mock_aggregate,
                ],
            ):
                # Execute workflow
                tasks = [
                    {"id": "task-1", "agent_id": "agent-1", "action": "test"},
                    {"id": "task-2", "agent_id": "agent-2", "action": "test"},
                    {"id": "task-3", "agent_id": "agent-3", "action": "test"},
                ]

                result = await env.client.execute_workflow(
                    CrossAgentCoordinationWorkflow.run,
                    CoordinationInput(
                        coordination_id=uuid4(),
                        agent_tasks=tasks,
                        require_sequential=False,
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is True
                assert len(result.results) == 3
                assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_sequential_task_execution(self) -> None:
        """Test sequential execution of agent tasks."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            execution_order = []

            # Mock activities
            async def mock_acquire_lock(resource_id: str) -> dict[str, Any]:
                return {"acquired": True, "resource_id": resource_id}

            async def mock_release_lock(resource_id: str) -> dict[str, Any]:
                return {"released": True, "resource_id": resource_id}

            async def mock_execute_task(task: dict[str, Any]) -> dict[str, Any]:
                execution_order.append(task.get("id"))
                return {
                    "task_id": task.get("id"),
                    "status": "completed",
                    "result": {"success": True},
                }

            async def mock_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
                return {
                    "total_tasks": len(results),
                    "successful": len(results),
                    "failed": 0,
                    "results": results,
                }

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[CrossAgentCoordinationWorkflow],
                activities=[
                    mock_acquire_lock,
                    mock_release_lock,
                    mock_execute_task,
                    mock_aggregate,
                ],
            ):
                # Execute workflow
                tasks = [
                    {"id": "task-1", "action": "test"},
                    {"id": "task-2", "action": "test"},
                    {"id": "task-3", "action": "test"},
                ]

                result = await env.client.execute_workflow(
                    CrossAgentCoordinationWorkflow.run,
                    CoordinationInput(
                        coordination_id=uuid4(),
                        agent_tasks=tasks,
                        require_sequential=True,
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                assert result.success is True
                # Verify sequential execution
                assert execution_order == ["task-1", "task-2", "task-3"]

    @pytest.mark.asyncio
    async def test_distributed_locking(self) -> None:
        """Test distributed locking for shared resources."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            locks_acquired = []
            locks_released = []

            # Mock activities
            async def mock_acquire_lock(resource_id: str) -> dict[str, Any]:
                locks_acquired.append(resource_id)
                return {"acquired": True, "resource_id": resource_id}

            async def mock_release_lock(resource_id: str) -> dict[str, Any]:
                locks_released.append(resource_id)
                return {"released": True, "resource_id": resource_id}

            async def mock_execute_task(task: dict[str, Any]) -> dict[str, Any]:
                return {"task_id": task.get("id"), "status": "completed"}

            async def mock_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
                return {"total_tasks": len(results), "results": results}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[CrossAgentCoordinationWorkflow],
                activities=[
                    mock_acquire_lock,
                    mock_release_lock,
                    mock_execute_task,
                    mock_aggregate,
                ],
            ):
                # Execute workflow
                tasks = [
                    {"id": "task-1", "resource_id": "resource-1", "action": "test"},
                    {"id": "task-2", "resource_id": "resource-2", "action": "test"},
                ]

                await env.client.execute_workflow(
                    CrossAgentCoordinationWorkflow.run,
                    CoordinationInput(
                        coordination_id=uuid4(),
                        agent_tasks=tasks,
                        require_sequential=False,
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                # Verify locks were acquired and released
                assert "resource-1" in locks_acquired
                assert "resource-2" in locks_acquired
                assert "resource-1" in locks_released
                assert "resource-2" in locks_released

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self) -> None:
        """Test handling of partial task failures."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock activities
            async def mock_acquire_lock(resource_id: str) -> dict[str, Any]:
                return {"acquired": True, "resource_id": resource_id}

            async def mock_release_lock(resource_id: str) -> dict[str, Any]:
                return {"released": True, "resource_id": resource_id}

            async def mock_execute_task(task: dict[str, Any]) -> dict[str, Any]:
                if task.get("id") == "task-2":
                    raise ValueError("Task 2 failed")
                return {"task_id": task.get("id"), "status": "completed"}

            async def mock_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
                return {"total_tasks": len(results), "results": results}

            # Create worker
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[CrossAgentCoordinationWorkflow],
                activities=[
                    mock_acquire_lock,
                    mock_release_lock,
                    mock_execute_task,
                    mock_aggregate,
                ],
            ):
                # Execute workflow
                tasks = [
                    {"id": "task-1", "action": "test"},
                    {"id": "task-2", "action": "test"},
                    {"id": "task-3", "action": "test"},
                ]

                result = await env.client.execute_workflow(
                    CrossAgentCoordinationWorkflow.run,
                    CoordinationInput(
                        coordination_id=uuid4(),
                        agent_tasks=tasks,
                        require_sequential=False,
                    ),
                    id=f"test-workflow-{uuid4()}",
                    task_queue="test-queue",
                )

                # Workflow should complete but report errors
                assert result.success is False
                assert len(result.errors) > 0
                # Some tasks should succeed
                assert len(result.results) > 0


class TestCoordinationInput:
    """Tests for coordination input validation."""

    def test_input_structure(self) -> None:
        """Test CoordinationInput structure."""
        coordination_id = uuid4()
        tasks = [
            {"id": "task-1", "agent_id": "agent-1"},
            {"id": "task-2", "agent_id": "agent-2"},
        ]

        input_data = CoordinationInput(
            coordination_id=coordination_id,
            agent_tasks=tasks,
            require_sequential=True,
        )

        assert input_data.coordination_id == coordination_id
        assert len(input_data.agent_tasks) == 2
        assert input_data.require_sequential is True


class TestCoordinationResult:
    """Tests for coordination result structure."""

    def test_success_result(self) -> None:
        """Test successful coordination result."""
        coordination_id = uuid4()

        result = CoordinationResult(
            success=True,
            coordination_id=coordination_id,
            results=[{"task_id": "task-1", "status": "completed"}],
            errors=[],
        )

        assert result.success is True
        assert result.coordination_id == coordination_id
        assert len(result.results) == 1
        assert len(result.errors) == 0

    def test_failure_result(self) -> None:
        """Test coordination result with failures."""
        coordination_id = uuid4()

        result = CoordinationResult(
            success=False,
            coordination_id=coordination_id,
            results=[],
            errors=["Task 1 failed", "Task 2 failed"],
        )

        assert result.success is False
        assert len(result.errors) == 2
