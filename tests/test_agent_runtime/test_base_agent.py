"""Tests for BaseAgent class."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from apps.agent_runtime.base_agent import BaseAgent
from packages.governance_sdk.policy_engine import PolicyEngine, PolicyEvaluationResult
from packages.governance_sdk.pii_detector import PIIDetector
from packages.mcp_adapter.client import MCPClient


class TestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute test task."""
        action = task.get("action")
        if action == "fail":
            raise ValueError("Task execution failed")
        return {"status": "success", "result": f"Executed {action}"}

    def get_capabilities(self) -> dict[str, Any]:
        """Get test agent capabilities."""
        return {
            "agent_type": "test",
            "supported_actions": ["test_action", "fail"],
        }


class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization."""

    def test_agent_initialization(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test agent initialization with required components."""
        agent_id = uuid4()
        agent = TestAgent(
            agent_id=agent_id,
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        assert agent.agent_id == agent_id
        assert agent.agent_name == "Test Agent"
        assert agent.policy_engine is policy_engine
        assert agent.pii_detector is pii_detector
        assert agent.mcp_client is None

    def test_agent_with_mcp_client(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test agent initialization with MCP client."""
        mcp_client = MagicMock(spec=MCPClient)
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
            mcp_client=mcp_client,
        )

        assert agent.mcp_client is mcp_client


class TestBaseAgentExecution:
    """Tests for BaseAgent execution methods."""

    @pytest.mark.asyncio
    async def test_execute_method_must_be_implemented(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test that execute method is abstract."""
        # BaseAgent itself cannot be instantiated
        with pytest.raises(TypeError):
            BaseAgent(  # type: ignore
                agent_id=uuid4(),
                agent_name="Base",
                policy_engine=policy_engine,
                pii_detector=pii_detector,
            )

    @pytest.mark.asyncio
    async def test_successful_execution(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test successful task execution."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "test_action", "parameters": {"key": "value"}}
        result = await agent.execute(task)

        assert result["status"] == "success"
        assert "test_action" in result["result"]

    @pytest.mark.asyncio
    async def test_execution_failure(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test task execution failure."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "fail"}
        with pytest.raises(ValueError, match="Task execution failed"):
            await agent.execute(task)


class TestGovernanceHooks:
    """Tests for governance enforcement in execute_with_governance."""

    @pytest.mark.asyncio
    async def test_execute_with_governance_success(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test successful execution with governance checks."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "test_action",
            "data_classification": "internal",
            "redact_pii": False,
        }
        result = await agent.execute_with_governance(task)

        assert result["success"] is True
        assert "result" in result
        assert result["governance"]["policy_compliant"] is True

    @pytest.mark.asyncio
    async def test_policy_violation_blocks_execution(
        self, pii_detector: PIIDetector
    ) -> None:
        """Test that policy violations prevent execution."""
        from packages.domain_models.policy import Policy, PolicyRule, PolicyStatus

        # Create restrictive policy
        deny_policy = Policy(
            id=uuid4(),
            name="Deny All",
            description="Test",
            rules=[
                PolicyRule(
                    rule_type="agent_type",
                    condition={"allowed_types": ["test"]},
                    action="deny",
                )
            ],
            scope="agent",
            priority=1,
            created_by_id=uuid4(),
            status=PolicyStatus.ACTIVE,
        )

        policy_engine = PolicyEngine([deny_policy])
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "test_action", "agent_type": "test"}

        with pytest.raises(PermissionError, match="Policy violation"):
            await agent.execute_with_governance(task)

    @pytest.mark.asyncio
    async def test_pii_detection_in_output(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test PII detection in task output."""

        class PIIAgent(BaseAgent):
            """Agent that returns PII in output."""

            async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
                return {
                    "status": "success",
                    "data": "Contact john.doe@example.com",
                }

            def get_capabilities(self) -> dict[str, Any]:
                return {"agent_type": "pii_test"}

        agent = PIIAgent(
            agent_id=uuid4(),
            agent_name="PII Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "get_data", "data_classification": "internal"}
        result = await agent.execute_with_governance(task)

        # Execution should succeed but PII should be flagged
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pre_execution_checks(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test pre-execution governance checks are called."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        # Mock the pre-execution checks
        original_pre_check = agent._pre_execution_checks
        check_called = False

        async def mock_pre_check(task: dict[str, Any]) -> None:
            nonlocal check_called
            check_called = True
            await original_pre_check(task)

        agent._pre_execution_checks = mock_pre_check  # type: ignore

        task = {"action": "test_action", "data_classification": "internal"}
        await agent.execute_with_governance(task)

        assert check_called is True

    @pytest.mark.asyncio
    async def test_post_execution_checks(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test post-execution governance checks are called."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        # Mock the post-execution checks
        original_post_check = agent._post_execution_checks
        check_called = False

        async def mock_post_check(
            task: dict[str, Any], result: dict[str, Any]
        ) -> None:
            nonlocal check_called
            check_called = True
            await original_post_check(task, result)

        agent._post_execution_checks = mock_post_check  # type: ignore

        task = {"action": "test_action", "data_classification": "internal"}
        await agent.execute_with_governance(task)

        assert check_called is True


class TestCapabilities:
    """Tests for get_capabilities method."""

    def test_get_capabilities_must_be_implemented(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test that get_capabilities is abstract."""
        # Already tested in initialization, but verify the method exists
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        capabilities = agent.get_capabilities()
        assert "agent_type" in capabilities
        assert "supported_actions" in capabilities

    def test_capabilities_structure(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test capabilities return proper structure."""
        agent = TestAgent(
            agent_id=uuid4(),
            agent_name="Test Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        capabilities = agent.get_capabilities()
        assert isinstance(capabilities, dict)
        assert isinstance(capabilities["supported_actions"], list)
