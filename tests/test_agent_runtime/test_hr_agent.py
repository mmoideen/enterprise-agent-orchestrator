"""Tests for HRAgent."""

from uuid import uuid4

import pytest

from apps.agent_runtime.agents.hr_agent import HRAgent
from packages.governance_sdk.pii_detector import PIIDetector
from packages.governance_sdk.policy_engine import PolicyEngine


class TestHRAgentCapabilities:
    """Tests for HR agent capabilities."""

    def test_get_capabilities(self, policy_engine: PolicyEngine, pii_detector: PIIDetector) -> None:
        """Test HR agent capabilities structure."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        capabilities = agent.get_capabilities()

        assert capabilities["agent_type"] == "hr"
        assert "onboard_employee" in capabilities["supported_actions"]
        assert "offboard_employee" in capabilities["supported_actions"]
        assert "process_pto_request" in capabilities["supported_actions"]
        assert capabilities["data_access"]["pii_access"] is True
        assert capabilities["requires_approval"] is True


class TestHRAgentActions:
    """Tests for HR agent actions."""

    @pytest.mark.asyncio
    async def test_onboard_employee(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test employee onboarding action."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "onboard_employee",
            "parameters": {
                "employee_name": "John Doe",
                "start_date": "2024-02-01",
                "department": "Engineering",
            },
        }

        result = await agent.execute(task)

        assert result["status"] == "completed"
        assert "employee_id" in result
        assert "accounts_created" in result
        assert len(result["accounts_created"]) > 0

    @pytest.mark.asyncio
    async def test_offboard_employee(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test employee offboarding action."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "offboard_employee",
            "parameters": {
                "employee_id": "EMP-12345",
                "last_day": "2024-01-31",
                "reason": "resignation",
            },
        }

        result = await agent.execute(task)

        assert result["status"] == "completed"
        assert result["accounts_deactivated"] is not None
        assert result["data_archived"] is True

    @pytest.mark.asyncio
    async def test_process_pto_request(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test PTO request processing."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "process_pto_request",
            "parameters": {
                "employee_id": "EMP-12345",
                "start_date": "2024-03-01",
                "end_date": "2024-03-05",
                "type": "vacation",
            },
        }

        result = await agent.execute(task)

        assert result["status"] == "approved"
        assert "request_id" in result
        assert result["days_requested"] > 0

    @pytest.mark.asyncio
    async def test_query_benefits(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test benefits query action."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "query_benefits",
            "parameters": {"employee_id": "EMP-12345", "benefit_type": "health"},
        }

        result = await agent.execute(task)

        assert "benefits" in result
        assert isinstance(result["benefits"], dict)

    @pytest.mark.asyncio
    async def test_generate_compliance_report(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test compliance report generation."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "generate_compliance_report",
            "parameters": {"report_type": "i9_verification", "date_range": "2024-Q1"},
        }

        result = await agent.execute(task)

        assert "report_type" in result
        assert "compliance_items" in result
        assert isinstance(result["compliance_items"], list)

    @pytest.mark.asyncio
    async def test_unsupported_action(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test that unsupported actions raise ValueError."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "invalid_action", "parameters": {}}

        with pytest.raises(ValueError, match="Unsupported action"):
            await agent.execute(task)


class TestHRAgentWithGovernance:
    """Tests for HR agent with governance checks."""

    @pytest.mark.asyncio
    async def test_onboarding_with_governance(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test onboarding with full governance checks."""
        agent = HRAgent(
            agent_id=uuid4(),
            agent_name="HR Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "onboard_employee",
            "parameters": {"employee_name": "Jane Smith"},
            "data_classification": "confidential",
        }

        result = await agent.execute_with_governance(task)

        assert result["success"] is True
        assert result["governance"]["policy_compliant"] is True
