"""
PR Risk Prediction Engine
Predicts Low / Medium / High / Critical risk using:
- Files changed, LOC modified
- Historical bug density per file
- Developer history in this repo
- Presence of risky file patterns (auth, payments, migrations)
- Static scan severity
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import PullRequest, Review, RiskLevel


# Files that historically cause the most bugs
HIGH_RISK_PATTERNS = [
    "auth", "login", "password", "token", "secret", "key",
    "payment", "billing", "stripe", "wallet",
    "migration", "schema", "database",
    "security", "permission", "role", "admin",
    "config", "env", "settings",
    "deploy", "dockerfile", "docker-compose", "k8s", "helm",
    "ci.yml", "github/workflows",
]

MEDIUM_RISK_PATTERNS = [
    "api", "route", "endpoint", "controller",
    "model", "entity", "repository",
    "service", "manager", "handler",
    "test", "spec",
]


def _file_risk_score(filename: str) -> float:
    """Score a single file 0-1 based on its name/path."""
    lower = filename.lower()
    for pattern in HIGH_RISK_PATTERNS:
        if pattern in lower:
            return 1.0
    for pattern in MEDIUM_RISK_PATTERNS:
        if pattern in lower:
            return 0.5
    return 0.2


def _developer_risk_factor(username: str, repo_id: int, db: Session) -> float:
    """
    0.0 = experienced, low risk
    1.0 = new or historically buggy
    """
    prs = db.query(PullRequest).filter(
        PullRequest.repository_id == repo_id,
        PullRequest.author == username,
    ).order_by(PullRequest.created_at.desc()).limit(10).all()

    if not prs:
        return 0.7  # Unknown developer = slightly elevated risk

    pr_ids = [p.id for p in prs]
    reviews = db.query(Review).filter(Review.pull_request_id.in_(pr_ids)).all()
    if not reviews:
        return 0.5

    avg_score = sum(r.overall_score for r in reviews if r.overall_score) / len(reviews)
    critical_count = sum(
        1 for r in reviews
        for issue in (r.issues or [])
        if issue.get("severity") == "critical"
    )

    # Low avg score = higher risk; lots of criticals = higher risk
    score_risk = max(0, (7.0 - avg_score) / 7.0)
    critical_risk = min(1.0, critical_count / 5.0)
    return round((score_risk * 0.6 + critical_risk * 0.4), 2)


def predict_risk(
    files: List[Dict],
    author: str,
    repo_id: int,
    additions: int,
    deletions: int,
    scan_results: Optional[Dict],
    db: Session,
) -> Tuple[RiskLevel, float, List[str]]:
    """
    Returns (risk_level, risk_score 0-100, list of risk factors).
    """
    risk_factors = []
    score = 0.0

    # ── Factor 1: Files changed ──────────────────────────────────────────────
    n_files = len(files)
    if n_files > 20:
        score += 20
        risk_factors.append(f"Large PR: {n_files} files changed")
    elif n_files > 10:
        score += 10
        risk_factors.append(f"Moderate PR size: {n_files} files")

    # ── Factor 2: LOC modified ───────────────────────────────────────────────
    loc = additions + deletions
    if loc > 500:
        score += 20
        risk_factors.append(f"High LOC change: +{additions} -{deletions}")
    elif loc > 200:
        score += 10
        risk_factors.append(f"Moderate LOC change: +{additions} -{deletions}")

    # ── Factor 3: High-risk file patterns ────────────────────────────────────
    risky_files = []
    for f in files:
        fname = f.get("filename", "")
        rs = _file_risk_score(fname)
        if rs >= 1.0:
            risky_files.append(fname)
    if risky_files:
        score += min(30, len(risky_files) * 10)
        risk_factors.append(f"High-risk files: {', '.join(risky_files[:3])}")

    # ── Factor 4: Developer history ──────────────────────────────────────────
    dev_risk = _developer_risk_factor(author, repo_id, db)
    dev_contribution = dev_risk * 20
    score += dev_contribution
    if dev_risk > 0.6:
        risk_factors.append(f"Developer has history of critical issues")
    elif dev_risk < 0.3:
        risk_factors.append(f"Experienced developer — lower risk")

    # ── Factor 5: Static scan findings ───────────────────────────────────────
    if scan_results:
        critical_static = len(scan_results.get("critical_findings", []))
        if critical_static > 0:
            score += min(25, critical_static * 8)
            risk_factors.append(f"Static scan: {critical_static} critical finding(s)")
        bandit_high = scan_results.get("bandit", {}).get("high", 0)
        if bandit_high > 0:
            score += min(10, bandit_high * 3)
            risk_factors.append(f"Bandit: {bandit_high} high severity issue(s)")

    score = min(100.0, score)

    if score >= 70:
        level = RiskLevel.critical
    elif score >= 45:
        level = RiskLevel.high
    elif score >= 20:
        level = RiskLevel.medium
    else:
        level = RiskLevel.low
        risk_factors.append("Small, focused change in safe files")

    return level, round(score, 1), risk_factors
