"""upgrades: llm_reviews, scan_results, developer_stats, risk fields, memory fields

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # Add risk fields to pull_requests
    op.add_column("pull_requests", sa.Column("risk_level", sa.String(), nullable=True))
    op.add_column("pull_requests", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("pull_requests", sa.Column("risk_factors", sa.JSON(), nullable=True))

    # Add consensus field + models_used to reviews
    op.add_column("reviews", sa.Column("consensus_score", sa.Float(), nullable=True))
    op.add_column("reviews", sa.Column("models_used", sa.JSON(), nullable=True))
    # Rename model_used -> models_used handled above; drop old col if exists
    try:
        op.drop_column("reviews", "model_used")
        op.drop_column("reviews", "raw_ai_response")
    except Exception:
        pass

    # Add semantic memory fields to repositories
    op.add_column("repositories", sa.Column("architecture_docs", sa.Text(), nullable=True))
    op.add_column("repositories", sa.Column("coding_standards", sa.Text(), nullable=True))
    op.add_column("repositories", sa.Column("team_conventions", sa.Text(), nullable=True))

    # New table: llm_reviews
    op.create_table(
        "llm_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("issues", sa.JSON(), nullable=True),
        sa.Column("suggestions", sa.JSON(), nullable=True),
        sa.Column("security_flags", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), default=0),
        sa.Column("latency_ms", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # New table: scan_results
    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("scanner", sa.String(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # New table: developer_stats
    op.create_table(
        "developer_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("username", sa.String(), nullable=False, index=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("total_prs", sa.Integer(), default=0),
        sa.Column("avg_score", sa.Float(), default=0.0),
        sa.Column("total_issues", sa.Integer(), default=0),
        sa.Column("critical_issues", sa.Integer(), default=0),
        sa.Column("security_issues", sa.Integer(), default=0),
        sa.Column("score_trend", sa.Float(), default=0.0),
        sa.Column("streak_days", sa.Integer(), default=0),
        sa.Column("badges", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("developer_stats")
    op.drop_table("scan_results")
    op.drop_table("llm_reviews")
    try:
        op.drop_column("repositories", "team_conventions")
        op.drop_column("repositories", "coding_standards")
        op.drop_column("repositories", "architecture_docs")
        op.drop_column("reviews", "models_used")
        op.drop_column("reviews", "consensus_score")
        op.drop_column("pull_requests", "risk_factors")
        op.drop_column("pull_requests", "risk_score")
        op.drop_column("pull_requests", "risk_level")
    except Exception:
        pass
