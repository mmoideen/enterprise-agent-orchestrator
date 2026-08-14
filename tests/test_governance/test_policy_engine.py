"""Tests for policy engine."""

import pytest

from packages.domain_models.policy import Policy, PolicyRule, PolicyStatus
from packages.governance_sdk.policy_engine import PolicyEngine


class TestPolicyEvaluation:
    """Tests for policy evaluation."""

    def test_allow_when_no_policies_match(self) -> None:
        """Test that actions are allowed when no policies match."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="Test Policy",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["hr"]},
                        action="deny",
                    )
                ],
                scope="agent",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"agent_type": "finance"}, scope="agent")

        assert result.allowed is True
        assert len(result.matched_rules) == 0

    def test_deny_when_policy_matches(self) -> None:
        """Test that actions are denied when policy matches."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="Deny Finance",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["finance"]},
                        action="deny",
                    )
                ],
                scope="agent",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"agent_type": "finance"}, scope="agent")

        assert result.allowed is False
        assert len(result.violations) > 0

    def test_data_access_policy(self) -> None:
        """Test data access classification policy."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="Restrict Confidential",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="data_access",
                        condition={"max_classification": "internal"},
                        action="deny",
                    )
                ],
                scope="agent",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate(
            {"data_classification": "confidential"}, scope="agent"
        )

        assert result.allowed is False

    def test_risk_threshold_policy(self) -> None:
        """Test risk threshold policy."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="High Risk Block",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="risk_threshold",
                        condition={"max_risk_score": 0.5},
                        action="deny",
                    )
                ],
                scope="agent",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"risk_score": 0.8}, scope="agent")

        assert result.allowed is False

    def test_policy_priority_ordering(self) -> None:
        """Test that higher priority policies are evaluated first."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000001",
                name="Low Priority",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["hr"]},
                        action="allow",
                    )
                ],
                scope="agent",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            ),
            Policy(
                id="00000000-0000-0000-0000-000000000002",
                name="High Priority",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["hr"]},
                        action="deny",
                    )
                ],
                scope="agent",
                priority=100,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            ),
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"agent_type": "hr"}, scope="agent")

        # Higher priority deny should take precedence
        assert result.allowed is False


class TestPolicyScoping:
    """Tests for policy scope filtering."""

    def test_global_scope_applies_to_all(self) -> None:
        """Test that global scope policies apply to all scopes."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="Global Policy",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["hr"]},
                        action="deny",
                    )
                ],
                scope="global",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"agent_type": "hr"}, scope="agent")

        assert result.allowed is False

    def test_scope_specific_policy(self) -> None:
        """Test that scope-specific policies only apply to that scope."""
        policies = [
            Policy(
                id="00000000-0000-0000-0000-000000000000",
                name="Deployment Policy",
                description="Test",
                rules=[
                    PolicyRule(
                        rule_type="agent_type",
                        condition={"allowed_types": ["hr"]},
                        action="deny",
                    )
                ],
                scope="deployment",
                priority=1,
                created_by_id="00000000-0000-0000-0000-000000000000",
                status=PolicyStatus.ACTIVE,
            )
        ]

        engine = PolicyEngine(policies)
        result = engine.evaluate({"agent_type": "hr"}, scope="agent")

        # Policy should not apply to different scope
        assert result.allowed is True
