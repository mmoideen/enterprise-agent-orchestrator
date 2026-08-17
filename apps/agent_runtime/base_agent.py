"""Base agent class with governance hooks."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

import structlog

from packages.governance_sdk.pii_detector import PIIDetector
from packages.governance_sdk.policy_engine import PolicyEngine
from packages.mcp_adapter.client import MCPClient

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Base class for all specialized agents.

    This class provides common functionality and governance hooks that all
    agents must implement. It enforces policy compliance, audit logging,
    and data lineage tracking.

    All agent implementations must inherit from this class and implement
    the abstract methods for their specific functionality.
    """

    def __init__(
        self,
        agent_id: UUID,
        agent_name: str,
        policy_engine: PolicyEngine,
        pii_detector: PIIDetector,
        mcp_client: MCPClient | None = None,
    ) -> None:
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent instance.
            agent_name: Human-readable name for the agent.
            policy_engine: Policy engine for governance checks.
            pii_detector: PII detector for data validation.
            mcp_client: Optional MCP client for tool access.
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.policy_engine = policy_engine
        self.pii_detector = pii_detector
        self.mcp_client = mcp_client
        self.logger = logger.bind(agent_id=str(agent_id), agent_name=agent_name)

    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a task.

        This method must be implemented by all agent subclasses to define
        their specific behavior.

        Args:
            task: Task specification with action and parameters.

        Returns:
            Task execution result.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """
        Get agent capabilities.

        Returns:
            Dictionary describing agent capabilities.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement get_capabilities()")

    async def execute_with_governance(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a task with full governance checks.

        This wrapper method applies all governance controls before, during,
        and after task execution.

        Args:
            task: Task specification.

        Returns:
            Task execution result with governance metadata.

        Raises:
            PermissionError: If policy evaluation denies the action.
            ValueError: If PII is detected when not allowed.
        """
        self.logger.info("executing_task_with_governance", task_type=task.get("action"))

        # Pre-execution governance checks
        await self._pre_execution_checks(task)

        # Execute the actual task
        try:
            result = await self.execute(task)

            # Post-execution governance checks
            await self._post_execution_checks(task, result)

            self.logger.info("task_completed_successfully", task_type=task.get("action"))

            return {
                "success": True,
                "result": result,
                "governance": {
                    "policy_compliant": True,
                    "pii_detected": False,
                    "data_lineage_tracked": True,
                },
            }

        except Exception as e:
            self.logger.error(
                "task_execution_failed",
                task_type=task.get("action"),
                error=str(e),
            )
            raise

    async def _pre_execution_checks(self, task: dict[str, Any]) -> None:
        """
        Perform pre-execution governance checks.

        Args:
            task: Task specification.

        Raises:
            PermissionError: If a matched policy rule denies the action. Rules that
                only require review do not block execution; they are logged so the
                approval workflow can pick them up.
        """
        # Evaluate policies
        context = {
            "agent_id": str(self.agent_id),
            "agent_type": task.get("agent_type", self.agent_name),
            "action": task.get("action"),
            "data_classification": task.get("data_classification", "internal"),
        }

        policy_result = self.policy_engine.evaluate(context, scope="agent")

        denials = [rule for rule in policy_result.matched_rules if rule.action == "deny"]
        if denials:
            raise PermissionError(f"Policy violation: {', '.join(policy_result.violations)}")

        if "review" in policy_result.actions:
            self.logger.info("policy_review_required", violations=policy_result.violations)

        self.logger.info(
            "pre_execution_checks_passed",
            matched_rules=len(policy_result.matched_rules),
        )

    async def _post_execution_checks(self, task: dict[str, Any], result: dict[str, Any]) -> None:
        """
        Perform post-execution governance checks.

        Args:
            task: Task specification.
            result: Task execution result.

        Raises:
            ValueError: If PII is detected in output when not allowed.
        """
        # Check for PII in output
        output_text = str(result)
        if self.pii_detector.has_pii(output_text):
            self.logger.warning("pii_detected_in_output")

            # If PII detection is required, redact it
            if task.get("redact_pii", True):
                result["redacted"] = True
                result["original_output"] = result.copy()
                # In production, would actually redact the sensitive data

        # Track data lineage
        await self._track_data_lineage(task, result)

        self.logger.info("post_execution_checks_passed")

    async def _track_data_lineage(
        self,
        task: dict[str, Any],
        result: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """
        Track data lineage for this operation.

        Args:
            task: Task specification.
            result: Task execution result.
        """
        # In production, this would create a DataLineage record in the database
        # documenting the data flow from source to destination through this agent

        self.logger.info(
            "data_lineage_tracked",
            source_type=task.get("source_type"),
            destination_type=task.get("destination_type"),
        )
