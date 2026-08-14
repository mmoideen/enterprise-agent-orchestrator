"""Tests for ComplianceAgent."""

from uuid import uuid4

import pytest

from apps.agent_runtime.agents.compliance_agent import ComplianceAgent
from packages.governance_sdk.policy_engine import PolicyEngine
from packages.governance_sdk.pii_detector import PIIDetector


class TestComplianceAgentCapabilities:
    """Tests for Compliance agent capabilities."""

    def test_get_capabilities(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test Compliance agent capabilities structure."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        capabilities = agent.get_capabilities()

        assert capabilities["agent_type"] == "compliance"
        assert "detect_policy_violations" in capabilities["supported_actions"]
        assert "generate_audit_trail" in capabilities["supported_actions"]
        assert capabilities["data_access"]["classification"] == "restricted"
        assert capabilities["data_access"]["pii_access"] is True
        assert capabilities["requires_approval"] is True


class TestComplianceAgentActions:
    """Tests for Compliance agent actions."""

    @pytest.mark.asyncio
    async def test_detect_policy_violations(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test policy violation detection."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "detect_policy_violations",
            "parameters": {
                "time_range": "last_24_hours",
                "policy_scope": "data_access",
                "severity": "high",
            },
        }

        result = await agent.execute(task)

        assert "violations_found" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)

    @pytest.mark.asyncio
    async def test_generate_audit_trail(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test audit trail generation."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "generate_audit_trail",
            "parameters": {
                "resource_id": "AGT-12345",
                "resource_type": "agent",
                "time_range": "2024-01",
            },
        }

        result = await agent.execute(task)

        assert "resource_id" in result
        assert "resource_type" in result
        assert "events" in result
        assert isinstance(result["events"], list)
        assert "total_events" in result

    @pytest.mark.asyncio
    async def test_create_regulatory_report(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test regulatory report creation."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "create_regulatory_report",
            "parameters": {"framework": "SOX", "period": "2024-Q1", "scope": "all"},
        }

        result = await agent.execute(task)

        assert result["framework"] == "SOX"
        assert "compliance_score" in result
        assert "findings" in result
        assert isinstance(result["findings"], list)

    @pytest.mark.asyncio
    async def test_assess_compliance_risk(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test compliance risk assessment."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "assess_compliance_risk",
            "parameters": {
                "target_id": "AGT-12345",
                "target_type": "agent",
                "frameworks": ["GDPR", "SOX", "HIPAA"],
            },
        }

        result = await agent.execute(task)

        assert "risk_score" in result
        assert "risk_level" in result
        assert "framework_compliance" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_review_data_access(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test data access review."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "review_data_access",
            "parameters": {
                "user_id": "USR-12345",
                "data_classification": "restricted",
                "time_range": "last_7_days",
            },
        }

        result = await agent.execute(task)

        assert "user_id" in result
        assert "access_patterns" in result
        assert isinstance(result["access_patterns"], list)

    @pytest.mark.asyncio
    async def test_unsupported_action(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test that unsupported actions raise ValueError."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "invalid_action", "parameters": {}}

        with pytest.raises(ValueError, match="Unsupported action"):
            await agent.execute(task)


class TestComplianceAgentWithGovernance:
    """Tests for Compliance agent with governance checks."""

    @pytest.mark.asyncio
    async def test_violation_detection_with_governance(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test violation detection with full governance checks."""
        agent = ComplianceAgent(
            agent_id=uuid4(),
            agent_name="Compliance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "detect_policy_violations",
            "parameters": {"time_range": "last_24_hours"},
            "data_classification": "restricted",
        }

        result = await agent.execute_with_governance(task)

        assert result["success"] is True
        assert result["governance"]["policy_compliant"] is True
