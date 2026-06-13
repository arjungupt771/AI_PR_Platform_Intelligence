from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, PullRequest, Review, Repository
from app.services.pdf_service import generate_review_html, generate_pdf_bytes

router = APIRouter()


@router.get("/{pr_id}/export/pdf")
async def export_review_pdf(
    pr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export the AI review for a PR as a downloadable PDF."""
    pr = db.query(PullRequest).join(Repository).filter(
        PullRequest.id == pr_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not pr:
        raise HTTPException(status_code=404, detail="PR not found")

    repo = db.query(Repository).filter(Repository.id == pr.repository_id).first()

    review = db.query(Review).filter(
        Review.pull_request_id == pr_id
    ).order_by(Review.created_at.desc()).first()
    if not review:
        raise HTTPException(status_code=404, detail="No review found for this PR")

    review_data = {
        "summary": review.summary,
        "overall_score": review.overall_score,
        "issues": review.issues or [],
        "suggestions": review.suggestions or [],
        "security_flags": review.security_flags or [],
        "metrics": review.metrics or {},
        "model_used": review.model_used,
    }
    pr_data = {
        "title": pr.title,
        "number": pr.number,
        "author": pr.author,
        "repo_name": repo.full_name if repo else "",
    }

    html = generate_review_html(review_data, pr_data)
    pdf_bytes = generate_pdf_bytes(html)

    filename = f"review-pr-{pr.number}-{repo.name if repo else 'unknown'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
