"""
Celery task pipeline:
1. Fetch PR diff + files from GitHub
2. Run security scanners (Bandit + Semgrep)
3. Predict PR risk
4. Run multi-LLM review (Groq + optional GPT-4o + Gemini)
5. Store consensus + individual LLM reviews
6. Update developer leaderboard
7. Send Slack/Discord notifications
8. Store PR summary in semantic memory
"""
import asyncio
from datetime import datetime
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.user import (
    PullRequest, Review, LLMReview, ScanResult,
    Repository, CodebaseIndex, PRStatus, User
)
from app.services.github_service import GitHubService
from app.services.ai_review_service import AIReviewService
from app.services.scanners.security_scanner import SecurityScannerService
from app.services.risk_service import predict_risk
from app.services.leaderboard_service import compute_developer_stats
from app.services.qdrant_service import QdrantService


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60,
                 name="app.workers.tasks.process_pr_review")
def process_pr_review(self, pr_id: int, github_access_token: str):
    """Full pipeline: scan → risk → multi-LLM review → notify."""
    db = SessionLocal()
    pr = None
    try:
        pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
        if not pr:
            return {"error": "PR not found"}

        repo = db.query(Repository).filter(Repository.id == pr.repository_id).first()
        if not repo:
            return {"error": "Repository not found"}

        pr.status = PRStatus.reviewing
        db.commit()

        gh = GitHubService(github_access_token)
        diff = gh.get_pr_diff(repo.full_name, pr.number)
        files = gh.get_pr_files(repo.full_name, pr.number)

        pr.files_changed = len(files)
        pr.additions = sum(f["additions"] for f in files)
        pr.deletions = sum(f["deletions"] for f in files)
        db.commit()

        # ── Stage 1: Static security scan ────────────────────────────────────
        scanner = SecurityScannerService()
        scan_results = scanner.scan(files, language=repo.language)

        # Save scan results
        for tool in ("bandit", "semgrep"):
            tool_data = scan_results.get(tool, {})
            if tool_data.get("findings"):
                scan_record = ScanResult(
                    pull_request_id=pr.id,
                    scanner=tool,
                    findings=tool_data.get("findings", []),
                    summary={
                        k: v for k, v in tool_data.items() if k != "findings"
                    },
                )
                db.add(scan_record)
        db.commit()

        # ── Stage 2: Risk prediction ──────────────────────────────────────────
        risk_level, risk_score, risk_factors = predict_risk(
            files=files,
            author=pr.author,
            repo_id=repo.id,
            additions=pr.additions,
            deletions=pr.deletions,
            scan_results=scan_results,
            db=db,
        )
        pr.risk_level = risk_level
        pr.risk_score = risk_score
        pr.risk_factors = risk_factors
        db.commit()

        # ── Stage 3: Multi-LLM review ─────────────────────────────────────────
        ai_service = AIReviewService()
        consensus = run_async(
            ai_service.review_pull_request(
                diff=diff,
                files=files,
                repo_full_name=repo.full_name,
                pr_title=pr.title,
                pr_description=pr.description,
                repo_id=repo.id,
                scan_results=scan_results,
            )
        )

        # Save individual LLM reviews
        for llm_result in consensus.get("llm_results", []):
            llm_rec = LLMReview(
                pull_request_id=pr.id,
                provider=llm_result["provider"],
                model=llm_result["model"],
                summary=llm_result["data"].get("summary"),
                overall_score=llm_result["data"].get("overall_score"),
                issues=llm_result["data"].get("issues", []),
                suggestions=llm_result["data"].get("suggestions", []),
                security_flags=llm_result["data"].get("security_flags", []),
                metrics=llm_result["data"].get("metrics", {}),
                raw_response=llm_result["data"].get("raw_ai_response"),
                tokens_used=llm_result.get("tokens", 0),
                latency_ms=llm_result.get("latency_ms", 0),
            )
            db.add(llm_rec)

        # Save consensus review
        review = Review(
            pull_request_id=pr.id,
            summary=consensus.get("summary"),
            overall_score=consensus.get("overall_score"),
            consensus_score=consensus.get("consensus_agreement"),
            issues=consensus.get("issues", []),
            suggestions=consensus.get("suggestions", []),
            security_flags=consensus.get("security_flags", []),
            metrics=consensus.get("metrics", {}),
            models_used=consensus.get("models_used", []),
            tokens_used=consensus.get("tokens_used", 0),
        )
        db.add(review)

        pr.status = PRStatus.completed
        pr.reviewed_at = datetime.utcnow()
        db.commit()

        # ── Stage 4: Update leaderboard ───────────────────────────────────────
        try:
            compute_developer_stats(repo.id, db)
        except Exception as e:
            print(f"Leaderboard update failed: {e}")

        # ── Stage 5: Store PR summary in semantic memory ───────────────────────
        try:
            qdrant = QdrantService()
            issues_summary = f"{len(consensus.get('issues', []))} issues, " \
                             f"{len(consensus.get('security_flags', []))} security flags"
            qdrant.store_pr_summary(
                repo_id=repo.id,
                pr_number=pr.number,
                summary=consensus.get("summary", ""),
                issues_summary=issues_summary,
            )
        except Exception as e:
            print(f"Semantic memory store failed: {e}")

        # ── Stage 6: Notifications ────────────────────────────────────────────
        try:
            from app.services.notification_service import send_review_notification
            run_async(send_review_notification(
                pr_number=pr.number,
                pr_title=pr.title,
                pr_author=pr.author,
                pr_url=pr.github_url,
                repo_name=repo.full_name,
                review=consensus,
                risk_level=risk_level.value if risk_level else "unknown",
            ))
        except Exception as e:
            print(f"Notification failed: {e}")

        return {
            "pr_id": pr_id,
            "review_id": review.id,
            "score": review.overall_score,
            "risk": risk_level.value if risk_level else None,
            "models_used": consensus.get("models_used", []),
            "issues": len(review.issues or []),
            "static_issues": scan_results.get("total_static_issues", 0),
        }

    except Exception as exc:
        db.rollback()
        if pr:
            pr.status = PRStatus.failed
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2,
                 name="app.workers.tasks.index_repository")
def index_repository(self, repo_id: int, github_access_token: str):
    db = SessionLocal()
    index_record = None
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return {"error": "Repository not found"}

        index_record = db.query(CodebaseIndex).filter(
            CodebaseIndex.repository_id == repo_id
        ).first()
        if not index_record:
            index_record = CodebaseIndex(repository_id=repo_id)
            db.add(index_record)

        index_record.status = "indexing"
        db.commit()

        gh = GitHubService(github_access_token)
        qdrant = QdrantService()

        tree = gh.get_repo_tree(repo.full_name)
        files_with_content = []
        for item in tree[:200]:
            content = gh.get_file_content(repo.full_name, item["path"])
            if content:
                files_with_content.append({"path": item["path"], "content": content})

        total_chunks = qdrant.index_repository(repo_id, files_with_content)

        # Store repo-level architecture hints in semantic memory
        arch_hint = _detect_architecture(files_with_content)
        if arch_hint:
            qdrant.store_memory_document(
                repo_id=repo_id,
                memory_type="architecture",
                content=arch_hint,
            )

        repo.is_indexed = True
        repo.indexed_at = datetime.utcnow()
        index_record.status = "ready"
        index_record.total_files = len(files_with_content)
        index_record.total_chunks = total_chunks
        db.commit()

        return {"repo_id": repo_id, "files": len(files_with_content), "chunks": total_chunks}

    except Exception as exc:
        db.rollback()
        if index_record:
            index_record.status = "failed"
            index_record.error = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _detect_architecture(files: list) -> str:
    """Auto-detect repo architecture from file structure."""
    paths = [f["path"] for f in files]
    hints = []
    if any("fastapi" in p or "main.py" in p for p in paths):
        hints.append("FastAPI Python backend")
    if any("next.config" in p or "pages/" in p or "app/" in p for p in paths):
        hints.append("Next.js frontend")
    if any("docker-compose" in p for p in paths):
        hints.append("Docker Compose deployment")
    if any("celery" in p.lower() for p in paths):
        hints.append("Celery async task queue")
    if any("migration" in p or "alembic" in p for p in paths):
        hints.append("Alembic database migrations")
    if not hints:
        return ""
    return f"Detected architecture: {', '.join(hints)}. " \
           f"Total files: {len(files)}. " \
           f"Key paths: {', '.join(paths[:10])}"


@celery_app.task(name="app.workers.tasks.sync_open_prs")
def sync_open_prs():
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=1)
        stuck = db.query(PullRequest).filter(
            PullRequest.status == PRStatus.reviewing,
            PullRequest.created_at < cutoff,
        ).all()
        for pr in stuck:
            pr.status = PRStatus.failed
        db.commit()
        return {"reset_count": len(stuck)}
    finally:
        db.close()
