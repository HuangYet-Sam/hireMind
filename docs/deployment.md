# HireMind Production Deployment Guide

This guide covers deploying the full HireMind stack to a production server.

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Docker Engine | 24.0+ | With Compose v2 plugin |
| Docker Compose | 2.20+ | `docker compose` (not `docker-compose`) |
| RAM | 8 GB+ | 16 GB recommended for production |
| Disk | 50 GB+ SSD | For PostgreSQL, MinIO, and Docker images |
| CPU | 4 cores+ | 8 cores recommended |
| Domain | - | Pointed to your server's public IP |
| OS | Ubuntu 22.04+ / Debian 12+ | Or any modern Linux with Docker support |

### Software Installation (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect.

---

## Architecture Overview

```
                    ┌─ Internet ─────────────────────────┐
                    │                                     │
              ┌─────▼──────┐                              │
              │  Nginx/Caddy│ :80/:443                    │
              │  (Reverse   │                              │
              │   Proxy)    │                              │
              └──┬────┬────┘                              │
                 │    │                                    │
         /api/*  │    │  /* (static)                       │
                 │    │                                    │
    ┌────────────▼┐  ┌▼──────────────┐                    │
    │ hr-api       │  │ hr-frontend   │                   │
    │ (FastAPI)    │  │ (Nginx+Vue3)  │                   │
    │ :8000        │  │ :80           │                   │
    └──┬────┬──┬───┘  └──────────────┘                    │
       │    │  │                                          │
  ┌────▼─┐ ┌▼──┐ ┌▼─────┐                               │
  │Postgres│Redis│MinIO  │                                │
  │:5432   │:6379│:9000   │                               │
  │(pgvector)│    │(S3)   │                               │
  └────────┘────┘────────┘                                │
                    └─────────────────────────────────────┘
```

**Services:**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg17` | 5432 (internal) | Primary database with vector support |
| `redis` | `redis:7-alpine` | 6379 (internal) | Caching, sessions, task queues |
| `minio` | `minio/minio:latest` | 9000/9001 (internal) | S3-compatible resume file storage |
| `hr-api` | Built from `packages/api/Dockerfile` | 8000 (internal) | FastAPI backend |
| `hr-frontend` | Built from frontend Dockerfile | 80 (exposed) | Vue 3 SPA with Nginx |

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/HuangYet-Sam/hireMind.git
cd hireMind
```

### 2. Create Environment File

Copy the example file and fill in your production values:

```bash
cp .env.example .env.production
```

Edit `.env.production` — see the [Environment Variables](#environment-variables) section below for details.

### 3. Configure SSL with Let's Encrypt

Install Certbot and obtain certificates:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com
```

Certificate files will be placed at:
- Certificate: `/etc/letsencrypt/live/your-domain.com/fullchain.pem`
- Private key: `/etc/letsencrypt/live/your-domain.com/privkey.pem`

### 4. Start All Services

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 5. Verify Deployment

```bash
# Check all containers are healthy
docker compose -f docker-compose.prod.yml ps

# Test health endpoint
curl http://localhost/health
# Expected: {"status":"ok"}

# Test API docs
curl http://localhost/api/docs
# Expected: Swagger UI HTML
```

---

## Environment Variables

All configuration is driven by environment variables. Create a `.env.production` file in the project root.

### Required Variables (Must Change)

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL password | `your-secure-db-password` |
| `JWT_SECRET_KEY` | JWT signing key (min 32 chars) | `openssl rand -hex 32` |
| `MINIO_ROOT_USER` | MinIO admin username | `hiremind-minio` |
| `MINIO_ROOT_PASSWORD` | MinIO admin password (min 8 chars) | `your-secure-minio-password` |
| `MINIO_ACCESS_KEY` | MinIO API access key | `your-access-key` |
| `MINIO_SECRET_KEY` | MinIO API secret key | `your-secret-key` |
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["https://your-domain.com"]` |

### Application Settings

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `HireMind` | Application display name |
| `APP_VERSION` | `0.1.0` | Application version |
| `DEBUG` | `false` | Enable debug mode (must be `false` in production) |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Database

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `postgres` | PostgreSQL hostname (container name) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `hiremind` | PostgreSQL user |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password |
| `POSTGRES_DB` | `hiremind` | Database name |
| `DATABASE_URL` | *(auto)* | Full async connection string |
| `DB_POOL_SIZE` | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |

### MinIO (S3 Storage)

| Variable | Default | Description |
|---|---|---|
| `MINIO_ENDPOINT` | `minio:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | *(required)* | Access key |
| `MINIO_SECRET_KEY` | *(required)* | Secret key |
| `MINIO_BUCKET_RESUMES` | `resumes` | Bucket name for resume files |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO (set `true` if TLS) |

### JWT Authentication

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | *(required)* | HMAC signing key |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | *(required)* | JSON array of allowed origins |

### LLM / OpenAI

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key for AI features |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | API base URL |
| `OPENAI_MODEL_RESUME` | `gpt-4o-mini` | Model for resume parsing |
| `OPENAI_MODEL_MATCHING` | `gpt-4o-mini` | Model for candidate matching |

### Hermes Agent Integration

| Variable | Default | Description |
|---|---|---|
| `HERMES_AGENT_URL` | `http://localhost:8648` | Hermes Agent URL |
| `HERMES_AGENT_API_KEY` | *(empty)* | Hermes API key |
| `HERMES_AGENT_MODEL` | `default` | Default model for Hermes |

### File Upload

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `uploads` | Upload directory path |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum file upload size |

### Pagination

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PAGE_SIZE` | `20` | Default items per page for list endpoints |
| `MAX_PAGE_SIZE` | `100` | Maximum allowed items per page |

---

## HTTPS/SSL Configuration

### Option A: Nginx + Let's Encrypt

Create `/etc/nginx/sites-available/hiremind`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    client_max_body_size 25M;

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # Frontend static files
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check passthrough
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 256;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/hiremind /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Option B: Caddy (Automatic HTTPS)

```Caddyfile
your-domain.com {
    encode gzip

    @api path /api/* /health /openapi.json
    handle @api {
        reverse_proxy hr-api:8000
    }

    handle {
        reverse_proxy hr-frontend:80
    }
}
```

### Auto-Renewal (Let's Encrypt)

```bash
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## Database Initialization and Migration

The `hr-api` container automatically runs `alembic upgrade head` on startup before launching the server. This applies all pending migrations.

### Manual Migration

To run migrations manually:

```bash
docker compose -f docker-compose.prod.yml exec hr-api alembic upgrade head
```

### Check Current Migration State

```bash
docker compose -f docker-compose.prod.yml exec hr-api alembic current
```

### Create a New Migration

After modifying SQLAlchemy models:

```bash
docker compose -f docker-compose.prod.yml exec hr-api alembic revision --autogenerate -m "description"
```

---

## Backup and Recovery

### Database Backup

```bash
# Full backup
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U hiremind hiremind > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U hiremind -F c hiremind > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Database Restore

```bash
# From SQL dump
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U hiremind hiremind

# From custom format
docker compose -f docker-compose.prod.yml exec postgres \
  pg_restore -U hiremind -d hiremind < backup.dump
```

### MinIO (File Storage) Backup

```bash
# Install mc (MinIO Client) if not present
docker compose -f docker-compose.prod.yml exec minio mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Mirror bucket to local directory
docker compose -f docker-compose.prod.yml exec minio mc mirror local/resumes /data/backup/resumes
```

### Full Stack Backup Script

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/hiremind/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Database
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U hiremind -F c hiremind > "$BACKUP_DIR/hiremind.dump"

# MinIO resumes bucket
docker compose -f docker-compose.prod.yml exec minio \
  mc mirror local/resumes "$BACKUP_DIR/resumes/"

# Environment config
cp .env.production "$BACKUP_DIR/.env.production.bak"

echo "Backup completed: $BACKUP_DIR"
```

### Automated Daily Backups

```bash
sudo crontab -e
# Add: 0 2 * * * /opt/hiremind/scripts/backup.sh >> /var/log/hiremind-backup.log 2>&1
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs <service-name>

# Check specific container
docker inspect <container-name> | jq '.[0].State'
```

### Database Connection Failed

```bash
# Verify postgres is healthy
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U hiremind

# Check connectivity from hr-api
docker compose -f docker-compose.prod.yml exec hr-api python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://hiremind:password@postgres:5432/hiremind'))"
```

### Port Already in Use

```bash
sudo lsof -i :<port>
sudo kill -9 <PID>
```

### Reset Everything (Data Loss!)

```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
```
