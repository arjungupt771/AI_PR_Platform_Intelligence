from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, PullRequest, Review, Repository
from app.schemas.schemas import AnalyticsResponse, LeaderboardResponse
from app.services.leaderboard_service import get_leaderboard, compute_developer_stats

router = APIRouter()


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    repo_id: Optional[int] = None,
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    pr_query = db.query(PullRequest).join(Repository).filter(
        Repository.owner_id == current_user.id,
        PullRequest.reviewed_at >= since,
    )
    if repo_id:
        pr_query = pr_query.filter(PullRequest.repository_id == repo_id)

    prs = pr_query.all()
    pr_ids = [p.id for p in prs]

    if not pr_ids:
        return AnalyticsResponse(
            quality_trend=[], developer_insights=[],
            total_prs_reviewed=0, avg_score_all_time=0,
            issues_caught=0, security_flags=0,
        )

    reviews = db.query(Review).filter(Review.pull_request_id.in_(pr_ids)).all()
    review_by_pr = {r.pull_request_id: r for r in reviews}

    # Quality trend by day
    trend_data: dict = {}
    for pr in prs:
        if not pr.reviewed_at:
            continue
        day = pr.reviewed_at.strftime("%Y-%m-%d")
        review = review_by_pr.get(pr.id)
        if day not in trend_data:
            trend_data[day] = {"scores": [], "prs": 0, "critical": 0}
        trend_data[day]["prs"] += 1
        if review:
            if review.overall_score is not None:
                trend_data[day]["scores"].append(review.overall_score)
            trend_data[day]["critical"] += sum(
                1 for i in (review.issues or []) if i.get("severity") == "critical"
            )

    quality_trend = [
        {
            "date": day,
            "avg_score": round(sum(d["scores"]) / len(d["scores"]), 2) if d["scores"] else 0,
            "pr_count": d["prs"],
            "critical_issues": d["critical"],
        }
        for day, d in sorted(trend_data.items())
    ]

    # Developer insights
    dev_data: dict = {}
    for pr in prs:
        a = pr.author
        if a not in dev_data:
            dev_data[a] = {"username": a, "avatar_url": pr.author_avatar, "prs": 0, "scores": [], "issues": 0, "critical": 0}
        dev_data[a]["prs"] += 1
        review = review_by_pr.get(pr.id)
        if review:
            if review.overall_score is not None:
                dev_data[a]["scores"].append(review.overall_score)
            dev_data[a]["issues"] += len(review.issues or [])
            dev_data[a]["critical"] += sum(1 for i in (review.issues or []) if i.get("severity") == "critical")

    developer_insights = [
        {
            "username": d["username"],
            "avatar_url": d["avatar_url"],
            "total_prs": d["prs"],
            "avg_score": round(sum(d["scores"]) / len(d["scores"]), 2) if d["scores"] else 0,
            "total_issues": d["issues"],
            "critical_issues": d["critical"],
        }
        for d in sorted(dev_data.values(), key=lambda x: x["prs"], reverse=True)
    ]

    all_scores = [r.overall_score for r in reviews if r.overall_score is not None]
    all_issues = sum(len(r.issues or []) for r in reviews)
    all_security = sum(len(r.security_flags or []) for r in reviews)

    return AnalyticsResponse(
        quality_trend=quality_trend,
        developer_insights=developer_insights,
        total_prs_reviewed=len(pr_ids),
        avg_score_all_time=round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
        issues_caught=all_issues,
        security_flags=all_security,
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard_route(
    repo_id: Optional[int] = None,
    refresh: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get team leaderboard. Pass refresh=true to recompute stats."""
    if repo_id is None:
        # Use first repo
        repo = db.query(Repository).filter(Repository.owner_id == current_user.id).first()
        if not repo:
            return LeaderboardResponse(entries=[], repo_id=None, computed_at=datetime.utcnow())
        repo_id = repo.id

    if refresh:
        compute_developer_stats(repo_id, db)

    entries = get_leaderboard(repo_id, db)
    return LeaderboardResponse(
        entries=entries,
        repo_id=repo_id,
        computed_at=datetime.utcnow(),
    )
