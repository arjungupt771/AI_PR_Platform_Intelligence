from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, Repository, PullRequest
from app.schemas.schemas import RepoResponse
from app.services.github_service import GitHubService
from app.workers.tasks import index_repository

router = APIRouter()


@router.get("/available", response_model=List[dict])
async def get_available_repos(
    current_user: User = Depends(get_current_user),
):
    """List all repos the user has on GitHub (not yet connected)."""
    if not current_user.github_access_token:
        raise HTTPException(status_code=400, detail="No GitHub token found")
    gh = GitHubService(current_user.github_access_token)
    return gh.get_user_repos()


@router.get("/", response_model=List[RepoResponse])
async def get_my_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List repos connected to this platform."""
    repos = db.query(Repository).filter(Repository.owner_id == current_user.id).all()
    result = []
    for repo in repos:
        pr_count = db.query(PullRequest).filter(
            PullRequest.repository_id == repo.id
        ).count()
        repo_dict = RepoResponse.model_validate(repo).model_dump()
        repo_dict["pr_count"] = pr_count
        result.append(repo_dict)
    return result


@router.post("/connect", response_model=RepoResponse)
async def connect_repo(
    repo_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect a GitHub repo to the platform and trigger initial indexing."""
    existing = db.query(Repository).filter(
        Repository.github_repo_id == str(repo_data.get("github_repo_id"))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already connected")

    repo = Repository(
        owner_id=current_user.id,
        github_repo_id=str(repo_data["github_repo_id"]),
        full_name=repo_data["full_name"],
        name=repo_data["name"],
        description=repo_data.get("description"),
        language=repo_data.get("language"),
        is_private=repo_data.get("is_private", False),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Trigger background indexing
    index_repository.delay(repo.id, current_user.github_access_token)

    return repo


@router.delete("/{repo_id}")
async def disconnect_repo(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect a repo and clean up its vectors."""
    from app.services.qdrant_service import QdrantService
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    QdrantService().delete_repo_index(repo_id)
    db.delete(repo)
    db.commit()
    return {"status": "disconnected"}


@router.post("/{repo_id}/reindex")
async def reindex_repo(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger re-indexing of a repository."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    task = index_repository.delay(repo_id, current_user.github_access_token)
    return {"status": "indexing_started", "task_id": task.id}


@router.put("/{repo_id}/memory")
async def update_repo_memory(
    repo_id: int,
    memory: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Store architecture docs, coding standards, and team conventions
    in both the DB and Qdrant for RAG retrieval.
    """
    from app.services.qdrant_service import QdrantService
    repo = db.query(Repository).filter(
        Repository.id == repo_id, Repository.owner_id == current_user.id
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    qdrant = QdrantService()

    if memory.get("architecture_docs"):
        repo.architecture_docs = memory["architecture_docs"]
        qdrant.store_memory_document(repo_id, "architecture", memory["architecture_docs"])

    if memory.get("coding_standards"):
        repo.coding_standards = memory["coding_standards"]
        qdrant.store_memory_document(repo_id, "standards", memory["coding_standards"])

    if memory.get("team_conventions"):
        repo.team_conventions = memory["team_conventions"]
        qdrant.store_memory_document(repo_id, "conventions", memory["team_conventions"])

    db.commit()
    return {"status": "updated"}


@router.get("/{repo_id}/memory")
async def get_repo_memory(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id, Repository.owner_id == current_user.id
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {
        "architecture_docs": repo.architecture_docs,
        "coding_standards": repo.coding_standards,
        "team_conventions": repo.team_conventions,
    }
