# AI PR Intelligence Platform

> Multi-LLM code review platform — Groq + GPT-4o + Gemini consensus, static security scanning, risk prediction, semantic memory, and team leaderboards.

## What It Does

Latest Update

- **Multi-LLM Consensus**: Groq (primary, free), + optional GPT-4o and Gemini. Issues flagged by 2+ models get higher confidence badges
- **Static Security Scan**: Bandit + Semgrep run before the LLM — combined static + AI analysis
- **Risk Prediction**: Low/Medium/High/Critical risk scored per-PR using file patterns, developer history, LOC, and scan results
- **Semantic Memory**: Store architecture docs, coding standards, and team conventions — AI says "this violates your team's conventions"
- **Team Leaderboard**: Per-developer stats, streak tracking, badges (Most Improved, Security Champion, Clean Streak)
- **Slack + Discord**: Auto-post review summaries with multi-model breakdown after each PR
- **PR Chat**: Ask follow-up questions — AI uses Groq with full codebase context
- **PDF Export**: Downloadable review reports per PR

## Architecture

```
GitHub Webhook → FastAPI → Celery Worker
                               ├── Bandit + Semgrep (static scan)
                               ├── Risk Prediction
                               ├── Groq llama-3.3-70b-versatile (primary)
                               ├── GPT-4o (optional)
                               ├── Gemini 1.5 Flash (optional)
                               ├── Consensus Engine
                               ├── Qdrant (semantic memory)
                               ├── Leaderboard update
                               └── Slack / Discord notification
```

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.11 |
| Primary LLM | Groq API — llama-3.3-70b-versatile (fast, free tier) |
| Optional LLMs | OpenAI GPT-4o, Google Gemini 1.5 Flash |
| Vector DB | Qdrant (semantic codebase memory) |
| Security Scanners | Bandit, Semgrep |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + Alembic |
| Auth | GitHub OAuth |
| Notifications | Slack SDK, Discord webhooks |
| Infra | Docker Compose |

## Quick Start

```bash
git clone <your-repo> && cd ai-pr-platform
cp .env.example .env
# Required: GROQ_API_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_WEBHOOK_SECRET, SECRET_KEY
# Optional: OPENAI_API_KEY, GOOGLE_API_KEY, SLACK_BOT_TOKEN, DISCORD_WEBHOOK_URL
bash scripts/dev-setup.sh
docker-compose up
```

URLs:
- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

## Multi-LLM Setup

**Minimum (just Groq — free):**
```
GROQ_API_KEY=gsk_your_key
```

**Full consensus (all 3 models):**
```
GROQ_API_KEY=gsk_your_key
OPENAI_API_KEY=sk-your_key
GOOGLE_API_KEY=AIza_your_key
```

With all 3 active, each PR gets reviewed independently. Issues confirmed by 2+ models are highlighted with a "✓ N models agree" badge.

## Notifications

**Slack:**
1. Create a Slack App at api.slack.com/apps
2. Add `chat:write` scope, install to workspace
3. Set `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` in .env

**Discord:**
1. Server Settings → Integrations → Webhooks → New Webhook
2. Set `DISCORD_WEBHOOK_URL` in .env

## Semantic Memory

In the Repositories page, each repo has a 🧠 memory editor:
- **Architecture Docs**: "FastAPI backend + Next.js frontend. Auth via JWT."
- **Coding Standards**: "All functions must have type hints. Max 50 lines."
- **Team Conventions**: "PRs must reference a Jira ticket. No secrets in code."

This context is injected into every AI review so Claude can say "This violates your team's no-bare-exceptions convention."

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Project Structure

```
ai-pr-platform/
├── backend/
│   └── app/
│       ├── api/routes/          # auth, repos, reviews, analytics, webhooks, export
│       ├── core/                # config, database, JWT auth
│       ├── models/              # SQLAlchemy models (User, PR, Review, LLMReview, ScanResult, ...)
│       ├── schemas/             # Pydantic request/response types
│       ├── services/
│       │   ├── ai_review_service.py     # Multi-LLM orchestration + consensus
│       │   ├── qdrant_service.py        # Semantic memory (code + docs + conventions)
│       │   ├── risk_service.py          # PR risk prediction
│       │   ├── leaderboard_service.py   # Team stats + badges
│       │   ├── notification_service.py  # Slack + Discord
│       │   ├── pdf_service.py           # Report generation
│       │   └── scanners/
│       │       └── security_scanner.py  # Bandit + Semgrep
│       └── workers/
│           ├── celery_app.py    # Celery + Redis config
│           └── tasks.py         # Full 6-stage review pipeline
└── frontend/
    └── src/
        ├── app/dashboard/
        │   ├── page.tsx          # Overview dashboard
        │   ├── pulls/            # PR list + detail with consensus panel
        │   ├── analytics/        # Charts + leaderboard
        │   ├── repos/            # Repo manager + memory editor
        │   └── settings/         # Multi-LLM + notification config
        ├── hooks/                # usePRPoller, useAutoRefreshList
        ├── lib/                  # API client, utils
        └── types/                # Full TypeScript types
```
#
