"""Temporal worker main entry point."""

import asyncio
import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from apps.orchestrator.config import settings
from apps.worker.workflows.agent_lifecycle import AgentLifecycleWorkflow
from apps.worker.workflows.cross_agent_coordination import CrossAgentCoordinationWorkflow
from apps.worker.activities.agent_activities import (
    validate_agent,
    deploy_agent,
    health_check_agent,
    rollback_agent,
)
from apps.worker.activities.coordination_activities import (
    acquire_lock,
    release_lock,
    execute_agent_task,
    aggregate_results,
)

logger = structlog.get_logger()


async def main() -> None:
    """Start the Temporal worker."""
    logger.info(
        "connecting_to_temporal",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    # Connect to Temporal server
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    # Create worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            AgentLifecycleWorkflow,
            CrossAgentCoordinationWorkflow,
        ],
        activities=[
            validate_agent,
            deploy_agent,
            health_check_agent,
            rollback_agent,
            acquire_lock,
            release_lock,
            execute_agent_task,
            aggregate_results,
        ],
    )

    logger.info(
        "temporal_worker_started",
        task_queue=settings.temporal_task_queue,
    )

    # Run worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
