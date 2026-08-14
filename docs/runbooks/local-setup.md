# Local Development Setup

This guide walks you through setting up the Enterprise Agent Orchestrator on your local machine.

## Prerequisites

Ensure you have the following installed:

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Make** (usually pre-installed on macOS/Linux)

## Quick Start

The fastest way to get started is using the automated setup script:

```bash
git clone https://github.com/your-org/enterprise-agent-orchestrator.git
cd enterprise-agent-orchestrator
make dev-setup
```

This single command will:
1. Install Python dependencies
2. Set up pre-commit hooks
3. Create `.env` file from template
4. Start all required services via Docker Compose
5. Run database migrations
6. Seed demo data

**Total setup time:** ~5 minutes

## Manual Setup (Step-by-Step)

If you prefer to understand each step:

### 1. Clone Repository

```bash
git clone https://github.com/your-org/enterprise-agent-orchestrator.git
cd enterprise-agent-orchestrator
```

### 2. Create Python Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
make install
# Or manually:
pip install -e ".[dev]"
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and customize variables if needed. Default values work for local development.

### 5. Start Infrastructure Services

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres redis temporal
```

Wait for services to be healthy (~30 seconds):

```bash
docker compose -f infra/docker/docker-compose.yml ps
```

All services should show "healthy" status.

### 6. Run Database Migrations

```bash
alembic upgrade head
```

This creates all database tables and indexes.

### 7. Seed Demo Data

```bash
python scripts/seed_demo_data.py
```

This creates:
- 3 demo users (admin, developer, viewer)
- 3 example agents (HR, Finance, Compliance)
- Sample governance policies

### 8. Start Orchestrator API

In one terminal:

```bash
make run
# Or manually:
uvicorn apps.orchestrator.main:app --reload --host 0.0.0.0 --port 8000
```

### 9. Start Temporal Worker

In another terminal:

```bash
python -m apps.worker.main
```

### 10. Verify Installation

Open your browser to:

- **API Documentation:** http://localhost:8000/docs
- **Temporal UI:** http://localhost:8080
- **Health Check:** http://localhost:8000/health

Expected response from health check:
```json
{"status": "healthy"}
```

## Running Tests

```bash
make test
```

This runs the full test suite with coverage reporting. Expected output:

```
======== test session starts ========
collected 87 items

tests/test_orchestrator/test_agents.py ........
tests/test_governance/test_policy_engine.py .....
...

---------- coverage: 92% ----------
```

## Code Quality Checks

Run all quality checks before committing:

```bash
make lint      # Check code style
make format    # Auto-format code
make typecheck # Run mypy type checking
```

Or run all checks at once:

```bash
make lint && make typecheck && make test
```

## Common Tasks

### Reset Database

```bash
docker compose -f infra/docker/docker-compose.yml down -v
docker compose -f infra/docker/docker-compose.yml up -d postgres redis temporal
alembic upgrade head
python scripts/seed_demo_data.py
```

### View Logs

```bash
# All services
docker compose -f infra/docker/docker-compose.yml logs -f

# Specific service
docker compose -f infra/docker/docker-compose.yml logs -f postgres
```

### Stop All Services

```bash
docker compose -f infra/docker/docker-compose.yml down
```

### Access Database

```bash
docker exec -it enterprise-agents-postgres psql -U user -d enterprise_agents
```

### Access Redis CLI

```bash
docker exec -it enterprise-agents-redis redis-cli
```

## Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use, modify `.env`:

```
API_PORT=8001
DATABASE_URL=postgresql+psycopg://user:password@localhost:5433/enterprise_agents
```

And update the Docker Compose port mappings accordingly.

### Docker Services Not Starting

Check Docker Desktop is running and has sufficient resources:
- Minimum 4 GB RAM allocated
- Minimum 2 CPU cores

### Database Connection Errors

Ensure Postgres is fully started:

```bash
docker compose -f infra/docker/docker-compose.yml ps postgres
```

If not healthy, check logs:

```bash
docker compose -f infra/docker/docker-compose.yml logs postgres
```

### Import Errors

Ensure you are in the virtual environment:

```bash
which python  # Should point to venv/bin/python
```

If not, activate it:

```bash
source venv/bin/activate
```

## Next Steps

- Read the [Architecture Decision Records](../adr/) to understand design choices
- Review the [API Documentation](http://localhost:8000/docs)
- Run the [End-to-End Demo](../../scripts/demo.py)
- Explore the [Deployment Guide](./deployment.md) for production setup

## Getting Help

- **Issues:** Report bugs on GitHub Issues
- **Documentation:** See [docs/](../) for detailed guides
- **Community:** Join our Slack workspace
