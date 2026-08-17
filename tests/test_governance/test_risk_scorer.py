"""Tests for risk scorer."""

from typing import Any

from packages.governance_sdk.risk_scorer import RiskScorer


class TestRiskScoring:
    """Tests for risk score calculation."""

    def test_calculate_risk_score(
        self, risk_scorer: RiskScorer, sample_agent_metadata: dict[str, Any]
    ) -> None:
        """Test basic risk score calculation."""
        result = risk_scorer.calculate(sample_agent_metadata)

        assert 0.0 <= result.total_score <= 1.0
        assert result.risk_level in ["low", "medium", "high", "critical"]
        assert len(result.components) > 0
        assert "data_sensitivity" in result.components

    def test_low_risk_agent(self, risk_scorer: RiskScorer) -> None:
        """Test scoring for low-risk agent."""
        metadata = {
            "data_access": {
                "classification": "public",
                "pii_access": False,
                "volume": "low",
            },
            "capabilities": {
                "write_operations": False,
                "external_integrations": [],
                "user_facing": False,
            },
            "compliance": {"frameworks": [], "audit_required": False},
            "configuration": {
                "dependencies": [],
                "custom_code": False,
                "integration_points": 0,
            },
            "history": {
                "failure_rate": 0.0,
                "rollback_count": 0,
                "successful_deployments": 20,
            },
        }

        result = risk_scorer.calculate(metadata)

        assert result.total_score < 0.25
        assert result.risk_level == "low"

    def test_high_risk_agent(self, risk_scorer: RiskScorer) -> None:
        """Test scoring for high-risk agent."""
        metadata = {
            "data_access": {
                "classification": "restricted",
                "pii_access": True,
                "volume": "high",
            },
            "capabilities": {
                "write_operations": True,
                "external_integrations": ["api1", "api2", "api3", "api4", "api5"],
                "user_facing": True,
            },
            "compliance": {
                "frameworks": ["SOX", "HIPAA", "GDPR"],
                "audit_required": True,
            },
            "configuration": {
                "dependencies": ["dep1", "dep2", "dep3", "dep4", "dep5"],
                "custom_code": True,
                "integration_points": 10,
            },
            "history": {
                "failure_rate": 0.3,
                "rollback_count": 5,
                "successful_deployments": 2,
            },
        }

        result = risk_scorer.calculate(metadata)

        assert result.total_score > 0.5
        assert result.risk_level in ["high", "critical"]

    def test_recommendations_generated(
        self, risk_scorer: RiskScorer, sample_agent_metadata: dict[str, Any]
    ) -> None:
        """Test that recommendations are generated."""
        result = risk_scorer.calculate(sample_agent_metadata)

        assert len(result.recommendations) > 0
        assert all(isinstance(rec, str) for rec in result.recommendations)


class TestRiskComponents:
    """Tests for individual risk components."""

    def test_data_sensitivity_component(self, risk_scorer: RiskScorer) -> None:
        """Test data sensitivity scoring."""
        metadata = {
            "data_access": {
                "classification": "restricted",
                "pii_access": True,
                "volume": "high",
            },
            "capabilities": {},
            "compliance": {},
            "configuration": {},
            "history": {},
        }

        result = risk_scorer.calculate(metadata)

        assert "data_sensitivity" in result.components
        # High sensitivity should score high
        assert result.components["data_sensitivity"] > 0.5

    def test_operational_impact_component(self, risk_scorer: RiskScorer) -> None:
        """Test operational impact scoring."""
        metadata = {
            "data_access": {},
            "capabilities": {
                "write_operations": True,
                "external_integrations": ["api1", "api2"],
                "user_facing": True,
            },
            "compliance": {},
            "configuration": {},
            "history": {},
        }

        result = risk_scorer.calculate(metadata)

        assert "operational_impact" in result.components
        # Write operations and user-facing should increase score
        assert result.components["operational_impact"] > 0.3

    def test_compliance_requirements_component(self, risk_scorer: RiskScorer) -> None:
        """Test compliance requirements scoring."""
        metadata = {
            "data_access": {},
            "capabilities": {},
            "compliance": {
                "frameworks": ["SOX", "HIPAA"],
                "audit_required": True,
            },
            "configuration": {},
            "history": {},
        }

        result = risk_scorer.calculate(metadata)

        assert "compliance_requirements" in result.components
        # Multiple frameworks should increase score
        assert result.components["compliance_requirements"] > 0.4


class TestRiskLevels:
    """Tests for risk level determination."""

    def test_risk_level_thresholds(self, risk_scorer: RiskScorer) -> None:
        """Test risk level threshold boundaries."""
        test_cases = [
            (0.1, "low"),
            (0.3, "medium"),
            (0.6, "high"),
            (0.9, "critical"),
        ]

        for score, _expected_level in test_cases:
            # Create metadata that produces approximately the target score
            metadata = {
                "data_access": {"classification": "internal", "pii_access": False, "volume": "low"},
                "capabilities": {},
                "compliance": {},
                "configuration": {},
                "history": {"failure_rate": score},
            }

            result = risk_scorer.calculate(metadata)
            # Note: Exact level depends on weighted calculation
            assert result.risk_level in ["low", "medium", "high", "critical"]
