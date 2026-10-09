"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_id", sa.String(), unique=True, nullable=False),
        sa.Column("username", sa.String(), unique=True, nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("github_access_token", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("github_repo_id", sa.String(), unique=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("is_private", sa.Boolean(), default=False),
        sa.Column("is_indexed", sa.Boolean(), default=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("github_pr_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("author_avatar", sa.String(), nullable=True),
        sa.Column("base_branch", sa.String(), nullable=False),
        sa.Column("head_branch", sa.String(), nullable=False),
        sa.Column("diff_url", sa.String(), nullable=True),
        sa.Column("files_changed", sa.Integer(), default=0),
        sa.Column("additions", sa.Integer(), default=0),
        sa.Column("deletions", sa.Integer(), default=0),
        sa.Column("status", sa.String(), default="pending"),
        sa.Column("github_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("issues", sa.JSON(), default=list),
        sa.Column("suggestions", sa.JSON(), default=list),
        sa.Column("security_flags", sa.JSON(), default=list),
        sa.Column("metrics", sa.JSON(), default=dict),
        sa.Column("raw_ai_response", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(), default="groq"),
        sa.Column("tokens_used", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "codebase_indices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), unique=True),
        sa.Column("total_files", sa.Integer(), default=0),
        sa.Column("total_chunks", sa.Integer(), default=0),
        sa.Column("status", sa.String(), default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table("codebase_indices")
    op.drop_table("chat_messages")
    op.drop_table("reviews")
    op.drop_table("pull_requests")
    op.drop_table("repositories")
    op.drop_table("users")
