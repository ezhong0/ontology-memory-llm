# Quick Start Guide

**Get the Memory System running in 5 minutes**

---

## Prerequisites

- **Python 3.11+** (recommended: 3.13)
- **Poetry 1.6+** for dependency management
- **Docker & Docker Compose** for PostgreSQL
- **OpenAI API key** for embeddings and semantic extraction

---

## Installation

### 1. Clone and Install Dependencies

```bash
# Clone repository
git clone [repository-url]
cd adenAssessment2

# Install dependencies with Poetry
poetry install

# Activate virtual environment
poetry shell
```

### 2. Start PostgreSQL Database

```bash
# Start PostgreSQL with pgvector extension
docker-compose up -d postgres

# Verify database is running
docker ps | grep postgres
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your keys
nano .env
```

**Required environment variables**:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb

# OpenAI (for embeddings and semantic extraction)
OPENAI_API_KEY=sk-your-key-here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4o

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text  # or "json" for production
```

### 4. Run Database Migrations

```bash
# Apply all migrations to create schema
poetry run alembic upgrade head

# Verify tables were created
poetry run python -c "
from src.infrastructure.database.session import init_db
from src.config.settings import Settings
init_db(Settings())
print('✓ Database schema created')
"
```

### 5. Start Development Server

```bash
# Start FastAPI server with auto-reload
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile shortcut
make run
```

### 6. Verify Installation

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "up",
    "api": "up"
  }
}
```

### 7. Explore API Documentation

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Your First API Call

### Send a Chat Message

```bash
curl -X POST http://localhost:8000/api/v1/chat/simplified \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Acme Corporation prefers deliveries on Fridays and NET30 payment terms",
    "user_id": "user_001",
    "session_id": "session_001"
  }'
```

**Response**:

```json
{
  "reply": "I've noted that Acme Corporation prefers Friday deliveries and NET30 payment terms.",
  "entities_resolved": [
    {
      "mention": "Acme Corporation",
      "entity_id": "customer_uuid",
      "confidence": 1.0,
      "method": "lazy_creation"
    }
  ],
  "memories_created": [
    {
      "memory_type": "semantic",
      "subject": "customer_uuid",
      "predicate": "delivery_preference",
      "object_value": "Friday",
      "confidence": 0.85
    },
    {
      "memory_type": "semantic",
      "subject": "customer_uuid",
      "predicate": "payment_terms",
      "object_value": "NET30",
      "confidence": 0.85
    }
  ]
}
```

### Ask About What You Learned

```bash
curl -X POST http://localhost:8000/api/v1/chat/simplified \\
  -H "Content-Type": application/json" \\
  -d '{
    "message": "What do I know about Acme?",
    "user_id": "user_001",
    "session_id": "session_001"
  }'
```

**Response**:

```json
{
  "reply": "Acme Corporation prefers Friday deliveries and uses NET30 payment terms.",
  "retrieved_memories": [
    {
      "content": "customer_uuid delivery_preference: Friday",
      "relevance_score": 0.92,
      "confidence": 0.85
    },
    {
      "content": "customer_uuid payment_terms: NET30",
      "relevance_score": 0.91,
      "confidence": 0.85
    }
  ]
}
```

---

## Makefile Commands

The project includes a comprehensive Makefile for common tasks:

```bash
# Setup & Installation
make install              # Install dependencies
make setup                # Complete first-time setup (install + DB + migrations)

# Development
make run                  # Start dev server with auto-reload
make docker-up            # Start PostgreSQL
make docker-down          # Stop Docker services

# Database
make db-migrate           # Apply migrations
make db-rollback          # Rollback last migration
make db-reset             # Reset database (⚠️ destroys all data)
make db-shell             # Open psql shell

# Testing
make test                 # Run all tests
make test-unit            # Run unit tests only (fast, no DB)
make test-integration     # Run integration tests (requires DB)
make test-cov             # Generate coverage report

# Code Quality
make lint                 # Check code style
make lint-fix             # Auto-fix style issues
make format               # Format code with ruff
make typecheck            # Run mypy type checking
make check-all            # Run all quality checks

# Demo Mode
make run-demo             # Start server with demo mode enabled
make demo-data            # Load demo scenario data
```

---

## Demo Mode (Optional)

The system includes an isolated demo mode for testing:

```bash
# Enable demo mode
export DEMO_MODE_ENABLED=true

# Start server
make run

# Access demo UI
open http://localhost:8000/demo
```

**Demo Features**:
- Pre-loaded business scenarios (e.g., "Acme Corp ERP System")
- Isolated database (won't affect production data)
- Interactive chat interface
- Memory visualization

See [Demo Guide](../development/DEMO.md) for details.

---

## Troubleshooting

### Database Connection Issues

**Problem**: `asyncpg.exceptions.InvalidCatalogNameError: database "memorydb" does not exist`

**Solution**:
```bash
# Create database manually
docker exec -it adenAssessment2_postgres_1 psql -U memoryuser -c "CREATE DATABASE memorydb;"

# Run migrations
poetry run alembic upgrade head
```

---

### Missing OpenAI API Key

**Problem**: `openai.error.AuthenticationError: No API key provided`

**Solution**:
```bash
# Ensure .env file has your key
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Restart server to reload environment
```

---

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Ensure you're in the virtual environment
poetry shell

# Verify Python path includes project root
python -c "import sys; print('\\n'.join(sys.path))"
```

---

### Port Already in Use

**Problem**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill

# Or use a different port
poetry run uvicorn src.api.main:app --port 8001
```

---

## Next Steps

Now that you have the system running:

1. **Read the Architecture Overview** → [docs_new/architecture/OVERVIEW.md](../architecture/OVERVIEW.md)
2. **Understand the API** → [docs_new/api/ENDPOINTS.md](../api/ENDPOINTS.md)
3. **Learn the Database Schema** → [docs_new/database/SCHEMA.md](../database/SCHEMA.md)
4. **Write Your First Test** → [docs_new/testing/GUIDE.md](../testing/GUIDE.md)
5. **Make Your First Contribution** → [docs_new/development/WORKFLOW.md](../development/WORKFLOW.md)

---

## Getting Help

- **Documentation**: See `docs_new/` folder
- **Issues**: Check existing issues or create a new one
- **Philosophy**: Read [VISION.md](../../docs/vision/VISION.md) and [CLAUDE.md](../../CLAUDE.md)

---

**Welcome to the Memory System! 🎉**
