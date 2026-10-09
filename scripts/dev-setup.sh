#!/bin/bash
# scripts/dev-setup.sh
# One-command setup for local development

set -e

echo "🔧 AI PR Intelligence Platform — Dev Setup"
echo ""

# Check dependencies
for cmd in docker docker-compose openssl; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd not found. Please install it first."
        exit 1
    fi
done

# Create .env from example if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    # Auto-generate secrets
    SECRET_KEY=$(openssl rand -hex 32)
    NEXTAUTH_SECRET=$(openssl rand -base64 32)
    sed -i.bak "s/generate_with_openssl_rand_hex_32/${SECRET_KEY}/g" .env
    sed -i.bak "s/generate_with_openssl_rand_base64_32/${NEXTAUTH_SECRET}/g" .env
    rm -f .env.bak
    echo "✅ .env created with auto-generated secrets"
    echo ""
    echo "⚠️  Please fill in these values in .env before continuing:"
    echo "   - GROQ_API_KEY"
    echo "   - GITHUB_CLIENT_ID"
    echo "   - GITHUB_CLIENT_SECRET"
    echo "   - GITHUB_WEBHOOK_SECRET"
    echo ""
    read -p "Press Enter once you've filled in .env..."
fi

echo ""
echo "🐳 Starting Docker services..."
docker-compose up -d db redis qdrant
echo "⏳ Waiting for services to be ready..."
sleep 8

echo "🔨 Running database migrations..."
docker-compose run --rm backend alembic upgrade head

echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo ""
echo "Start everything:   docker-compose up"
echo "Frontend only:      cd frontend && npm run dev"
echo "Backend only:       cd backend && uvicorn app.main:app --reload"
echo "Run tests:          cd backend && pytest tests/ -v"
echo "ngrok tunnel:       bash scripts/ngrok-setup.sh"
echo ""
echo "URLs:"
echo "  App:      http://localhost:3000"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Qdrant:   http://localhost:6333/dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
