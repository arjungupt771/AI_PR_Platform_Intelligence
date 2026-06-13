from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Float, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ReviewSeverity(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    suggestion = "suggestion"
    info = "info"


class PRStatus(str, enum.Enum):
    pending = "pending"
    reviewing = "reviewing"
    completed = "completed"
    failed = "failed"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    github_access_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    repos = relationship("Repository", back_populates="owner")
    reviews = relationship("Review", back_populates="reviewer")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    github_repo_id = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    is_private = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    webhook_id = Column(String, nullable=True)

    # Semantic memory metadata
    architecture_docs = Column(Text, nullable=True)
    coding_standards = Column(Text, nullable=True)
    team_conventions = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="repos")
    pull_requests = relationship("PullRequest", back_populates="repository")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    github_pr_id = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=False)
    author_avatar = Column(String, nullable=True)
    base_branch = Column(String, nullable=False)
    head_branch = Column(String, nullable=False)
    diff_url = Column(String, nullable=True)
    files_changed = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    status = Column(SAEnum(PRStatus), default=PRStatus.pending)
    github_url = Column(String, nullable=True)

    # Upgrade #3: Risk Prediction
    risk_level = Column(SAEnum(RiskLevel), nullable=True)
    risk_score = Column(Float, nullable=True)        # 0-100
    risk_factors = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    repository = relationship("Repository", back_populates="pull_requests")
    reviews = relationship("Review", back_populates="pull_request", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="pull_request", cascade="all, delete-orphan")
    llm_reviews = relationship("LLMReview", back_populates="pull_request", cascade="all, delete-orphan")
    scan_results = relationship("ScanResult", back_populates="pull_request", cascade="all, delete-orphan")


class Review(Base):
    """Consensus review — aggregated from all LLMs + static scanners."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Consensus fields
    summary = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)       # weighted consensus 0-10
    consensus_score = Column(Float, nullable=True)     # agreement % across LLMs
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    security_flags = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)

    # Multi-LLM metadata
    models_used = Column(JSON, default=list)           # ["groq/llama-3.3-70b", "gpt-4o", ...]
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pull_request = relationship("PullRequest", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")


class LLMReview(Base):
    """Individual review from one LLM (Groq, OpenAI, Gemini)."""
    __tablename__ = "llm_reviews"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    provider = Column(String, nullable=False)           # "groq" | "openai" | "gemini"
    model = Column(String, nullable=False)              # exact model name
    summary = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    security_flags = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    raw_response = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pull_request = relationship("PullRequest", back_populates="llm_reviews")


class ScanResult(Base):
    """Static analysis results (Bandit, Semgrep)."""
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    scanner = Column(String, nullable=False)            # "bandit" | "semgrep"
    findings = Column(JSON, default=list)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pull_request = relationship("PullRequest", back_populates="scan_results")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pull_request = relationship("PullRequest", back_populates="chat_messages")


class CodebaseIndex(Base):
    __tablename__ = "codebase_indices"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), unique=True)
    total_files = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    status = Column(String, default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeveloperStats(Base):
    """Leaderboard stats per developer per repo."""
    __tablename__ = "developer_stats"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    username = Column(String, nullable=False, index=True)
    avatar_url = Column(String, nullable=True)
    total_prs = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    total_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    security_issues = Column(Integer, default=0)
    score_trend = Column(Float, default=0.0)   # positive = improving
    streak_days = Column(Integer, default=0)   # consecutive clean PRs
    badges = Column(JSON, default=list)        # ["most_improved", "security_aware", ...]
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
