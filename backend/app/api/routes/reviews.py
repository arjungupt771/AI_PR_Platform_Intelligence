from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, PullRequest, Review, LLMReview, ScanResult, Repository, PRStatus
from app.schemas.schemas import PRResponse, ReviewResponse, ChatMessageCreate, ChatMessageResponse, PaginatedResponse
from app.services.ai_review_service import AIReviewService
from app.services.github_service import GitHubService
from app.workers.tasks import process_pr_review
import math

router = APIRouter()


def _get_pr_or_404(pr_id: int, current_user: User, db: Session) -> PullRequest:
    pr = db.query(PullRequest).join(Repository).filter(
        PullRequest.id == pr_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.get("/", response_model=PaginatedResponse)
async def list_pull_requests(
    repo_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PullRequest).join(Repository).filter(Repository.owner_id == current_user.id)
    if repo_id:
        query = query.filter(PullRequest.repository_id == repo_id)
    if status:
        query = query.filter(PullRequest.status == status)

    total = query.count()
    prs = query.order_by(PullRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for pr in prs:
        pr_dict = PRResponse.model_validate(pr).model_dump()
        latest = db.query(Review).filter(Review.pull_request_id == pr.id).order_by(Review.created_at.desc()).first()
        if latest:
            pr_dict["latest_review"] = {
                "id": latest.id,
                "overall_score": latest.overall_score,
                "consensus_score": latest.consensus_score,
                "issue_count": len(latest.issues or []),
                "critical_count": sum(1 for i in (latest.issues or []) if i.get("severity") == "critical"),
                "models_used": latest.models_used or [],
                "created_at": latest.created_at,
            }
        items.append(pr_dict)

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=math.ceil(total / page_size))


@router.get("/{pr_id}", response_model=PRResponse)
async def get_pull_request(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_pr_or_404(pr_id, current_user, db)


@router.get("/{pr_id}/review", response_model=ReviewResponse)
async def get_pr_review(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_pr_or_404(pr_id, current_user, db)
    review = db.query(Review).filter(Review.pull_request_id == pr_id).order_by(Review.created_at.desc()).first()
    if not review:
        raise HTTPException(status_code=404, detail="No review found")

    # Attach model_breakdown from LLMReview table
    llm_reviews = db.query(LLMReview).filter(LLMReview.pull_request_id == pr_id).all()
    review_dict = ReviewResponse.model_validate(review).model_dump()
    review_dict["model_breakdown"] = [
        {
            "provider": r.provider,
            "model": r.model,
            "score": r.overall_score,
            "issue_count": len(r.issues or []),
            "critical_count": sum(1 for i in (r.issues or []) if i.get("severity") == "critical"),
            "security_flags": len(r.security_flags or []),
            "latency_ms": r.latency_ms,
        }
        for r in llm_reviews
    ]
    return review_dict


@router.get("/{pr_id}/llm-reviews")
async def get_llm_reviews(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get individual reviews from each LLM for a PR."""
    _get_pr_or_404(pr_id, current_user, db)
    llm_reviews = db.query(LLMReview).filter(LLMReview.pull_request_id == pr_id).all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "model": r.model,
            "summary": r.summary,
            "overall_score": r.overall_score,
            "issues": r.issues or [],
            "suggestions": r.suggestions or [],
            "security_flags": r.security_flags or [],
            "metrics": r.metrics or {},
            "tokens_used": r.tokens_used,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at,
        }
        for r in llm_reviews
    ]


@router.get("/{pr_id}/scans")
async def get_scan_results(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get static analysis scan results (Bandit + Semgrep) for a PR."""
    _get_pr_or_404(pr_id, current_user, db)
    scans = db.query(ScanResult).filter(ScanResult.pull_request_id == pr_id).all()
    return [
        {
            "scanner": s.scanner,
            "findings": s.findings or [],
            "summary": s.summary or {},
            "created_at": s.created_at,
        }
        for s in scans
    ]


@router.post("/{pr_id}/rereview")
async def trigger_rereview(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pr = _get_pr_or_404(pr_id, current_user, db)
    if pr.status == PRStatus.reviewing:
        raise HTTPException(status_code=400, detail="Review already in progress")
    pr.status = PRStatus.pending
    db.commit()
    task = process_pr_review.delay(pr_id, current_user.github_access_token)
    return {"status": "queued", "task_id": task.id}


# ─── Chat ─────────────────────────────────────────────────────────────────────

@router.get("/{pr_id}/chat", response_model=List[ChatMessageResponse])
async def get_chat_history(pr_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.user import ChatMessage
    _get_pr_or_404(pr_id, current_user, db)
    return db.query(ChatMessage).filter(ChatMessage.pull_request_id == pr_id).order_by(ChatMessage.created_at.asc()).all()


@router.post("/{pr_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    pr_id: int,
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.user import ChatMessage
    pr = _get_pr_or_404(pr_id, current_user, db)
    repo = db.query(Repository).filter(Repository.id == pr.repository_id).first()

    user_msg = ChatMessage(pull_request_id=pr_id, role="user", content=message.content)
    db.add(user_msg)
    db.commit()

    history = db.query(ChatMessage).filter(
        ChatMessage.pull_request_id == pr_id,
        ChatMessage.id != user_msg.id,
    ).order_by(ChatMessage.created_at.desc()).limit(20).all()
    conversation = [{"role": m.role, "content": m.content} for m in reversed(history)]

    gh = GitHubService(current_user.github_access_token)
    diff = gh.get_pr_diff(repo.full_name, pr.number)
    latest_review = db.query(Review).filter(Review.pull_request_id == pr_id).order_by(Review.created_at.desc()).first()

    ai_service = AIReviewService()
    ai_text = await ai_service.chat_about_pr(
        pr_diff=diff,
        review_summary=latest_review.summary if latest_review else None,
        conversation_history=conversation,
        user_message=message.content,
        repo_id=repo.id,
    )

    ai_msg = ChatMessage(pull_request_id=pr_id, role="assistant", content=ai_text)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    return ai_msg
