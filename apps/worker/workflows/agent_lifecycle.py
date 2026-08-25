"""Agent lifecycle workflow."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.agent_activities import (
        deploy_agent,
        health_check_agent,
        rollback_agent,
        validate_agent,
    )


@dataclass
class AgentLifecycleInput:
    """Input parameters for agent lifecycle workflow."""

    deployment_id: UUID
    agent_id: UUID
    environment: str
    configuration: dict[str, Any]


@dataclass
class AgentLifecycleResult:
    """Result of agent lifecycle workflow."""

    success: bool
    deployment_id: UUID
    status: str
    message: str


@workflow.defn
class AgentLifecycleWorkflow:
    """
    Workflow for managing the complete agent deployment lifecycle.

    This workflow orchestrates the following stages:
    1. Validation: Verify agent configuration and prerequisites
    2. Deployment: Deploy agent to target environment
    3. Health check: Verify agent is running correctly
    4. Rollback: Compensating action if any stage fails

    The workflow uses Temporal's retry policies and compensation patterns
    to ensure reliable deployment with automatic rollback on failure.
    """

    @workflow.run
    async def run(self, input: AgentLifecycleInput) -> AgentLifecycleResult:
        """
        Execute the agent lifecycle workflow.

        Args:
            input: AgentLifecycleInput with deployment parameters.

        Returns:
            AgentLifecycleResult with deployment outcome.
        """
        workflow.logger.info(
            "Starting agent lifecycle workflow",
            extra={
                "deployment_id": str(input.deployment_id),
                "agent_id": str(input.agent_id),
            },
        )

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )

        try:
            # Stage 1: Validation
            workflow.logger.info("Stage 1: Validating agent")
            validation_result = await workflow.execute_activity(
                validate_agent,
                args=[input.agent_id, input.configuration],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            if not validation_result["valid"]:
                raise ValueError(f"Agent validation failed: {validation_result['errors']}")

            # Stage 2: Deployment
            workflow.logger.info("Stage 2: Deploying agent")
            deployment_result = await workflow.execute_activity(
                deploy_agent,
                args=[input.deployment_id, input.agent_id, input.environment, input.configuration],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy,
            )

            if not deployment_result["success"]:
                raise RuntimeError(f"Deployment failed: {deployment_result['error']}")

            # Stage 3: Health check
            workflow.logger.info("Stage 3: Performing health check")
            health_result = await workflow.execute_activity(
                health_check_agent,
                args=[input.deployment_id],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            if not health_result["healthy"]:
                raise RuntimeError(f"Health check failed: {health_result['issues']}")

            workflow.logger.info(
                "Agent lifecycle completed successfully",
                extra={"deployment_id": str(input.deployment_id)},
            )

            return AgentLifecycleResult(
                success=True,
                deployment_id=input.deployment_id,
                status="completed",
                message="Agent deployed and verified successfully",
            )

        except Exception as e:
            workflow.logger.error(
                "Agent lifecycle failed, initiating rollback",
                extra={"deployment_id": str(input.deployment_id), "error": str(e)},
            )

            # Compensating action: Rollback
            try:
                await workflow.execute_activity(
                    rollback_agent,
                    args=[input.deployment_id],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy,
                )
            except Exception as rollback_error:
                workflow.logger.error(
                    "Rollback failed",
                    extra={
                        "deployment_id": str(input.deployment_id),
                        "error": str(rollback_error),
                    },
                )

            return AgentLifecycleResult(
                success=False,
                deployment_id=input.deployment_id,
                status="failed",
                message=f"Deployment failed: {str(e)}",
            )
