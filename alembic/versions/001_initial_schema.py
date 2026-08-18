"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user table
    op.create_table(
        "user",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "DEVELOPER", "APPROVER", "VIEWER", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # Create agent table
    op.create_table(
        "agent",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("agent_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("capabilities", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING_APPROVAL",
                "APPROVED",
                "DEPLOYED",
                "SUSPENDED",
                "ARCHIVED",
                name="agentstatus",
            ),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_name"), "agent", ["name"], unique=False)
    op.create_index(op.f("ix_agent_agent_type"), "agent", ["agent_type"], unique=False)
    op.create_index(op.f("ix_agent_status"), "agent", ["status"], unique=False)
    op.create_index(op.f("ix_agent_owner_id"), "agent", ["owner_id"], unique=False)

    # Create deployment table
    op.create_table(
        "deployment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("environment", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("configuration", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("triggered_by_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "RUNNING", "COMPLETED", "FAILED", "ROLLED_BACK", name="deploymentstatus"
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("workflow_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("run_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.id"],
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deployment_agent_id"), "deployment", ["agent_id"], unique=False)
    op.create_index(op.f("ix_deployment_environment"), "deployment", ["environment"], unique=False)
    op.create_index(op.f("ix_deployment_status"), "deployment", ["status"], unique=False)
    op.create_index(op.f("ix_deployment_workflow_id"), "deployment", ["workflow_id"], unique=False)

    # Create policy table
    op.create_table(
        "policy",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("rules", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("scope", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column(
            "status", sa.Enum("ACTIVE", "INACTIVE", "DRAFT", name="policystatus"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policy_name"), "policy", ["name"], unique=False)
    op.create_index(op.f("ix_policy_scope"), "policy", ["scope"], unique=False)
    op.create_index(op.f("ix_policy_status"), "policy", ["status"], unique=False)

    # Create auditlog table
    op.create_table(
        "auditlog",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("resource_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("user_agent", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditlog_event_type"), "auditlog", ["event_type"], unique=False)
    op.create_index(op.f("ix_auditlog_resource_type"), "auditlog", ["resource_type"], unique=False)
    op.create_index(op.f("ix_auditlog_resource_id"), "auditlog", ["resource_id"], unique=False)
    op.create_index(op.f("ix_auditlog_user_id"), "auditlog", ["user_id"], unique=False)
    op.create_index(op.f("ix_auditlog_timestamp"), "auditlog", ["timestamp"], unique=False)

    # Create datalineage table
    op.create_table(
        "datalineage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("deployment_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("source_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("destination_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("destination_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "data_classification", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column("transformation", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.id"],
        ),
        sa.ForeignKeyConstraint(
            ["deployment_id"],
            ["deployment.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_datalineage_agent_id"), "datalineage", ["agent_id"], unique=False)
    op.create_index(op.f("ix_datalineage_timestamp"), "datalineage", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_table("datalineage")
    op.drop_table("auditlog")
    op.drop_table("policy")
    op.drop_table("deployment")
    op.drop_table("agent")
    op.drop_table("user")
