from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import engine
from app.models.user import Base
from app.api.routes import auth, repos, reviews, analytics, webhooks, export
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI PR Intelligence Platform",
    description="Senior-engineer-quality AI code reviews for every pull request",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(repos.router, prefix="/api/repos", tags=["repositories"])
app.include_router(reviews.router, prefix="/api/prs", tags=["pull-requests"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(export.router, prefix="/api/prs", tags=["export"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI PR Intelligence Platform"}
