from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import Repository, PullRequest, PRStatus, User
from app.services.github_service import verify_github_signature
from app.workers.tasks import process_pr_review

router = APIRouter()


@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives GitHub webhook events.
    Filters for pull_request events and dispatches async review tasks.
    """
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        return {"status": "ignored", "event": event_type}

    payload = await request.json()
    action = payload.get("action")

    # Only review when a PR is opened or marked ready for review
    if action not in ("opened", "ready_for_review", "synchronize"):
        return {"status": "ignored", "action": action}

    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    # Find the repo in our DB
    github_repo_id = str(repo_data.get("id"))
    repo = db.query(Repository).filter(
        Repository.github_repo_id == github_repo_id
    ).first()

    if not repo:
        return {"status": "repo_not_connected"}

    # Get the repo owner's access token
    owner = db.query(User).filter(User.id == repo.owner_id).first()
    if not owner or not owner.github_access_token:
        return {"status": "no_access_token"}

    # Upsert PR record
    github_pr_id = pr_data.get("id")
    pr = db.query(PullRequest).filter(
        PullRequest.github_pr_id == github_pr_id
    ).first()

    if not pr:
        pr = PullRequest(
            repository_id=repo.id,
            github_pr_id=github_pr_id,
            number=pr_data.get("number"),
            title=pr_data.get("title", ""),
            description=pr_data.get("body", ""),
            author=pr_data.get("user", {}).get("login", ""),
            author_avatar=pr_data.get("user", {}).get("avatar_url"),
            base_branch=pr_data.get("base", {}).get("ref", "main"),
            head_branch=pr_data.get("head", {}).get("ref", ""),
            github_url=pr_data.get("html_url"),
            status=PRStatus.pending,
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)
    else:
        # Re-review on new commits
        pr.status = PRStatus.pending
        pr.title = pr_data.get("title", pr.title)
        db.commit()

    # Dispatch Celery task
    process_pr_review.delay(pr.id, owner.github_access_token)

    return {"status": "queued", "pr_id": pr.id}
