"""Policy engine for evaluating governance policies."""

import re
from dataclasses import dataclass
from typing import Any

from packages.domain_models.policy import Policy, PolicyRule


@dataclass
class PolicyEvaluationResult:
    """Result of a policy evaluation."""

    allowed: bool
    matched_rules: list[PolicyRule]
    actions: list[str]
    violations: list[str]
    metadata: dict[str, Any]


class PolicyEngine:
    """
    Policy engine that evaluates agent actions against governance policies.

    This engine supports various rule types including data access controls,
    PII detection requirements, and risk thresholds. Policies are evaluated
    in priority order, with higher priority policies taking precedence.
    """

    def __init__(self, policies: list[Policy]) -> None:
        """
        Initialize the policy engine with a list of active policies.

        Args:
            policies: List of Policy objects to evaluate against.
        """
        self.policies = sorted(
            [p for p in policies if p.status.value == "active"],
            key=lambda p: p.priority,
            reverse=True,
        )

    def evaluate(
        self, context: dict[str, Any], scope: str = "global"
    ) -> PolicyEvaluationResult:
        """
        Evaluate policies against a given context.

        Args:
            context: Dictionary containing the evaluation context (agent, action, data, etc.)
            scope: Scope to filter policies (e.g., "agent", "deployment", "global")

        Returns:
            PolicyEvaluationResult with evaluation outcome and matched rules.
        """
        matched_rules: list[PolicyRule] = []
        actions: list[str] = []
        violations: list[str] = []
        allowed = True

        applicable_policies = [p for p in self.policies if p.scope == scope or p.scope == "global"]

        for policy in applicable_policies:
            for rule in policy.rules:
                if self._evaluate_rule(rule, context):
                    matched_rules.append(rule)
                    actions.append(rule.action)

                    if rule.action == "deny":
                        allowed = False
                        violations.append(
                            f"Policy '{policy.name}' denied: {rule.rule_type}"
                        )
                    elif rule.action == "review":
                        allowed = False
                        violations.append(
                            f"Policy '{policy.name}' requires review: {rule.rule_type}"
                        )

        return PolicyEvaluationResult(
            allowed=allowed,
            matched_rules=matched_rules,
            actions=list(set(actions)),
            violations=violations,
            metadata={"evaluated_policies": len(applicable_policies)},
        )

    def _evaluate_rule(self, rule: PolicyRule, context: dict[str, Any]) -> bool:
        """
        Evaluate a single policy rule against context.

        Args:
            rule: PolicyRule to evaluate
            context: Evaluation context

        Returns:
            True if the rule matches the context, False otherwise.
        """
        condition = rule.condition

        if rule.rule_type == "data_access":
            return self._check_data_access(condition, context)
        elif rule.rule_type == "pii_detection":
            return self._check_pii_requirement(condition, context)
        elif rule.rule_type == "risk_threshold":
            return self._check_risk_threshold(condition, context)
        elif rule.rule_type == "agent_type":
            return self._check_agent_type(condition, context)

        return False

    def _check_data_access(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if data access conditions are met."""
        required_classification = condition.get("max_classification")
        data_classification = context.get("data_classification")

        if not required_classification or not data_classification:
            return False

        classification_levels = ["public", "internal", "confidential", "restricted"]
        try:
            required_level = classification_levels.index(required_classification)
            actual_level = classification_levels.index(data_classification)
            return actual_level > required_level
        except ValueError:
            return False

    def _check_pii_requirement(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if PII detection requirements are met."""
        requires_scanning = condition.get("requires_scanning", False)
        has_pii = context.get("contains_pii", False)

        return requires_scanning and has_pii

    def _check_risk_threshold(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if risk score exceeds threshold."""
        threshold = condition.get("max_risk_score", 1.0)
        risk_score = context.get("risk_score", 0.0)

        return risk_score > threshold

    def _check_agent_type(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if agent type matches condition."""
        allowed_types = condition.get("allowed_types", [])
        agent_type = context.get("agent_type")

        if not agent_type:
            return False

        return agent_type in allowed_types
