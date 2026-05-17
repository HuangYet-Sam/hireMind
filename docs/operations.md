# HireMind Operations Manual

Day-to-day operations guide for managing a running HireMind production deployment.

---

## Container Management

### View Running Services

```bash
docker compose -f docker-compose.prod.yml ps
```

Expected output — 5 services all with `healthy` status:

| Service | Container Name | Port |
|---|---|---|
| postgres | hiremind-postgres | 5432 (internal) |
| redis | hiremind-redis | 6379 (internal) |
| minio | hiremind-minio | 9000/9001 (internal) |
| hr-api | hiremind-api | 8000 (internal) |
| hr-frontend | hiremind-frontend | 80 (exposed) |

### Start / Stop / Restart

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Stop all services (preserves data)
docker compose -f docker-compose.prod.yml stop

# Stop and remove containers (preserves volumes)
docker compose -f docker-compose.prod.yml down

# Restart a single service
docker compose -f docker-compose.prod.yml restart hr-api

# Rebuild and restart after code changes
docker compose -f docker-compose.prod.yml up -d --build hr-api
```

### Rebuild After Updates

```bash
cd /home/yetsam/hireMind
git pull origin main

# Rebuild only the changed service
docker compose -f docker-compose.prod.yml up -d --build hr-api

# Or rebuild everything
docker compose -f docker-compose.prod.yml up -d --build
```

### Scale FastAPI Workers

```bash
# Run 2 API instances behind the reverse proxy
docker compose -f docker-compose.prod.yml up -d --scale hr-api=2
```

---

## Log Management

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs --tail=100

# Specific service
docker compose -f docker-compose.prod.yml logs --tail=200 hr-api

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f hr-api

# Logs with timestamps
docker compose -f docker-compose.prod.yml logs -t hr-api --since 1h

# Filter by time range
docker compose -f docker-compose.prod.yml logs hr-api --since "2026-05-17T10:00:00" --until "2026-05-17T12:00:00"
```

### Log Locations

| Source | Path / Command | Retention |
|---|---|---|
| Docker container stdout | `docker compose logs <service>` | Configured by `max-size` / `max-file` |
| API access logs | JSON format to stdout | 30 days via Docker log rotation |
| Error logs | JSON format to stderr | 90 days via Docker log rotation |
| Audit logs | PostgreSQL `audit_log` table | Permanent |
| AI decision logs | PostgreSQL `ai_decisions` table | Permanent |

### Log Format

All API logs follow JSON format:

```json
{
  "timestamp": "2026-05-17T10:30:00Z",
  "method": "GET",
  "path": "/api/v1/candidates",
  "status": 200,
  "duration_ms": 45,
  "user_id": "user-123",
  "tenant_id": "company-a"
}
```

---

## Database Operations

### Connect to PostgreSQL

```bash
# Interactive session
docker compose -f docker-compose.prod.yml exec postgres psql -U hiremind

# Run a single query
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hiremind -c "SELECT count(*) FROM candidates;"
```

### Backup Script

Create `/opt/hiremind/scripts/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/hiremind/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# PostgreSQL backup (custom format, compressed)
docker compose -f /opt/hiremind/docker-compose.prod.yml exec -T postgres \
  pg_dump -U hiremind -F c hiremind > "$BACKUP_DIR/db_${TIMESTAMP}.dump"

echo "[$(date)] Database backup: db_${TIMESTAMP}.dump"

# MinIO resume files backup
docker compose -f /opt/hiremind/docker-compose.prod.yml exec minio \
  mc mirror --overwrite local/resumes "$BACKUP_DIR/resumes_${TIMESTAMP}/" 2>/dev/null || true

echo "[$(date)] MinIO backup: resumes_${TIMESTAMP}/"

# Cleanup old backups
find "$BACKUP_DIR" -name "db_*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "resumes_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true

echo "[$(date)] Cleanup completed (retention: ${RETENTION_DAYS} days)"
echo "[$(date)] Backup finished successfully"
```

Make it executable:

```bash
chmod +x /opt/hiremind/scripts/backup.sh
```

### Restore Database

```bash
# Stop the API to prevent writes during restore
docker compose -f docker-compose.prod.yml stop hr-api

# Restore from backup
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U hiremind -d hiremind -c < /opt/hiremind/backups/db_TIMESTAMP.dump

# Restart API
docker compose -f docker-compose.prod.yml start hr-api
```

### Check Database Size

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hiremind -c "SELECT pg_size_pretty(pg_database_size('hiremind')) AS db_size;"
```

### Check Table Sizes

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U hiremind -c \
  "SELECT relname AS table, pg_size_pretty(pg_total_relation_size(relid)) AS size
   FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
```

---

## Redis Operations

### Connect to Redis

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli
```

### Useful Commands

```bash
# Check Redis info
docker compose -f docker-compose.prod.yml exec redis redis-cli info

# Check memory usage
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory | grep used_memory_human

# List keys
docker compose -f docker-compose.prod.yml exec redis redis-cli keys "*"

# Flush all data (use with caution)
docker compose -f docker-compose.prod.yml exec redis redis-cli flushall
```

---

## MinIO Operations

### Access MinIO Console

The MinIO console is available at `http://your-server:9001`. Log in with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`.

### CLI Operations

```bash
# List buckets
docker compose -f docker-compose.prod.yml exec minio mc ls local/

# List files in resumes bucket
docker compose -f docker-compose.prod.yml exec minio mc ls local/resumes/

# Check bucket size
docker compose -f docker-compose.prod.yml exec minio mc du local/resumes/
```

---

## Health Checks

### Automated Health Check

```bash
# Quick health check
curl -s http://localhost/health | python3 -m json.tool

# Check all services via Docker
docker compose -f docker-compose.prod.yml ps --format json | python3 -m json.tool
```

### Health Check Endpoints

| Endpoint | Expected Response | Description |
|---|---|---|
| `GET /health` | `{"status": "ok"}` | FastAPI health |
| `GET /api/docs` | HTML (200) | Swagger UI |
| `pg_isready -U hiremind` | exit 0 | PostgreSQL readiness |
| `redis-cli ping` | `PONG` | Redis readiness |

### Service Health Check Configuration

All services in `docker-compose.prod.yml` have built-in health checks:

- **postgres**: `pg_isready` every 5s
- **redis**: `redis-cli ping` every 5s
- **minio**: `mc ready local` every 5s
- **hr-api**: depends on postgres and redis being healthy

---

## Monitoring Configuration

### Prometheus Setup

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'hiremind-api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['hr-api:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'minio'
    metrics_path: /minio/v2/metrics/cluster
    static_configs:
      - targets: ['minio:9000']
```

### Key Metrics to Monitor

| Metric | Alert Threshold | Description |
|---|---|---|
| API Response Time (P95) | > 5s | Slow API responses |
| API 5xx Error Rate | > 1% | Server errors |
| PostgreSQL Connections | > 80% of pool | Connection exhaustion |
| PostgreSQL Disk Usage | > 80% | Running out of disk space |
| Redis Memory | > 80% of max | Cache memory pressure |
| MinIO Disk Usage | > 80% | Storage running low |
| Resume Parse Queue Depth | > 500 | Processing backlog |

### Alert Channels

Configure alerts to send notifications via:
- Email (SMTP)
- WeChat / Feishu webhook
- Slack / Discord webhook
- SMS (for P0 critical alerts)

### Error Severity Levels

| Level | Response Time | Example |
|---|---|---|
| **P0 Critical** | < 5 min | Database down, auth service failure |
| **P1 Error** | < 30 min | Single API 5xx, LLM timeout |
| **P2 Warning** | Next business day | Slow response, queue backlog |
| **P3 Info** | No action | Normal CRUD operations |

---

## Updates and Upgrades

### Update Application Code

```bash
cd /opt/hiremind
git fetch origin
git pull origin main

# Rebuild affected services
docker compose -f docker-compose.prod.yml up -d --build

# Verify
docker compose -f docker-compose.prod.yml ps
curl http://localhost/health
```

### Update Database Schema

If a new migration was added:

```bash
# Check current migration state
docker compose -f docker-compose.prod.yml exec hr-api alembic current

# Apply migrations
docker compose -f docker-compose.prod.yml exec hr-api alembic upgrade head

# Verify
docker compose -f docker-compose.prod.yml exec hr-api alembic current
```

### Rollback a Migration

```bash
# Rollback one step
docker compose -f docker-compose.prod.yml exec hr-api alembic downgrade -1

# Rollback to specific revision
docker compose -f docker-compose.prod.yml exec hr-api alembic downgrade <revision_id>
```

---

## Security Checklist

- [ ] `JWT_SECRET_KEY` is not the default value
- [ ] `POSTGRES_PASSWORD` is a strong, unique password
- [ ] `MINIO_ROOT_PASSWORD` is set (not `minioadmin`)
- [ ] `CORS_ORIGINS` only includes production domains (no `localhost`)
- [ ] `DEBUG=false` in production
- [ ] SSL/TLS is configured (HTTPS only)
- [ ] Database port (5432) is not exposed to the internet
- [ ] Redis port (6379) is not exposed to the internet
- [ ] MinIO ports (9000/9001) are not exposed to the internet
- [ ] Only ports 80 and 443 are publicly accessible
- [ ] Firewall configured: `ufw allow 80/tcp && ufw allow 443/tcp`
- [ ] `.env.production` is not committed to Git
- [ ] Docker log rotation is configured
- [ ] Automated backups are running

---

## Emergency Procedures

### Service Down

```bash
# Check which service is down
docker compose -f docker-compose.prod.yml ps

# Restart the failing service
docker compose -f docker-compose.prod.yml restart <service>

# Check logs for the root cause
docker compose -f docker-compose.prod.yml logs --tail=500 <service>
```

### Full Stack Restart

```bash
docker compose -f docker-compose.prod.yml restart
```

### Disk Full

```bash
# Check disk usage
df -h

# Docker cleanup (removes unused images/containers)
docker system prune -a

# Check Docker log sizes
docker compose -f docker-compose.prod.yml logs --tail=0 2>&1 | wc -c
```

### Database Corruption

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Restore from latest backup
cat /opt/hiremind/backups/db_LATEST.sql | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U hiremind hiremind

# Start services
docker compose -f docker-compose.prod.yml up -d
```
