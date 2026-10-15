#!/bin/bash
# ============================================================
# Price Comparison Engine — one-shot project setup script
# Run this ONCE inside an empty folder to create everything.
# Usage:  bash setup.sh
# ============================================================

set -e   # stop on first error

echo "🚀 Setting up Price Comparison + Prediction Engine..."

# ── Folders ──────────────────────────────────────────────────
mkdir -p scrapers/quick_commerce
mkdir -p db
mkdir -p prediction
mkdir -p services
mkdir -p api/routes
mkdir -p tasks
mkdir -p tests
mkdir -p frontend/src/{pages,components,hooks,utils}

echo "✅ Folders created"

# ── Python virtual environment ────────────────────────────────
python3 -m venv venv
echo "✅ Virtual environment created"

# ── .env from example ─────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env created — EDIT IT before running the app"
else
  echo "⚠️  .env already exists — skipping"
fi

# ── Install Python deps ────────────────────────────────────────
source venv/bin/activate
pip install -r requirements.txt --quiet
playwright install chromium
echo "✅ Python dependencies installed"

# ── Install Node deps ──────────────────────────────────────────
cd frontend
npm install --silent
cd ..
echo "✅ Node dependencies installed"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env — set DATABASE_URL and REDIS_URL"
echo "  2. Start backend:   uvicorn api.main:app --reload"
echo "  3. Start frontend:  cd frontend && npm run dev"
echo "  4. Open: http://localhost:5173"
echo ""
echo "For background jobs (optional):"
echo "  celery -A tasks.celery_app worker --loglevel=info"
echo "  celery -A tasks.celery_app beat   --loglevel=info"
