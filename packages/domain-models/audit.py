"""Audit log domain models."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Column, DateTime, Field as SQLField, SQLModel


class AuditLogBase(SQLModel):
    """Base audit log model."""

    event_type: str = SQLField(max_length=100, index=True)
    resource_type: str = SQLField(max_length=100, index=True)
    resource_id: UUID = SQLField(index=True)
    user_id: UUID | None = SQLField(default=None, foreign_key="user.id", index=True)
    action: str = SQLField(max_length=100)
    details: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(type_=dict))
    ip_address: str | None = SQLField(default=None, max_length=45)
    user_agent: str | None = SQLField(default=None, max_length=500)


class AuditLog(AuditLogBase, table=True):
    """Audit log entity stored in database."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    timestamp: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        index=True,
    )


class DataLineage(SQLModel, table=True):
    """Data lineage tracking for agent actions."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    agent_id: UUID = SQLField(foreign_key="agent.id", index=True)
    deployment_id: UUID | None = SQLField(default=None, foreign_key="deployment.id")
    source_type: str = SQLField(max_length=100)
    source_id: str = SQLField(max_length=255)
    destination_type: str = SQLField(max_length=100)
    destination_id: str = SQLField(max_length=255)
    data_classification: str = SQLField(max_length=50)
    transformation: str | None = SQLField(default=None, max_length=2000)
    timestamp: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        index=True,
    )
