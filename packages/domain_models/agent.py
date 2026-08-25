"""Agent domain models."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, DateTime, Relationship, SQLModel
from sqlmodel import Field as SQLField

if TYPE_CHECKING:
    from packages.domain_models.deployment import Deployment


class AgentStatus(StrEnum):
    """Agent lifecycle status."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class AgentBase(SQLModel):
    """Base agent model with shared fields."""

    name: str = SQLField(index=True, min_length=1, max_length=255)
    description: str = SQLField(max_length=2000)
    agent_type: str = SQLField(index=True, max_length=100)
    capabilities: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))
    configuration: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))
    version: str = SQLField(default="1.0.0", max_length=50)
    tags: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))


class Agent(AgentBase, table=True):
    """Agent entity stored in database."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    owner_id: UUID = SQLField(foreign_key="user.id", index=True)
    status: AgentStatus = SQLField(default=AgentStatus.DRAFT, index=True)
    risk_score: float = SQLField(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow),
    )
    approved_at: datetime | None = SQLField(default=None, sa_column=Column(DateTime(timezone=True)))
    approved_by_id: UUID | None = SQLField(default=None, foreign_key="user.id")

    # Relationships
    deployments: list["Deployment"] = Relationship(back_populates="agent")


class AgentCreate(AgentBase):
    """Model for creating a new agent.

    ``owner_id`` is not accepted from clients; it is taken from the
    authenticated caller.
    """

    pass


class AgentUpdate(SQLModel):
    """Model for updating an agent."""

    name: str | None = None
    description: str | None = None
    capabilities: dict[str, Any] | None = None
    configuration: dict[str, Any] | None = None
    version: str | None = None
    tags: list[str] | None = None


class AgentVersion(SQLModel):
    """Agent version snapshot for auditing."""

    agent_id: UUID
    version: str
    snapshot: dict[str, Any]
    created_at: datetime
    created_by_id: UUID
