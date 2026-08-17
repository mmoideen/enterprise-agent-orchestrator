"""Risk scoring module for evaluating agent deployment risk."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskScore:
    """Risk score calculation result."""

    total_score: float
    components: dict[str, float]
    risk_level: str
    recommendations: list[str]


class RiskScorer:
    """
    Calculate risk scores for agent deployments.

    This scorer evaluates multiple risk dimensions including data access,
    operational impact, compliance requirements, and technical complexity.
    """

    RISK_LEVELS = [
        (0.0, 0.25, "low"),
        (0.25, 0.50, "medium"),
        (0.50, 0.75, "high"),
        (0.75, 1.0, "critical"),
    ]

    WEIGHTS = {
        "data_sensitivity": 0.30,
        "operational_impact": 0.25,
        "compliance_requirements": 0.25,
        "technical_complexity": 0.15,
        "deployment_history": 0.05,
    }

    def calculate(self, agent_metadata: dict[str, Any]) -> RiskScore:
        """
        Calculate risk score for an agent deployment.

        Args:
            agent_metadata: Dictionary containing agent metadata for risk assessment.

        Returns:
            RiskScore object with detailed risk analysis.
        """
        components: dict[str, float] = {}

        # Data sensitivity score
        components["data_sensitivity"] = self._score_data_sensitivity(
            agent_metadata.get("data_access", {})
        )

        # Operational impact score
        components["operational_impact"] = self._score_operational_impact(
            agent_metadata.get("capabilities", {})
        )

        # Compliance requirements score
        components["compliance_requirements"] = self._score_compliance(
            agent_metadata.get("compliance", {})
        )

        # Technical complexity score
        components["technical_complexity"] = self._score_complexity(
            agent_metadata.get("configuration", {})
        )

        # Deployment history score
        components["deployment_history"] = self._score_history(
            agent_metadata.get("history", {})
        )

        # Calculate weighted total
        total_score = sum(
            components[key] * self.WEIGHTS.get(key, 0.0) for key in components
        )

        # Determine risk level
        risk_level = self._determine_risk_level(total_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(components, risk_level)

        return RiskScore(
            total_score=round(total_score, 3),
            components=components,
            risk_level=risk_level,
            recommendations=recommendations,
        )

    def _score_data_sensitivity(self, data_access: dict[str, Any]) -> float:
        """Score based on data sensitivity levels accessed."""
        classification = data_access.get("classification", "public")
        pii_access = data_access.get("pii_access", False)
        data_volume = data_access.get("volume", "low")

        score = 0.0

        # Classification scoring
        classification_scores = {
            "public": 0.1,
            "internal": 0.3,
            "confidential": 0.6,
            "restricted": 0.9,
        }
        score += classification_scores.get(classification, 0.5)

        # PII access penalty
        if pii_access:
            score += 0.3

        # Volume multiplier
        volume_multipliers = {"low": 1.0, "medium": 1.2, "high": 1.5}
        score *= volume_multipliers.get(data_volume, 1.0)

        return min(score, 1.0)

    def _score_operational_impact(self, capabilities: dict[str, Any]) -> float:
        """Score based on operational impact of agent capabilities."""
        write_operations = capabilities.get("write_operations", False)
        external_integrations = capabilities.get("external_integrations", [])
        user_facing = capabilities.get("user_facing", False)

        score = 0.2  # Base score

        if write_operations:
            score += 0.3

        if len(external_integrations) > 0:
            score += 0.1 * min(len(external_integrations), 5)

        if user_facing:
            score += 0.2

        return min(score, 1.0)

    def _score_compliance(self, compliance: dict[str, Any]) -> float:
        """Score based on compliance requirements."""
        frameworks = compliance.get("frameworks", [])
        audit_required = compliance.get("audit_required", False)
        certifications = compliance.get("certifications", [])

        score = 0.0

        # More frameworks = higher compliance burden
        score += 0.2 * min(len(frameworks), 3)

        if audit_required:
            score += 0.3

        if "sox" in [f.lower() for f in frameworks]:
            score += 0.2

        if "hipaa" in [f.lower() for f in frameworks]:
            score += 0.3

        return min(score, 1.0)

    def _score_complexity(self, configuration: dict[str, Any]) -> float:
        """Score based on technical complexity."""
        dependencies = configuration.get("dependencies", [])
        custom_code = configuration.get("custom_code", False)
        integration_points = configuration.get("integration_points", 0)

        score = 0.1  # Base complexity

        score += 0.1 * min(len(dependencies), 5)

        if custom_code:
            score += 0.3

        score += 0.1 * min(integration_points, 5)

        return min(score, 1.0)

    def _score_history(self, history: dict[str, Any]) -> float:
        """Score based on deployment history."""
        failure_rate = history.get("failure_rate", 0.0)
        rollback_count = history.get("rollback_count", 0)
        successful_deployments = history.get("successful_deployments", 0)

        score = failure_rate

        if rollback_count > 2:
            score += 0.3

        if successful_deployments > 10:
            score -= 0.2

        return max(min(score, 1.0), 0.0)

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        for min_score, max_score, level in self.RISK_LEVELS:
            if min_score <= score <= max_score:
                return level
        return "unknown"

    def _generate_recommendations(
        self, components: dict[str, float], risk_level: str
    ) -> list[str]:
        """Generate risk mitigation recommendations."""
        recommendations: list[str] = []

        if components.get("data_sensitivity", 0) > 0.6:
            recommendations.append(
                "Implement additional data access controls and audit logging"
            )

        if components.get("operational_impact", 0) > 0.7:
            recommendations.append(
                "Consider phased rollout with canary deployment strategy"
            )

        if components.get("compliance_requirements", 0) > 0.5:
            recommendations.append(
                "Schedule compliance review before production deployment"
            )

        if components.get("technical_complexity", 0) > 0.6:
            recommendations.append(
                "Conduct thorough integration testing and code review"
            )

        if risk_level in ["high", "critical"]:
            recommendations.append(
                "Require multi-level approval before deployment"
            )
            recommendations.append(
                "Set up comprehensive monitoring and alerting"
            )

        return recommendations
