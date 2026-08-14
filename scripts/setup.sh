#!/bin/bash
#
# One-command local development setup script
# Usage: ./scripts/setup.sh

set -e

echo "=== Enterprise Agent Orchestrator Setup ==="
echo

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3 is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed."; exit 1; }

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
MIN_VERSION="3.12"

if [ "$(printf '%s\n' "$MIN_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$MIN_VERSION" ]; then
    echo "Error: Python $MIN_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Prerequisites check passed"
echo

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -e ".[dev]"
echo "✓ Dependencies installed"

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install
echo "✓ Pre-commit hooks installed"

# Create .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

# Start infrastructure services
echo "Starting infrastructure services (PostgreSQL, Redis, Temporal)..."
docker compose -f infra/docker/docker-compose.yml up -d postgres redis temporal

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 10

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose -f infra/docker/docker-compose.yml ps | grep -q "healthy"; then
        break
    fi
    echo "  Waiting for services... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Error: Services did not become healthy in time"
    docker compose -f infra/docker/docker-compose.yml logs
    exit 1
fi

echo "✓ Infrastructure services running"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✓ Database migrations complete"

# Seed demo data
echo "Seeding demo data..."
python scripts/seed_demo_data.py
echo "✓ Demo data seeded"

echo
echo "=========================================="
echo "✓ Setup complete!"
echo
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start orchestrator API: make run"
echo "  3. In another terminal, start worker: python -m apps.worker.main"
echo "  4. Visit API docs: http://localhost:8000/docs"
echo "  5. Visit Temporal UI: http://localhost:8080"
echo
echo "Run tests: make test"
echo "Run demo: python scripts/demo.py"
echo "=========================================="
