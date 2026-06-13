import hmac
import hashlib
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from app.core.config import settings


class GitHubService:
    """Handles all GitHub API interactions."""

    def __init__(self, access_token: str):
        self.token = access_token
        self.client = Github(access_token)

    def get_user_repos(self, page: int = 1, per_page: int = 30) -> List[Dict]:
        """Fetch repos the user has access to."""
        user = self.client.get_user()
        repos = []
        for repo in user.get_repos(type="all", sort="updated"):
            repos.append({
                "github_repo_id": str(repo.id),
                "full_name": repo.full_name,
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "is_private": repo.private,
                "stars": repo.stargazers_count,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            })
            if len(repos) >= per_page:
                break
        return repos

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """Get the unified diff for a PR."""
        repo = self.client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        # Fetch raw diff via direct HTTP
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        import requests
        resp = requests.get(pr.diff_url, headers=headers)
        return resp.text if resp.status_code == 200 else ""

    def get_pr_files(self, repo_full_name: str, pr_number: int) -> List[Dict]:
        """Get list of files changed in a PR."""
        repo = self.client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = []
        for f in pr.get_files():
            files.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": f.patch or "",
            })
        return files

    def get_repo_tree(self, repo_full_name: str, ref: str = "HEAD") -> List[Dict]:
        """Get the full file tree of a repo (for indexing)."""
        repo = self.client.get_repo(repo_full_name)
        tree = repo.get_git_tree(ref, recursive=True)
        files = []
        for item in tree.tree:
            if item.type == "blob" and self._is_code_file(item.path):
                files.append({
                    "path": item.path,
                    "sha": item.sha,
                    "size": item.size,
                })
        return files

    def get_file_content(self, repo_full_name: str, path: str, ref: str = "HEAD") -> Optional[str]:
        """Get the content of a single file."""
        try:
            repo = self.client.get_repo(repo_full_name)
            content = repo.get_contents(path, ref=ref)
            if isinstance(content, list):
                return None
            return content.decoded_content.decode("utf-8", errors="ignore")
        except (GithubException, UnicodeDecodeError):
            return None

    def create_pr_comment(self, repo_full_name: str, pr_number: int, body: str):
        """Post a review comment on a PR."""
        repo = self.client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)

    def setup_webhook(self, repo_full_name: str, webhook_url: str) -> Optional[str]:
        """Create a webhook on the repo for PR events."""
        try:
            repo = self.client.get_repo(repo_full_name)
            hook = repo.create_hook(
                name="web",
                config={
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": settings.github_webhook_secret,
                },
                events=["pull_request"],
                active=True,
            )
            return str(hook.id)
        except GithubException as e:
            print(f"Webhook creation failed: {e}")
            return None

    def _is_code_file(self, path: str) -> bool:
        """Filter to only index meaningful code files."""
        code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
            ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
            ".vue", ".svelte", ".sql", ".sh", ".yaml", ".yml", ".json",
            ".toml", ".md",
        }
        skip_dirs = {
            "node_modules", ".git", "__pycache__", ".next", "dist",
            "build", "vendor", ".venv", "venv",
        }
        parts = path.split("/")
        if any(d in skip_dirs for d in parts[:-1]):
            return False
        ext = "." + path.split(".")[-1] if "." in path else ""
        return ext.lower() in code_extensions


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify the X-Hub-Signature-256 from GitHub."""
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        "sha256",
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
