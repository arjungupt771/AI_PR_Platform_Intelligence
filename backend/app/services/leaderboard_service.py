"""
Team Leaderboard Service
Computes per-developer stats and awards badges:
- Most Improved Developer
- Security Awareness Champion
- Highest Code Quality
- Clean Streak (consecutive PRs with no critical issues)
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta
from app.models.user import PullRequest, Review, DeveloperStats, Repository


BADGES = {
    "most_improved": {"label": "📈 Most Improved", "desc": "Biggest score improvement this month"},
    "security_champion": {"label": "🛡️ Security Champion", "desc": "Zero security flags in last 5 PRs"},
    "quality_master": {"label": "🏆 Quality Master", "desc": "Avg score above 8.5"},
    "clean_streak": {"label": "🔥 Clean Streak", "desc": "5+ consecutive PRs with no critical issues"},
    "prolific": {"label": "⚡ Prolific", "desc": "Most PRs this month"},
    "rapid_reviewer": {"label": "🚀 Fast Mover", "desc": "Smallest average PR size"},
}


def compute_developer_stats(repo_id: int, db: Session) -> List[Dict]:
    """Recompute all developer stats for a repo and update DeveloperStats table."""
    # Get all completed PRs in this repo
    prs = db.query(PullRequest).filter(
        PullRequest.repository_id == repo_id,
    ).all()
    if not prs:
        return []

    pr_ids = [p.id for p in prs]
    pr_by_id = {p.id: p for p in prs}

    # Get all reviews
    reviews = db.query(Review).filter(Review.pull_request_id.in_(pr_ids)).all()
    review_by_pr = {r.pull_request_id: r for r in reviews}

    # Group by author
    authors: Dict[str, Dict] = {}
    for pr in prs:
        a = pr.author
        if a not in authors:
            authors[a] = {
                "username": a,
                "avatar_url": pr.author_avatar,
                "prs": [],
                "scores": [],
                "issues": 0,
                "critical": 0,
                "security": 0,
            }
        authors[a]["prs"].append(pr)
        review = review_by_pr.get(pr.id)
        if review:
            if review.overall_score is not None:
                authors[a]["scores"].append((pr.created_at, review.overall_score))
            for issue in (review.issues or []):
                authors[a]["issues"] += 1
                if issue.get("severity") == "critical":
                    authors[a]["critical"] += 1
            authors[a]["security"] += len(review.security_flags or [])

    results = []
    for username, data in authors.items():
        scores = [s for _, s in data["scores"]]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        # Score trend: compare last 3 vs previous 3
        sorted_scores = sorted(data["scores"], key=lambda x: x[0])
        trend = 0.0
        if len(sorted_scores) >= 4:
            recent = [s for _, s in sorted_scores[-3:]]
            older = [s for _, s in sorted_scores[-6:-3]]
            if recent and older:
                trend = round(sum(recent) / len(recent) - sum(older) / len(older), 2)

        # Clean streak
        streak = _compute_clean_streak(data["prs"], review_by_pr)

        # Compute badges
        badges = _compute_badges(
            username=username,
            avg_score=avg_score,
            security_count=data["security"],
            streak=streak,
            trend=trend,
            total_prs=len(data["prs"]),
            all_authors=authors,
        )

        # Upsert DeveloperStats
        stat = db.query(DeveloperStats).filter(
            DeveloperStats.repository_id == repo_id,
            DeveloperStats.username == username,
        ).first()
        if not stat:
            stat = DeveloperStats(repository_id=repo_id, username=username)
            db.add(stat)

        stat.avatar_url = data["avatar_url"]
        stat.total_prs = len(data["prs"])
        stat.avg_score = avg_score
        stat.total_issues = data["issues"]
        stat.critical_issues = data["critical"]
        stat.security_issues = data["security"]
        stat.score_trend = trend
        stat.streak_days = streak
        stat.badges = badges
        stat.updated_at = datetime.utcnow()

        results.append({
            "username": username,
            "avatar_url": data["avatar_url"],
            "total_prs": len(data["prs"]),
            "avg_score": avg_score,
            "total_issues": data["issues"],
            "critical_issues": data["critical"],
            "security_issues": data["security"],
            "score_trend": trend,
            "clean_streak": streak,
            "badges": badges,
        })

    db.commit()

    # Sort by avg_score desc
    return sorted(results, key=lambda x: x["avg_score"], reverse=True)


def _compute_clean_streak(prs: List, review_by_pr: Dict) -> int:
    """Count consecutive PRs (most recent first) with no critical issues."""
    sorted_prs = sorted(prs, key=lambda p: p.created_at, reverse=True)
    streak = 0
    for pr in sorted_prs:
        review = review_by_pr.get(pr.id)
        if not review:
            break
        has_critical = any(
            i.get("severity") == "critical" for i in (review.issues or [])
        )
        if has_critical:
            break
        streak += 1
    return streak


def _compute_badges(
    username: str,
    avg_score: float,
    security_count: int,
    streak: int,
    trend: float,
    total_prs: int,
    all_authors: Dict,
) -> List[str]:
    badges = []

    if avg_score >= 8.5:
        badges.append("quality_master")
    if security_count == 0 and total_prs >= 5:
        badges.append("security_champion")
    if streak >= 5:
        badges.append("clean_streak")
    if trend >= 1.0:
        badges.append("most_improved")

    # Prolific = most PRs among all authors
    max_prs = max((len(d["prs"]) for d in all_authors.values()), default=0)
    if total_prs == max_prs and total_prs >= 3:
        badges.append("prolific")

    return badges


def get_leaderboard(repo_id: int, db: Session) -> List[Dict]:
    """Return cached leaderboard from DB."""
    stats = db.query(DeveloperStats).filter(
        DeveloperStats.repository_id == repo_id
    ).order_by(DeveloperStats.avg_score.desc()).all()

    return [
        {
            "rank": i + 1,
            "username": s.username,
            "avatar_url": s.avatar_url,
            "total_prs": s.total_prs,
            "avg_score": s.avg_score,
            "total_issues": s.total_issues,
            "critical_issues": s.critical_issues,
            "security_issues": s.security_issues,
            "score_trend": s.score_trend,
            "clean_streak": s.streak_days,
            "badges": [
                {**BADGES[b], "id": b}
                for b in (s.badges or [])
                if b in BADGES
            ],
        }
        for i, s in enumerate(stats)
    ]
