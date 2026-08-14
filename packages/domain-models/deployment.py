"""Deployment domain models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field
from sqlmodel import Column, DateTime, Field as SQLField, Relationship, SQLModel


class DeploymentStatus(str, Enum):
    """Deployment lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentBase(SQLModel):
    """Base deployment model."""

    agent_id: UUID = SQLField(foreign_key="agent.id", index=True)
    environment: str = SQLField(max_length=50, index=True)
    configuration: dict[str, Any] = SQLField(
        default_factory=dict, sa_column=Column(type_=dict)
    )
    triggered_by_id: UUID = SQLField(foreign_key="user.id")


class Deployment(DeploymentBase, table=True):
    """Deployment entity stored in database."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    status: DeploymentStatus = SQLField(default=DeploymentStatus.PENDING, index=True)
    started_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = SQLField(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    error_message: str | None = SQLField(default=None, max_length=2000)
    workflow_id: str | None = SQLField(default=None, max_length=255, index=True)
    run_id: str | None = SQLField(default=None, max_length=255)

    # Relationships
    agent: "Agent" = Relationship(back_populates="deployments")  # type: ignore


class DeploymentCreate(DeploymentBase):
    """Model for creating a new deployment."""

    pass
