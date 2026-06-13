import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.schemas import GithubAuthRequest, TokenResponse, UserResponse

router = APIRouter()

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"


@router.post("/github", response_model=TokenResponse)
async def github_auth(payload: GithubAuthRequest, db: Session = Depends(get_db)):
    """
    Exchange a GitHub OAuth code for our JWT token.
    Called by the frontend after GitHub redirects back.
    """
    # 1. Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": payload.code,
            },
        )

    token_data = resp.json()
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description"))

    github_token = token_data["access_token"]

    # 2. Fetch GitHub user profile
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"token {github_token}"},
        )
        gh_user = user_resp.json()

    github_id = str(gh_user["id"])
    username = gh_user["login"]
    avatar_url = gh_user.get("avatar_url")
    email = gh_user.get("email")

    # 3. Upsert user in DB
    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        user = User(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            github_access_token=github_token,
        )
        db.add(user)
    else:
        user.username = username
        user.avatar_url = avatar_url
        user.github_access_token = github_token
        if email:
            user.email = email

    db.commit()
    db.refresh(user)

    # 4. Create our JWT
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
