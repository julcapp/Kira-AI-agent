"""Durable orchestrator jobs, steps and MAX notifications.

Revision ID: 20261122_02
Revises: 20261122_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_02"
down_revision = "20261122_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.String(100), nullable=False),
        sa.Column("request", sa.Text, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_work_jobs_owner_id", "work_jobs", ["owner_id"])
    op.create_index("ix_work_jobs_status_created", "work_jobs", ["status", "created_at"])
    op.create_table(
        "work_steps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("work_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("request", sa.Text, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.UniqueConstraint("job_id", "position", name="uq_work_step_position"),
    )
    op.create_index("ix_work_steps_job", "work_steps", ["job_id"])
    op.create_table(
        "work_notices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("work_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.String(100), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.UniqueConstraint("job_id", name="uq_work_notice_job"),
    )


def downgrade():
    op.drop_table("work_notices")
    op.drop_index("ix_work_steps_job", table_name="work_steps")
    op.drop_table("work_steps")
    op.drop_index("ix_work_jobs_status_created", table_name="work_jobs")
    op.drop_index("ix_work_jobs_owner_id", table_name="work_jobs")
    op.drop_table("work_jobs")
