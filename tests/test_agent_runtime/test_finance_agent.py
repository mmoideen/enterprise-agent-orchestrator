"""Tests for FinanceAgent."""

from uuid import uuid4

import pytest

from apps.agent_runtime.agents.finance_agent import FinanceAgent
from packages.governance_sdk.policy_engine import PolicyEngine
from packages.governance_sdk.pii_detector import PIIDetector


class TestFinanceAgentCapabilities:
    """Tests for Finance agent capabilities."""

    def test_get_capabilities(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test Finance agent capabilities structure."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        capabilities = agent.get_capabilities()

        assert capabilities["agent_type"] == "finance"
        assert "process_invoice" in capabilities["supported_actions"]
        assert "approve_expense" in capabilities["supported_actions"]
        assert capabilities["data_access"]["pii_access"] is False
        assert capabilities["requires_approval"] is True


class TestFinanceAgentActions:
    """Tests for Finance agent actions."""

    @pytest.mark.asyncio
    async def test_process_invoice(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test invoice processing action."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "process_invoice",
            "parameters": {
                "invoice_number": "INV-2024-001",
                "vendor": "Acme Corp",
                "amount": 5000.00,
                "due_date": "2024-02-15",
            },
        }

        result = await agent.execute(task)

        assert result["status"] == "approved"
        assert "invoice_id" in result
        assert "payment_scheduled" in result
        assert "approval_chain" in result

    @pytest.mark.asyncio
    async def test_approve_expense(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test expense approval action."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "approve_expense",
            "parameters": {
                "expense_id": "EXP-2024-001",
                "employee_id": "EMP-12345",
                "total_amount": 250.00,
            },
        }

        result = await agent.execute(task)

        assert result["status"] == "approved"
        assert result["expense_id"] == "EXP-2024-001"
        assert "reimbursement_amount" in result
        assert "payment_date" in result

    @pytest.mark.asyncio
    async def test_analyze_budget_variance(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test budget variance analysis."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "analyze_budget_variance",
            "parameters": {
                "department": "Engineering",
                "period": "2024-Q1",
                "budget_category": "personnel",
            },
        }

        result = await agent.execute(task)

        assert "budget" in result
        assert "actual" in result
        assert "variance" in result
        assert "variance_percent" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_generate_financial_report(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test financial report generation."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "generate_financial_report",
            "parameters": {
                "report_type": "monthly_summary",
                "period": "2024-01",
                "format": "pdf",
            },
        }

        result = await agent.execute(task)

        assert "report_type" in result
        assert "revenue" in result
        assert "expenses" in result
        assert "profit" in result
        assert "profit_margin" in result

    @pytest.mark.asyncio
    async def test_reconcile_accounts(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test account reconciliation."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "reconcile_accounts",
            "parameters": {"account_id": "ACC-1001", "period": "2024-01"},
        }

        result = await agent.execute(task)

        assert result["account_id"] == "ACC-1001"
        assert "transactions_matched" in result
        assert "discrepancies" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_unsupported_action(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test that unsupported actions raise ValueError."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {"action": "invalid_action", "parameters": {}}

        with pytest.raises(ValueError, match="Unsupported action"):
            await agent.execute(task)


class TestFinanceAgentWithGovernance:
    """Tests for Finance agent with governance checks."""

    @pytest.mark.asyncio
    async def test_invoice_processing_with_governance(
        self, policy_engine: PolicyEngine, pii_detector: PIIDetector
    ) -> None:
        """Test invoice processing with full governance checks."""
        agent = FinanceAgent(
            agent_id=uuid4(),
            agent_name="Finance Agent",
            policy_engine=policy_engine,
            pii_detector=pii_detector,
        )

        task = {
            "action": "process_invoice",
            "parameters": {
                "invoice_number": "INV-2024-001",
                "vendor": "Acme Corp",
                "amount": 5000.00,
            },
            "data_classification": "confidential",
        }

        result = await agent.execute_with_governance(task)

        assert result["success"] is True
        assert result["governance"]["policy_compliant"] is True
