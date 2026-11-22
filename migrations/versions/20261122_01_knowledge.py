"""Add tenant-scoped AI skill and brand knowledge tables.

Revision ID: 20261122_01
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_memberships",
        sa.Column("tenant_id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.String(100), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
    )
    op.create_index("ix_knowledge_memberships_owner", "knowledge_memberships", ["owner_id"])

    op.create_table(
        "knowledge_skill_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", "version", name="uq_knowledge_skill_version"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_knowledge_skill_id_tenant"),
    )
    op.create_index("ix_knowledge_skills_tenant", "knowledge_skill_versions", ["tenant_id"])

    op.create_table(
        "knowledge_agent_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tenant_id", "agent_key", "skill_id", name="uq_knowledge_agent_grant"),
        sa.ForeignKeyConstraint(
            ["skill_id", "tenant_id"],
            ["knowledge_skill_versions.id", "knowledge_skill_versions.tenant_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_knowledge_grants_tenant_agent", "knowledge_agent_grants",
                    ["tenant_id", "agent_key"])

    op.create_table(
        "knowledge_brand_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("brand_id", sa.String(100), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "brand_id", "revision", name="uq_knowledge_brand_revision"),
    )
    op.create_index("ix_knowledge_brands_tenant_brand", "knowledge_brand_revisions",
                    ["tenant_id", "brand_id"])

    op.create_table(
        "knowledge_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("object_key", sa.String(240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_audit_tenant_time", "knowledge_audit",
                    ["tenant_id", "created_at"])


def downgrade():
    op.drop_index("ix_knowledge_audit_tenant_time", "knowledge_audit")
    op.drop_table("knowledge_audit")
    op.drop_index("ix_knowledge_brands_tenant_brand", "knowledge_brand_revisions")
    op.drop_table("knowledge_brand_revisions")
    op.drop_index("ix_knowledge_grants_tenant_agent", "knowledge_agent_grants")
    op.drop_table("knowledge_agent_grants")
    op.drop_index("ix_knowledge_skills_tenant", "knowledge_skill_versions")
    op.drop_table("knowledge_skill_versions")
    op.drop_index("ix_knowledge_memberships_owner", "knowledge_memberships")
    op.drop_table("knowledge_memberships")
