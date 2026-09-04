# Testing Guide

سync features automated test suites for unit testing, integration testing, and end-to-end multi-service synchronization testing.

## Running Tests

### Running with Docker Compose
```bash
# Run all tests in the backend container
docker compose exec backend pytest

# Run unit tests only
docker compose exec backend pytest tests/unit

# Run integration tests only
docker compose exec backend pytest tests/integration

# Run with test coverage
docker compose exec backend pytest --cov=app tests/
```

### Running Locally (Bare Metal)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pytest
```

## Test Structure
- `tests/unit/`:
  - Test authentication tokens and password hashing.
  - Test encryption and decryption of adapter credentials.
  - Test Pydantic model schemas and validation logic.
  - Test MockSupplierAdapter catalog generation, stock variance, and pricing.
- `tests/integration/`:
  - Test database models and Alembic migrations.
  - Test FastAPI endpoints (Suppliers CRUD, Catalog CRUD, filtering, pagination).
  - Test end-to-end sync workflow from Mock Supplier into PostgreSQL and sync logs.
