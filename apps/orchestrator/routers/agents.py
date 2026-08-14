"""Agent management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.audit import create_audit_log
from apps.orchestrator.database import get_session
from apps.orchestrator.security import get_current_user, require_role
from packages.domain_models.agent import Agent, AgentCreate, AgentStatus, AgentUpdate
from packages.domain_models.user import User, UserRole
from packages.governance_sdk.risk_scorer import RiskScorer


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Agent:
    """
    Create a new agent.

    This endpoint creates an agent in DRAFT status. The agent must go through
    an approval workflow before it can be deployed.
    """
    # Calculate initial risk score
    risk_scorer = RiskScorer()
    risk_score = risk_scorer.calculate(
        {
            "data_access": agent_data.configuration.get("data_access", {}),
            "capabilities": agent_data.capabilities,
            "compliance": agent_data.configuration.get("compliance", {}),
            "configuration": agent_data.configuration,
            "history": {},
        }
    )

    agent = Agent(
        **agent_data.model_dump(),
        owner_id=current_user.id,
        status=AgentStatus.DRAFT,
        risk_score=risk_score.total_score,
    )

    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    # Create audit log
    await create_audit_log(
        session=session,
        event_type="agent.created",
        resource_type="agent",
        resource_id=agent.id,
        action="create",
        user_id=current_user.id,
        details={
            "agent_name": agent.name,
            "agent_type": agent.agent_type,
            "risk_score": agent.risk_score,
        },
    )

    return agent


@router.get("/", response_model=list[Agent])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    status_filter: AgentStatus | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Agent]:
    """
    List all agents.

    Supports pagination and filtering by status.
    """
    query = select(Agent)

    if status_filter:
        query = query.where(Agent.status == status_filter)

    # Non-admin users can only see their own agents
    if current_user.role not in [UserRole.ADMIN, UserRole.APPROVER]:
        query = query.where(Agent.owner_id == current_user.id)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    agents = result.scalars().all()

    return list(agents)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Agent:
    """Get a specific agent by ID."""
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check authorization
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.APPROVER]
        and agent.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view this agent")

    return agent


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Agent:
    """
    Update an agent.

    Only agents in DRAFT status can be updated. Deployed agents require
    versioning and redeployment.
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check authorization
    if agent.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this agent")

    # Only DRAFT agents can be updated
    if agent.status != AgentStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only agents in DRAFT status can be updated. "
            "Create a new version for deployed agents.",
        )

    # Update fields
    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    # Recalculate risk score if configuration changed
    if "configuration" in update_data or "capabilities" in update_data:
        risk_scorer = RiskScorer()
        risk_score = risk_scorer.calculate(
            {
                "data_access": agent.configuration.get("data_access", {}),
                "capabilities": agent.capabilities,
                "compliance": agent.configuration.get("compliance", {}),
                "configuration": agent.configuration,
                "history": {},
            }
        )
        agent.risk_score = risk_score.total_score

    await session.commit()
    await session.refresh(agent)

    # Create audit log
    await create_audit_log(
        session=session,
        event_type="agent.updated",
        resource_type="agent",
        resource_id=agent.id,
        action="update",
        user_id=current_user.id,
        details={"updated_fields": list(update_data.keys())},
    )

    return agent


@router.post("/{agent_id}/submit-approval", response_model=Agent)
async def submit_for_approval(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Agent:
    """
    Submit an agent for approval.

    Transitions the agent from DRAFT to PENDING_APPROVAL status.
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Not authorized to submit this agent for approval"
        )

    if agent.status != AgentStatus.DRAFT:
        raise HTTPException(
            status_code=400, detail="Only DRAFT agents can be submitted for approval"
        )

    agent.status = AgentStatus.PENDING_APPROVAL

    await session.commit()
    await session.refresh(agent)

    await create_audit_log(
        session=session,
        event_type="agent.submitted_for_approval",
        resource_type="agent",
        resource_id=agent.id,
        action="submit_approval",
        user_id=current_user.id,
    )

    return agent


@router.post("/{agent_id}/approve", response_model=Agent)
async def approve_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(
        lambda: require_role([UserRole.ADMIN, UserRole.APPROVER], get_current_user)
    ),
) -> Agent:
    """
    Approve an agent for deployment.

    Only users with ADMIN or APPROVER role can approve agents.
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status != AgentStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400, detail="Only agents pending approval can be approved"
        )

    agent.status = AgentStatus.APPROVED
    agent.approved_by_id = current_user.id

    await session.commit()
    await session.refresh(agent)

    await create_audit_log(
        session=session,
        event_type="agent.approved",
        resource_type="agent",
        resource_id=agent.id,
        action="approve",
        user_id=current_user.id,
    )

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Archive an agent.

    Agents are never hard-deleted for audit purposes.
    """
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this agent")

    if agent.status == AgentStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Cannot delete deployed agents")

    agent.status = AgentStatus.ARCHIVED

    await session.commit()

    await create_audit_log(
        session=session,
        event_type="agent.archived",
        resource_type="agent",
        resource_id=agent.id,
        action="archive",
        user_id=current_user.id,
    )
