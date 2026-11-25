FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt ./
# constraints.txt pins every library to the versions tested locally; open
# ranges in requirements.txt let a fresh build pull a newer SQLAlchemy that
# defaults to a different Postgres driver and fails at startup.
RUN pip install --upgrade pip && pip install -r requirements.txt -c constraints.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
