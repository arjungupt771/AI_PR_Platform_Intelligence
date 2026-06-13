from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.user import PRStatus, ReviewSeverity, RiskLevel


class GithubAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    github_id: str
    username: str
    email: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


class RepoResponse(BaseModel):
    id: int
    full_name: str
    name: str
    description: Optional[str]
    language: Optional[str]
    is_private: bool
    is_indexed: bool
    indexed_at: Optional[datetime]
    created_at: datetime
    pr_count: Optional[int] = 0
    class Config:
        from_attributes = True


class ReviewIssue(BaseModel):
    severity: ReviewSeverity
    file: str
    line: Optional[int] = None
    title: str
    description: str
    suggestion: Optional[str] = None
    confirmed_by: Optional[int] = 1   # how many models flagged this
    source_model: Optional[str] = None

class ModelBreakdown(BaseModel):
    provider: str
    model: str
    score: Optional[float]
    issue_count: int
    critical_count: int
    security_flags: int
    latency_ms: int

class ReviewResponse(BaseModel):
    id: int
    pull_request_id: int
    summary: Optional[str]
    overall_score: Optional[float]
    consensus_score: Optional[float]      # agreement %
    model_breakdown: Optional[List[ModelBreakdown]] = []
    issues: List[ReviewIssue]
    suggestions: List[str]
    security_flags: List[str]
    metrics: dict
    models_used: List[str]
    tokens_used: int
    created_at: datetime
    class Config:
        from_attributes = True

class ReviewSummary(BaseModel):
    id: int
    overall_score: Optional[float]
    consensus_score: Optional[float]
    issue_count: int
    critical_count: int
    models_used: Optional[List[str]] = []
    created_at: datetime
    class Config:
        from_attributes = True


class PRResponse(BaseModel):
    id: int
    repository_id: int
    github_pr_id: int
    number: int
    title: str
    description: Optional[str]
    author: str
    author_avatar: Optional[str]
    base_branch: str
    head_branch: str
    files_changed: int
    additions: int
    deletions: int
    status: PRStatus
    github_url: Optional[str]
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    risk_factors: Optional[List[str]] = []
    created_at: datetime
    reviewed_at: Optional[datetime]
    latest_review: Optional[ReviewSummary] = None
    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True


class ScanFinding(BaseModel):
    tool: str
    severity: str
    file: Optional[str]
    line: Optional[int]
    title: str

class ScanResultResponse(BaseModel):
    scanner: str
    findings: List[dict]
    summary: dict
    created_at: datetime
    class Config:
        from_attributes = True


class QualityTrend(BaseModel):
    date: str
    avg_score: float
    pr_count: int
    critical_issues: int

class DeveloperInsight(BaseModel):
    username: str
    avatar_url: Optional[str]
    total_prs: int
    avg_score: float
    total_issues: int
    critical_issues: int

class AnalyticsResponse(BaseModel):
    quality_trend: List[QualityTrend]
    developer_insights: List[DeveloperInsight]
    total_prs_reviewed: int
    avg_score_all_time: float
    issues_caught: int
    security_flags: int


class BadgeInfo(BaseModel):
    id: str
    label: str
    desc: str

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    avatar_url: Optional[str]
    total_prs: int
    avg_score: float
    total_issues: int
    critical_issues: int
    security_issues: int
    score_trend: float
    clean_streak: int
    badges: List[BadgeInfo]

class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    repo_id: Optional[int]
    computed_at: datetime


class RepoMemoryUpdate(BaseModel):
    architecture_docs: Optional[str] = None
    coding_standards: Optional[str] = None
    team_conventions: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
