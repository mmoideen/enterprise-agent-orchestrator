#!/usr/bin/env python3
"""
Seed database with demo data.

Creates sample users, agents, and policies for development and testing.
"""

import asyncio

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.database import async_engine
from apps.orchestrator.security import hash_password
from packages.domain_models.agent import Agent, AgentStatus
from packages.domain_models.policy import Policy, PolicyRule, PolicyStatus
from packages.domain_models.user import User, UserRole


async def seed_data() -> None:
    """Seed the database with demo data."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        print("Seeding demo data...")

        # Create demo users
        print("Creating demo users...")

        # Check if users already exist
        result = await session.execute(select(User).where(User.email == "admin@demo.com"))
        if result.scalar_one_or_none():
            print("Demo users already exist, skipping user creation")
        else:
            admin = User(
                email="admin@demo.com",
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_active=True,
                hashed_password=hash_password("admin123"),
            )

            developer = User(
                email="developer@demo.com",
                full_name="Developer User",
                role=UserRole.DEVELOPER,
                is_active=True,
                hashed_password=hash_password("dev123"),
            )

            approver = User(
                email="approver@demo.com",
                full_name="Approver User",
                role=UserRole.APPROVER,
                is_active=True,
                hashed_password=hash_password("approver123"),
            )

            viewer = User(
                email="viewer@demo.com",
                full_name="Viewer User",
                role=UserRole.VIEWER,
                is_active=True,
                hashed_password=hash_password("viewer123"),
            )

            session.add_all([admin, developer, approver, viewer])
            await session.commit()
            await session.refresh(admin)
            await session.refresh(developer)

            print("✓ Created 4 demo users")
            print("  - admin@demo.com / admin123 (ADMIN)")
            print("  - developer@demo.com / dev123 (DEVELOPER)")
            print("  - approver@demo.com / approver123 (APPROVER)")
            print("  - viewer@demo.com / viewer123 (VIEWER)")

        # Get existing users for agent/policy creation
        result = await session.execute(select(User).where(User.email == "developer@demo.com"))
        developer_user: User | None = result.scalar_one_or_none()

        result = await session.execute(select(User).where(User.email == "admin@demo.com"))
        admin_user: User | None = result.scalar_one_or_none()

        if not developer_user or not admin_user:
            print("Error: Could not find demo users")
            return

        # Create demo agents
        print("\nCreating demo agents...")

        result = await session.execute(select(Agent).where(Agent.name == "HR Automation Agent"))
        if result.scalar_one_or_none():
            print("Demo agents already exist, skipping agent creation")
        else:
            hr_agent = Agent(
                name="HR Automation Agent",
                description="Automates employee onboarding, offboarding, and PTO management",
                agent_type="hr",
                capabilities={
                    "actions": [
                        "onboard_employee",
                        "offboard_employee",
                        "process_pto_request",
                        "query_benefits",
                    ]
                },
                configuration={
                    "runtime": "python",
                    "resources": {"memory_mb": 512, "cpu_cores": 1},
                    "data_access": {
                        "classification": "confidential",
                        "pii_access": True,
                        "volume": "medium",
                    },
                    "compliance": {
                        "frameworks": ["SOX"],
                        "audit_required": True,
                    },
                },
                version="1.0.0",
                owner_id=developer_user.id,
                status=AgentStatus.APPROVED,
                risk_score=0.45,
                approved_by_id=admin_user.id,
                tags=["hr", "automation", "demo"],
            )

            finance_agent = Agent(
                name="Finance Operations Agent",
                description="Processes invoices, approves expenses, and generates financial reports",
                agent_type="finance",
                capabilities={
                    "actions": [
                        "process_invoice",
                        "approve_expense",
                        "analyze_budget_variance",
                        "generate_financial_report",
                    ]
                },
                configuration={
                    "runtime": "python",
                    "resources": {"memory_mb": 1024, "cpu_cores": 2},
                    "data_access": {
                        "classification": "confidential",
                        "pii_access": False,
                        "volume": "high",
                    },
                    "compliance": {
                        "frameworks": ["SOX", "GDPR"],
                        "audit_required": True,
                    },
                },
                version="1.0.0",
                owner_id=developer_user.id,
                status=AgentStatus.PENDING_APPROVAL,
                risk_score=0.62,
                tags=["finance", "automation", "demo"],
            )

            compliance_agent = Agent(
                name="Compliance Monitoring Agent",
                description="Detects policy violations, generates audit trails, and assesses compliance risk",
                agent_type="compliance",
                capabilities={
                    "actions": [
                        "detect_policy_violations",
                        "generate_audit_trail",
                        "create_regulatory_report",
                        "assess_compliance_risk",
                    ]
                },
                configuration={
                    "runtime": "python",
                    "resources": {"memory_mb": 2048, "cpu_cores": 2},
                    "data_access": {
                        "classification": "restricted",
                        "pii_access": True,
                        "volume": "high",
                    },
                    "compliance": {
                        "frameworks": ["SOX", "GDPR", "HIPAA"],
                        "audit_required": True,
                    },
                },
                version="1.0.0",
                owner_id=developer_user.id,
                status=AgentStatus.DRAFT,
                risk_score=0.78,
                tags=["compliance", "security", "demo"],
            )

            session.add_all([hr_agent, finance_agent, compliance_agent])
            await session.commit()

            print("✓ Created 3 demo agents")
            print("  - HR Automation Agent (APPROVED, risk: 0.45)")
            print("  - Finance Operations Agent (PENDING_APPROVAL, risk: 0.62)")
            print("  - Compliance Monitoring Agent (DRAFT, risk: 0.78)")

        # Create demo policies
        print("\nCreating demo policies...")

        result = await session.execute(select(Policy).where(Policy.name == "PII Access Control"))
        if result.scalar_one_or_none():
            print("Demo policies already exist, skipping policy creation")
        else:
            pii_policy = Policy(
                name="PII Access Control",
                description="Requires review for agents accessing personally identifiable information",
                rules=[
                    PolicyRule(
                        rule_type="pii_detection",
                        condition={"requires_scanning": True},
                        action="review",
                        severity="high",
                    )
                ],
                scope="agent",
                priority=100,
                created_by_id=admin_user.id,
                status=PolicyStatus.ACTIVE,
            )

            high_risk_policy = Policy(
                name="High Risk Deployment Block",
                description="Blocks deployment of agents with risk score above 0.75",
                rules=[
                    PolicyRule(
                        rule_type="risk_threshold",
                        condition={"max_risk_score": 0.75},
                        action="deny",
                        severity="critical",
                    )
                ],
                scope="global",
                priority=200,
                created_by_id=admin_user.id,
                status=PolicyStatus.ACTIVE,
            )

            restricted_data_policy = Policy(
                name="Restricted Data Access Control",
                description="Requires executive approval for restricted data access",
                rules=[
                    PolicyRule(
                        rule_type="data_access",
                        condition={"max_classification": "confidential"},
                        action="review",
                        severity="high",
                    )
                ],
                scope="agent",
                priority=150,
                created_by_id=admin_user.id,
                status=PolicyStatus.ACTIVE,
            )

            session.add_all([pii_policy, high_risk_policy, restricted_data_policy])
            await session.commit()

            print("✓ Created 3 demo policies")
            print("  - PII Access Control (priority: 100)")
            print("  - High Risk Deployment Block (priority: 200)")
            print("  - Restricted Data Access Control (priority: 150)")

        print("\n========================================")
        print("✓ Demo data seeding complete!")
        print("========================================")
        print("\nYou can now log in with:")
        print("  Email: admin@demo.com")
        print("  Password: admin123")


if __name__ == "__main__":
    asyncio.run(seed_data())
