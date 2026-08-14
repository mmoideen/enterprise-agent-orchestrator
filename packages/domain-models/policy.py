"""Policy domain models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field
from sqlmodel import Column, DateTime, Field as SQLField, SQLModel


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class PolicyRule(SQLModel):
    """Individual policy rule specification."""

    rule_type: str = Field(description="Type of rule: data_access, pii_detection, risk_threshold")
    condition: dict[str, Any] = Field(description="Condition to evaluate")
    action: str = Field(description="Action to take: allow, deny, review, redact")
    severity: str = Field(default="medium", description="Severity: low, medium, high, critical")


class PolicyBase(SQLModel):
    """Base policy model."""

    name: str = SQLField(index=True, max_length=255)
    description: str = SQLField(max_length=2000)
    rules: list[PolicyRule] = SQLField(default_factory=list, sa_column=Column(type_=list))
    scope: str = SQLField(max_length=100, index=True)
    priority: int = SQLField(default=0)
    created_by_id: UUID = SQLField(foreign_key="user.id")


class Policy(PolicyBase, table=True):
    """Policy entity stored in database."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    status: PolicyStatus = SQLField(default=PolicyStatus.DRAFT, index=True)
    created_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow),
    )
    version: int = SQLField(default=1)


class PolicyCreate(PolicyBase):
    """Model for creating a new policy."""

    pass
