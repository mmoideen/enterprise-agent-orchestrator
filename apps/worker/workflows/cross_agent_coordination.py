"""Cross-agent coordination workflow."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.coordination_activities import (
        acquire_lock,
        aggregate_results,
        execute_agent_task,
        release_lock,
    )


@dataclass
class CoordinationInput:
    """Input for cross-agent coordination workflow."""

    coordination_id: UUID
    agent_tasks: list[dict[str, Any]]
    require_sequential: bool = False


@dataclass
class CoordinationResult:
    """Result of cross-agent coordination."""

    success: bool
    coordination_id: UUID
    results: list[dict[str, Any]]
    errors: list[str]


@workflow.defn
class CrossAgentCoordinationWorkflow:
    """
    Workflow for coordinating tasks across multiple agents.

    This workflow supports both parallel and sequential execution patterns,
    with distributed locking to prevent conflicts when agents access shared
    resources. It aggregates results from multiple agents and handles partial
    failures gracefully.
    """

    @workflow.run
    async def run(self, input: CoordinationInput) -> CoordinationResult:
        """
        Execute cross-agent coordination.

        Args:
            input: CoordinationInput with tasks to coordinate.

        Returns:
            CoordinationResult with aggregated outcomes.
        """
        workflow.logger.info(
            "Starting cross-agent coordination",
            extra={
                "coordination_id": str(input.coordination_id),
                "task_count": len(input.agent_tasks),
            },
        )

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )

        results = []
        errors = []
        acquired_locks = []

        try:
            # Acquire distributed locks for shared resources
            for task in input.agent_tasks:
                if "resource_id" in task:
                    lock_result = await workflow.execute_activity(
                        acquire_lock,
                        args=[task["resource_id"]],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=retry_policy,
                    )
                    if lock_result["acquired"]:
                        acquired_locks.append(task["resource_id"])

            # Execute tasks
            if input.require_sequential:
                # Sequential execution
                for task in input.agent_tasks:
                    try:
                        result = await workflow.execute_activity(
                            execute_agent_task,
                            args=[task],
                            start_to_close_timeout=timedelta(minutes=5),
                            retry_policy=retry_policy,
                        )
                        results.append(result)
                    except Exception as e:
                        errors.append(f"Task {task.get('id')} failed: {str(e)}")
            else:
                # Parallel execution
                task_futures = []
                for task in input.agent_tasks:
                    future = workflow.execute_activity(
                        execute_agent_task,
                        args=[task],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=retry_policy,
                    )
                    task_futures.append((task, future))

                # Wait for all tasks
                for task, future in task_futures:
                    try:
                        result = await future
                        results.append(result)
                    except Exception as e:
                        errors.append(f"Task {task.get('id')} failed: {str(e)}")

            # Aggregate results
            aggregated = await workflow.execute_activity(
                aggregate_results,
                args=[results],
                start_to_close_timeout=timedelta(minutes=2),
            )

            success = len(errors) == 0

            workflow.logger.info(
                "Cross-agent coordination completed",
                extra={
                    "coordination_id": str(input.coordination_id),
                    "success": success,
                    "result_count": len(results),
                    "error_count": len(errors),
                },
            )

            return CoordinationResult(
                success=success,
                coordination_id=input.coordination_id,
                results=aggregated["results"],
                errors=errors,
            )

        finally:
            # Release all acquired locks
            for resource_id in acquired_locks:
                try:
                    await workflow.execute_activity(
                        release_lock,
                        args=[resource_id],
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                except Exception as e:
                    workflow.logger.error(
                        "Failed to release lock",
                        extra={"resource_id": resource_id, "error": str(e)},
                    )
