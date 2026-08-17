"""Deployment management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from apps.orchestrator.audit import create_audit_log
from apps.orchestrator.config import settings
from apps.orchestrator.database import get_session
from apps.orchestrator.security import get_current_user
from packages.domain_models.agent import Agent, AgentStatus
from packages.domain_models.deployment import Deployment, DeploymentCreate, DeploymentStatus
from packages.domain_models.user import User, UserRole

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("/", response_model=Deployment, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment_data: DeploymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Deployment:
    """
    Create and trigger a new agent deployment.

    This endpoint validates the agent is approved, creates a deployment record,
    and triggers a Temporal workflow to handle the deployment lifecycle.
    """
    # Verify agent exists and is approved
    result = await session.execute(select(Agent).where(Agent.id == deployment_data.agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status != AgentStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Only approved agents can be deployed",
        )

    # Check risk score threshold
    if agent.risk_score > settings.risk_score_threshold:
        raise HTTPException(
            status_code=400,
            detail=f"Agent risk score ({agent.risk_score}) exceeds threshold "
            f"({settings.risk_score_threshold}). Additional approval required.",
        )

    # Create deployment record
    deployment = Deployment(
        **deployment_data.model_dump(),
        triggered_by_id=current_user.id,
        status=DeploymentStatus.PENDING,
    )

    session.add(deployment)
    await session.commit()
    await session.refresh(deployment)

    # Trigger Temporal workflow
    # Note: In a real implementation, we would connect to Temporal here
    # For this reference architecture, we'll simulate the workflow ID
    workflow_id = f"deployment-{deployment.id}"
    deployment.workflow_id = workflow_id
    deployment.run_id = f"run-{deployment.id}"
    deployment.status = DeploymentStatus.RUNNING

    await session.commit()
    await session.refresh(deployment)

    # Create audit log
    await create_audit_log(
        session=session,
        event_type="deployment.created",
        resource_type="deployment",
        resource_id=deployment.id,
        action="create",
        user_id=current_user.id,
        details={
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "environment": deployment.environment,
            "workflow_id": workflow_id,
        },
    )

    return deployment


@router.get("/", response_model=list[Deployment])
async def list_deployments(
    skip: int = 0,
    limit: int = 100,
    agent_id: UUID | None = None,
    environment: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Deployment]:
    """
    List deployments.

    Supports filtering by agent ID and environment.
    """
    query = select(Deployment)

    if agent_id:
        query = query.where(Deployment.agent_id == agent_id)

    if environment:
        query = query.where(Deployment.environment == environment)

    # Non-admin users can only see deployments they triggered
    if current_user.role not in [UserRole.ADMIN, UserRole.APPROVER]:
        query = query.where(Deployment.triggered_by_id == current_user.id)

    query = query.offset(skip).limit(limit).order_by(col(Deployment.started_at).desc())
    result = await session.execute(query)
    deployments = result.scalars().all()

    return list(deployments)


@router.get("/{deployment_id}", response_model=Deployment)
async def get_deployment(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Deployment:
    """Get a specific deployment by ID."""
    result = await session.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment: Deployment | None = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Check authorization
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.APPROVER]
        and deployment.triggered_by_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view this deployment")

    return deployment


@router.post("/{deployment_id}/rollback", response_model=Deployment)
async def rollback_deployment(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Deployment:
    """
    Rollback a deployment.

    Triggers a compensating workflow to undo the deployment changes.
    """
    result = await session.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment: Deployment | None = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Only admins and approvers can rollback
    if current_user.role not in [UserRole.ADMIN, UserRole.APPROVER]:
        raise HTTPException(status_code=403, detail="Not authorized to rollback deployments")

    if deployment.status not in [DeploymentStatus.RUNNING, DeploymentStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Only running or completed deployments can be rolled back",
        )

    # Trigger rollback workflow
    # Note: In a real implementation, we would trigger a Temporal compensating workflow
    deployment.status = DeploymentStatus.ROLLED_BACK

    await session.commit()
    await session.refresh(deployment)

    # Create audit log
    await create_audit_log(
        session=session,
        event_type="deployment.rolled_back",
        resource_type="deployment",
        resource_id=deployment.id,
        action="rollback",
        user_id=current_user.id,
    )

    return deployment
