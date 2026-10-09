"""Shared test configuration with isolated, credential-free defaults."""

import os

# Set these before importing app modules, because Settings is instantiated at import time.
os.environ["SECRET_KEY"] = "test-only-secret-key-not-for-production"
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["GROQ_API_KEY"] = "test-only-groq-key"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-only-webhook-secret"
