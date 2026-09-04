# Setup Guide

This guide covers running **سync** locally using Docker Compose or bare-metal development.

## Prerequisites
- Docker & Docker Compose (v20+ / Docker Desktop)
- Python 3.11+ / 3.12+ (if running bare metal)
- Node.js 18+ / 20+ (if running frontend bare metal)

## Quickstart with Docker Compose

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Build and launch all containers:
   ```bash
   docker compose up --build -d
   ```

3. Check service statuses:
   ```bash
   docker compose ps
   ```

4. Run database migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

5. Seed initial data (default admin user and mock suppliers):
   ```bash
   docker compose exec backend python app/seed.py
   ```

6. Access the services:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **RabbitMQ Management Dashboard**: [http://localhost:15672](http://localhost:15672) (User: `guest`, Password: `guest`)

Default admin login:
- **Email**: `admin@syncplatform.io`
- **Password**: `adminpassword123`
