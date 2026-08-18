"""Tests for policy rule persistence via the PydanticListJSON column type."""

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.domain_models.policy import Policy, PolicyRule, PolicyStatus
from packages.domain_models.user import User


class TestPolicyRuleRoundTrip:
    """Tests that policy rules survive a database round trip as models."""

    @pytest.mark.asyncio
    async def test_rules_reload_as_models(self, session: AsyncSession, admin_user: User) -> None:
        """Test that stored rules come back as PolicyRule instances."""
        policy = Policy(
            name="Round Trip Policy",
            description="Persists a structured rule list",
            rules=[
                PolicyRule(
                    rule_type="risk_threshold",
                    condition={"max_risk_score": 0.7},
                    action="deny",
                    severity="critical",
                )
            ],
            scope="agent",
            priority=10,
            created_by_id=admin_user.id,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.commit()
        session.expunge_all()

        result = await session.execute(select(Policy).where(Policy.name == "Round Trip Policy"))
        loaded = result.scalar_one()

        assert len(loaded.rules) == 1
        rule = loaded.rules[0]
        assert isinstance(rule, PolicyRule)
        assert rule.rule_type == "risk_threshold"
        assert rule.condition == {"max_risk_score": 0.7}
        assert rule.action == "deny"
        assert rule.severity == "critical"
