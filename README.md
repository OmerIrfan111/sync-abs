# سync — Multi-Supplier Dropshipping & Inventory Synchronization Platform

سync is a high-performance inventory synchronization and automated dropshipping platform designed to sit between wholesale distributors and retail ecommerce marketplaces.

## 🚀 Key Features in V1
- **Central Catalog Management**: Normalized catalog schema holding canonical products linked to one or multiple supplier sources.
- **Modular Adapter Architecture**: Decoupled supplier and marketplace connectors supporting high-fidelity mock testing and extensible real API implementations.
- **Real-Time Inventory & Price Synchronization**: Prevents overselling, enforces safety stock buffers, handles out-of-stock events, and tracks all field changes in immutable audit logs.
- **Enterprise Background Task Pipeline**: Asynchronous sync operations powered by Celery, RabbitMQ, and Redis distributed locks.
- **Executive Operations Dashboard**: Live visibility into product counts, active listings, in-stock/out-of-stock metrics, and supplier/marketplace health.

## 🛠️ Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Task Queue**: Celery, Celery Beat, RabbitMQ
- **Database & Cache**: PostgreSQL 16, Redis 7
- **Frontend**: Next.js (App Router), React, Tailwind CSS, Lucide Icons
- **DevOps**: Docker, Docker Compose

## ⚡ Quick Start

```bash
# 1. Clone the repository and navigate into it
git clone <repo_url>
cd "Sync ABS"

# 2. Copy the environment variables
cp .env.example .env

# 3. Start the entire application suite with Docker Compose
docker compose up --build -d

# 4. Run database migrations & seed initial mock suppliers
docker compose exec backend alembic upgrade head
docker compose exec backend python app/seed.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.  
Default Admin Credentials: `admin@syncplatform.io` / `adminpassword123`.

## 📚 Documentation
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API.md)
- [Setup & Deployment](SETUP.md)
- [Testing Guide](TESTING.md)
- [Environment & Free API Keys Guide](ENVIRONMENT.md)
