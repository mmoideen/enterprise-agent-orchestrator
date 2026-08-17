"""Shared test fixtures and configuration."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.database import get_session
from apps.orchestrator.main import app
from apps.orchestrator.security import create_access_token, hash_password
from packages.domain_models.agent import Agent, AgentStatus
from packages.domain_models.policy import Policy, PolicyRule, PolicyStatus
from packages.domain_models.user import User, UserRole
from packages.governance_sdk.pii_detector import PIIDetector
from packages.governance_sdk.policy_engine import PolicyEngine
from packages.governance_sdk.risk_scorer import RiskScorer

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database session override."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession) -> User:
    """Create admin user for tests."""
    user = User(
        email="admin@test.com",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def developer_user(session: AsyncSession) -> User:
    """Create developer user for tests."""
    user = User(
        email="developer@test.com",
        full_name="Developer User",
        role=UserRole.DEVELOPER,
        is_active=True,
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(session: AsyncSession) -> User:
    """Create viewer user for tests."""
    user = User(
        email="viewer@test.com",
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True,
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create access token for admin user."""
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest.fixture
def developer_token(developer_user: User) -> str:
    """Create access token for developer user."""
    return create_access_token(data={"sub": str(developer_user.id)})


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    """Create access token for viewer user."""
    return create_access_token(data={"sub": str(viewer_user.id)})


@pytest_asyncio.fixture
async def sample_agent(session: AsyncSession, developer_user: User) -> Agent:
    """Create sample agent for tests."""
    agent = Agent(
        name="Test HR Agent",
        description="Test agent for HR operations",
        agent_type="hr",
        capabilities={"actions": ["onboard", "offboard"]},
        configuration={"runtime": "python", "resources": {"memory_mb": 512}},
        version="1.0.0",
        owner_id=developer_user.id,
        status=AgentStatus.DRAFT,
        risk_score=0.3,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def approved_agent(session: AsyncSession, developer_user: User, admin_user: User) -> Agent:
    """Create approved agent for tests."""
    agent = Agent(
        name="Approved Agent",
        description="Pre-approved test agent",
        agent_type="finance",
        capabilities={"actions": ["process_invoice"]},
        configuration={"runtime": "python", "resources": {"memory_mb": 512}},
        version="1.0.0",
        owner_id=developer_user.id,
        status=AgentStatus.APPROVED,
        risk_score=0.4,
        approved_by_id=admin_user.id,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def sample_policy(session: AsyncSession, admin_user: User) -> Policy:
    """Create sample policy for tests."""
    policy = Policy(
        name="Test Data Access Policy",
        description="Test policy for data access control",
        rules=[
            PolicyRule(
                rule_type="data_access",
                condition={"max_classification": "confidential"},
                action="review",
                severity="high",
            )
        ],
        scope="agent",
        priority=100,
        created_by_id=admin_user.id,
        status=PolicyStatus.ACTIVE,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


@pytest.fixture
def policy_engine(sample_policy: Policy) -> PolicyEngine:
    """Create policy engine with sample policy."""
    return PolicyEngine(policies=[sample_policy])


@pytest.fixture
def pii_detector() -> PIIDetector:
    """Create PII detector instance."""
    return PIIDetector()


@pytest.fixture
def risk_scorer() -> RiskScorer:
    """Create risk scorer instance."""
    return RiskScorer()


@pytest.fixture
def sample_agent_metadata() -> dict[str, Any]:
    """Sample agent metadata for risk scoring."""
    return {
        "data_access": {
            "classification": "confidential",
            "pii_access": True,
            "volume": "medium",
        },
        "capabilities": {
            "write_operations": True,
            "external_integrations": ["slack", "email"],
            "user_facing": True,
        },
        "compliance": {
            "frameworks": ["SOX", "GDPR"],
            "audit_required": True,
        },
        "configuration": {
            "dependencies": ["sqlmodel", "httpx"],
            "custom_code": True,
            "integration_points": 3,
        },
        "history": {
            "failure_rate": 0.1,
            "rollback_count": 1,
            "successful_deployments": 5,
        },
    }
