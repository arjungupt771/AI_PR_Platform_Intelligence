# AI PR Intelligence Platform

An AI-powered pull request review platform that combines LLM-based code analysis, static security scanning, risk assessment, semantic repository memory, and team analytics to help developers identify issues earlier and improve code quality.

Groq is the primary LLM provider, with optional OpenAI and Google Gemini integrations for multi-model review when configured and supported.

## Features

### AI-Powered Code Reviews
- **Groq-powered reviews:** Use Groq as the default LLM provider for code review.
- **Optional LLM providers:** Configure OpenAI GPT-4o and Google Gemini for additional analysis where supported.
- **Multi-model consensus:** Compare findings across configured models and assign higher confidence to issues independently identified by multiple models.
- **Pull request context:** Analyze code changes and present review findings through the dashboard.
- **PR chat:** Ask follow-up questions about pull requests using the available AI review context.

### Static Security Analysis
- **Bandit:** Scan Python code for common security issues.
- **Semgrep:** Perform rule-based static analysis.
- **Combined analysis:** Use static scanner findings alongside AI-generated review feedback.

### Pull Request Risk Assessment
- Categorize pull requests by risk level: Low, Medium, High, or Critical.
- Use available signals such as changed files, lines of code, and scan results to help prioritize review.
- Surface higher-risk changes for additional attention.

### Semantic Repository Memory
Maintain repository-specific context to improve review relevance.

- **Architecture documentation:** Store architectural information and design decisions.
- **Coding standards:** Define expected coding practices and conventions.
- **Team conventions:** Record requirements such as issue references and security policies.
- **Context-aware reviews:** Make stored repository context available to the review workflow.

### Team Analytics and Leaderboards
- Track developer and team review statistics.
- Display available contribution metrics and trends.
- Support leaderboard badges and streaks where implemented.

### Notifications and Reports
- **Slack:** Send review summaries using the configured Slack integration.
- **Discord:** Send notifications using a Discord webhook.
- **PDF export:** Generate downloadable reports for pull request reviews.

## Architecture

The platform uses a frontend, API backend, background task processing, LLM integrations, static analysis tools, and supporting data services.

```text
GitHub
  |
  v
GitHub Webhook / API
  |
  v
FastAPI Backend
  |
  v
Celery + Redis
  |
  +--> Static Security Analysis
  |      +--> Bandit
  |      +--> Semgrep
  |
  +--> Pull Request Risk Assessment
  |
  +--> Groq LLM Review
  |      +--> Optional OpenAI Integration
  |      +--> Optional Google Gemini Integration
  |
  +--> Review Aggregation / Consensus
  |
  +--> Qdrant Semantic Repository Memory
  |
  +--> Database Persistence
  |
  +--> Slack / Discord Notifications
  |
  +--> PDF Report Generation
  |
  v
Next.js Dashboard
```

The exact review stages depend on the enabled integrations and the implemented backend workflow.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React, TypeScript |
| Styling | Tailwind CSS, shadcn/ui |
| Charts | Recharts |
| Backend | FastAPI, Python 3.11 |
| Primary LLM | Groq API |
| Optional LLMs | OpenAI GPT-4o, Google Gemini |
| Vector Database | Qdrant |
| Static Analysis | Bandit, Semgrep |
| Background Tasks | Celery |
| Message Broker | Redis |
| Relational Database | PostgreSQL |
| Database Migrations | Alembic |
| Authentication | GitHub OAuth |
| Notifications | Slack SDK, Discord Webhooks |
| Containerization | Docker Compose |

## Prerequisites

Install the following before starting the application:

- Git
- Docker and Docker Compose
- A Groq API key
- GitHub OAuth application credentials

Additional API keys and integration credentials are optional unless you enable the corresponding functionality.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/arjungupt771/AI_PR_Platform_Intelligence.git
cd AI_PR_Platform_Intelligence
```

### 2. Configure environment variables

Check that `.env.example` exists in the repository, then create your local environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure the required values:

```dotenv
GROQ_API_KEY=your_groq_api_key
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
SECRET_KEY=your_generated_secret_key
```

Configure optional integrations as needed:

```dotenv
OPENAI_API_KEY=
GOOGLE_API_KEY=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
DISCORD_WEBHOOK_URL=
```

Use the variable names expected by the project's `.env.example` and backend configuration. Do not commit `.env` or expose real credentials.

Generate a random secret key with:

```bash
openssl rand -hex 32
```

### 3. Run the development setup script

```bash
bash scripts/dev-setup.sh
```

Review the script output and resolve any setup instructions it reports before continuing.

### 4. Start the application

Build and start the Docker Compose services:

```bash
docker compose up --build -d
```

Check their status:

```bash
docker compose ps
```

Inspect logs when troubleshooting:

```bash
docker compose logs --tail=100 backend frontend celery_worker celery_beat
```

### 5. Open the application

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API documentation | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

These URLs assume the default ports are available and the corresponding services started successfully.

## LLM Configuration

### Groq — Primary Provider

Groq is the default LLM provider.

```dotenv
GROQ_API_KEY=your_groq_api_key
```

The application must be configured with a valid key and a supported model to generate real AI reviews.

### Optional OpenAI Integration

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

### Optional Google Gemini Integration

```dotenv
GOOGLE_API_KEY=your_google_api_key
```

Optional providers require valid credentials and corresponding implementation support.

When multi-model review is enabled, findings can be compared across configured models. A finding independently identified by multiple models can receive a higher confidence indication. Consensus should not be interpreted as a guarantee that a finding is correct.

## GitHub Integration

GitHub credentials are required for the repository authentication and integration flows supported by the application.

Configure the GitHub OAuth application and corresponding environment variables:

```dotenv
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
```

For webhook-driven workflows, configure the webhook URL and secret according to the application's webhook implementation. A locally running application generally needs an externally reachable webhook endpoint to receive events directly from GitHub.

Never publish your client secret or webhook secret.

## Notifications

### Slack

1. Create a Slack application through the Slack API portal.
2. Configure the required bot permissions, including `chat:write` if required by the implementation.
3. Install the application in your workspace.
4. Configure the required environment variables.

```dotenv
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
```

### Discord

1. Open your Discord server settings.
2. Navigate to Integrations and create a webhook.
3. Configure the webhook URL in the environment file.

```dotenv
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

Notifications require valid credentials, the relevant application configuration, and a working notification flow.

## Semantic Repository Memory

The repository memory feature allows teams to maintain context that can inform code reviews.

Examples of information to store include:

- **Architecture:** FastAPI backend, Next.js frontend, and authentication design.
- **Coding standards:** Type hints, function complexity limits, and naming conventions.
- **Team conventions:** Issue references, testing requirements, and security policies.

The review workflow can use this context to identify potential deviations from repository-specific guidelines. The usefulness of the results depends on the stored context and the review implementation.

Qdrant must be running and accessible to the service that uses semantic memory.

## Running Tests

Run the backend tests from the `backend` directory.

First, ensure the required services are running and Qdrant is reachable at `http://localhost:6333`.

```bash
cd backend
QDRANT_URL=http://localhost:6333 python -m pytest -q
```

The `QDRANT_URL` override is needed when running tests directly from your host environment if the default configuration uses the Docker service hostname `qdrant`.

The test suite was previously verified with **26 passing tests** using this local Qdrant configuration. Results can vary as the code and environment change.

## Troubleshooting

### Qdrant hostname resolution errors

If tests fail with an error such as `Temporary failure in name resolution`, check the URL used by the test process.

- From the host machine, use `http://localhost:6333` when Qdrant publishes port 6333.
- From another service inside the Docker Compose network, use the configured Qdrant service hostname, typically `http://qdrant:6333`.

### Check container status

```bash
docker compose ps
```

### Inspect service logs

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
docker compose logs --tail=100 celery_worker
docker compose logs --tail=100 celery_beat
docker compose logs --tail=100 qdrant
```

### Check application endpoints

```bash
curl -I http://localhost:8000/docs
curl -I http://localhost:3000
curl -I http://localhost:6333/
```

### Environment variables

If an integration fails:

1. Check the variable names against `.env.example` and the backend configuration.
2. Confirm that the relevant API key or credential is valid.
3. Recreate affected containers after changing environment variables.
4. Inspect the relevant service logs for configuration errors.

Do not include secrets when sharing logs or troubleshooting output.

## Project Structure

```text
AI_PR_Platform_Intelligence/
├── backend/
│   ├── alembic/                  # Database migrations
│   ├── app/
│   │   ├── api/routes/           # API endpoints
│   │   ├── core/                 # Configuration, database, authentication
│   │   ├── models/               # Database models
│   │   ├── schemas/              # Request and response schemas
│   │   ├── services/             # AI review and application services
│   │   │   ├── ai_review_service.py
│   │   │   ├── qdrant_service.py
│   │   │   ├── risk_service.py
│   │   │   ├── leaderboard_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── pdf_service.py
│   │   │   └── scanners/
│   │   └── workers/              # Background task processing, if present
│   ├── tests/                    # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js pages and dashboard
│   │   ├── hooks/                # React hooks
│   │   ├── lib/                  # API client and utilities
│   │   └── types/                # TypeScript types
│   ├── package.json
│   └── package-lock.json
├── scripts/
│   └── dev-setup.sh
├── docker-compose.yml
├── .env.example
└── README.md
```

The tree highlights the main application areas. Individual files and directories may differ as the repository evolves.

## Security Notes

- Never commit `.env` files, API keys, OAuth secrets, or webhook secrets.
- Keep development credentials separate from production credentials.
- Review static-analysis findings and AI-generated suggestions before merging code.
- Treat AI-generated findings as recommendations that require engineering judgment.
- Do not rely exclusively on LLM output for security-critical decisions.

## Project Status

The project has been tested locally with Docker Compose, and the backend test suite has previously reported 26 passing tests with the local Qdrant URL configured.

Some integrations require external credentials and additional configuration. Their availability depends on the environment and the implementation enabled in the repository.

## License

Add a license file and specify the license here if you intend to distribute the project under an open-source license.
