"""
Test suite for AI PR Intelligence Platform (Groq-powered)
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User, Repository, PullRequest, Review, PRStatus
from app.core.auth import create_access_token

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    yield
    db = TestSession()
    for table in [Review, PullRequest, Repository, User]:
        db.query(table).delete()
    db.commit()
    db.close()


@pytest.fixture
def test_user():
    db = TestSession()
    user = User(github_id="12345", username="testuser", email="test@example.com",
                avatar_url="https://avatars.githubusercontent.com/u/12345", github_access_token="fake_token")
    db.add(user); db.commit(); db.refresh(user); db.close()
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_repo(test_user):
    db = TestSession()
    repo = Repository(owner_id=test_user.id, github_repo_id="99999",
                      full_name="testuser/testrepo", name="testrepo",
                      language="Python", is_private=False)
    db.add(repo); db.commit(); db.refresh(repo); db.close()
    return repo


@pytest.fixture
def test_pr(test_repo):
    db = TestSession()
    pr = PullRequest(repository_id=test_repo.id, github_pr_id=1001, number=42,
                     title="Add new feature", description="This adds a feature",
                     author="testuser", base_branch="main", head_branch="feature/new",
                     status=PRStatus.completed)
    db.add(pr); db.commit(); db.refresh(pr); db.close()
    return pr


@pytest.fixture
def test_review(test_pr):
    db = TestSession()
    review = Review(
        pull_request_id=test_pr.id,
        summary="Good PR overall.",
        overall_score=7.5,
        consensus_score=75,
        issues=[{"severity": "warning", "file": "main.py", "line": 10, "title": "Unused import", "description": "Remove it", "confirmed_by": 2}],
        suggestions=["Add docstrings"],
        security_flags=[],
        metrics={"complexity": "low"},
        models_used=["llama-3.3-70b-versatile", "gpt-4o"],
        tokens_used=1234,
    )
    db.add(review); db.commit(); db.refresh(review); db.close()
    return review


# ── Health ────────────────────────────────────────────────────────────────────
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ── Auth ──────────────────────────────────────────────────────────────────────
def test_get_me(test_user, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"

def test_get_me_no_auth():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 403

def test_invalid_token():
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer bad_token"})
    assert resp.status_code == 401


# ── Repos ─────────────────────────────────────────────────────────────────────
def test_list_repos_empty(auth_headers):
    resp = client.get("/api/repos/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

def test_list_repos(test_repo, auth_headers):
    resp = client.get("/api/repos/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["full_name"] == "testuser/testrepo"

def test_connect_duplicate_repo(test_repo, auth_headers):
    resp = client.post("/api/repos/connect", json={
        "github_repo_id": "99999", "full_name": "testuser/testrepo", "name": "testrepo"
    }, headers=auth_headers)
    assert resp.status_code == 400

def test_disconnect_repo(test_repo, auth_headers):
    resp = client.delete(f"/api/repos/{test_repo.id}", headers=auth_headers)
    assert resp.status_code == 200

def test_disconnect_nonexistent(auth_headers):
    resp = client.delete("/api/repos/99999", headers=auth_headers)
    assert resp.status_code == 404

def test_get_repo_memory(test_repo, auth_headers):
    resp = client.get(f"/api/repos/{test_repo.id}/memory", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "architecture_docs" in data
    assert "coding_standards" in data
    assert "team_conventions" in data

def test_update_repo_memory(test_repo, auth_headers):
    resp = client.put(f"/api/repos/{test_repo.id}/memory",
        json={"architecture_docs": "FastAPI + Next.js", "coding_standards": "Type hints required"},
        headers=auth_headers)
    assert resp.status_code == 200


# ── Pull Requests ─────────────────────────────────────────────────────────────
def test_list_prs_empty(auth_headers):
    resp = client.get("/api/prs/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

def test_list_prs(test_pr, auth_headers):
    resp = client.get("/api/prs/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "Add new feature"

def test_get_pr(test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["number"] == 42

def test_get_nonexistent_pr(auth_headers):
    resp = client.get("/api/prs/99999", headers=auth_headers)
    assert resp.status_code == 404

def test_filter_by_status(test_pr, auth_headers):
    resp = client.get("/api/prs/?status=completed", headers=auth_headers)
    assert resp.json()["total"] == 1
    resp2 = client.get("/api/prs/?status=pending", headers=auth_headers)
    assert resp2.json()["total"] == 0

def test_get_pr_scan_results(test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}/scans", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_get_pr_llm_reviews(test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}/llm-reviews", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Reviews ───────────────────────────────────────────────────────────────────
def test_get_review(test_review, test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}/review", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 7.5
    assert data["consensus_score"] == 75
    assert len(data["issues"]) == 1
    assert data["issues"][0]["confirmed_by"] == 2
    assert "llama-3.3-70b-versatile" in data["models_used"]

def test_review_not_found(test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}/review", headers=auth_headers)
    assert resp.status_code == 404

def test_chat_history_empty(test_pr, auth_headers):
    resp = client.get(f"/api/prs/{test_pr.id}/chat", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── Analytics ─────────────────────────────────────────────────────────────────
def test_get_analytics_empty(auth_headers):
    resp = client.get("/api/analytics/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_prs_reviewed"] == 0

def test_get_analytics_days(auth_headers):
    resp = client.get("/api/analytics/?days=7", headers=auth_headers)
    assert resp.status_code == 200

def test_get_leaderboard_empty(auth_headers):
    resp = client.get("/api/analytics/leaderboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "computed_at" in data


# ── Webhooks ──────────────────────────────────────────────────────────────────
def test_webhook_bad_signature():
    resp = client.post("/api/webhooks/github", json={"action": "opened"},
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=bad"})
    assert resp.status_code == 401

def test_webhook_non_pr_event():
    import hmac, json
    from app.core.config import settings
    payload = json.dumps({"action": "created"}).encode()
    sig = "sha256=" + hmac.new(settings.github_webhook_secret.encode(), payload, "sha256").hexdigest()
    resp = client.post("/api/webhooks/github", data=payload,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": sig, "Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
