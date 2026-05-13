# 🚀 DevOps / 部署专家审计报告

> 审计角色：DevOps/部署专家  
> 审计对象：HireMind 项目部署架构与基础设施  
> 审计日期：2026-05-12  
> 参考来源：PRD V3.6 §11/§12/§13，docs/devops/，docs/architecture/

---

## 一、总体评估

| 维度 | PRD定义 | 当前状态 | 差距 |
|------|---------|---------|------|
| **容器化** | Docker Compose（6服务） | ❌ 无任何Docker配置 | 🔴 Critical |
| **CI/CD** | GitHub Actions（lint+test+deploy） | ❌ 无.github/workflows | 🔴 Critical |
| **监控** | Prometheus+Grafana+Loki+Sentry | ❌ 无监控配置 | 🔴 Critical |
| **备份** | PG备份+MinIO备份 | ❌ 无备份策略 | 🟡 High |
| **开发环境** | 一键启动（docker-compose up） | ❌ 仅有next dev | 🔴 Critical |
| **部署文档** | §11.8详细架构图 | ✅ docs/devops/deployment.md | 🟢 OK |

---

## 二、目标部署架构（PRD §11.8）

```
┌─ Caddy (反向代理+自动HTTPS) ──────────────────────────────┐
│  :443 → /api/*     → FastAPI :8000                        │
│        /hr/*       → Vue SPA  :8648                       │
│        /socket.io  → Koa BFF  :8648                       │
│        /agent/*    → Hermes API Server :8642              │
└───────────────────────────────────────────────────────────┘

┌─ 应用层 ──────────────────────────────────────────────────┐
│  FastAPI × 2 (Gunicorn + Uvicorn workers)                 │
│  Koa BFF × 1  (hermes-web-ui)                            │
│  Hermes Agent × 1 (Gateway模式)                           │
└───────────────────────────────────────────────────────────┘

┌─ 数据层 ──────────────────────────────────────────────────┐
│  PostgreSQL 17 (主从, pgvector) │ MinIO (简历文件)         │
│  Redis 7 (缓存+队列)           │ SQLite (Session+Kanban)  │
└───────────────────────────────────────────────────────────┘

┌─ 监控层 ──────────────────────────────────────────────────┐
│  Prometheus + Grafana │ Loki │ Sentry │ AlertManager      │
└───────────────────────────────────────────────────────────┘

部署：单机（8C16G+100G SSD）→ V1.0应用2节点+数据库主从
```

---

## 三、Docker Compose 配置草案

### 3.1 开发环境 docker-compose.dev.yml

```yaml
# /home/agent/HireMind/docker-compose.dev.yml
version: "3.8"

services:
  # ========== 数据层 ==========
  postgres:
    image: pgvector/pgvector:pg17
    container_name: hiremind-postgres
    environment:
      POSTGRES_DB: hiremind
      POSTGRES_USER: hiremind
      POSTGRES_PASSWORD: ${DB_PASSWORD:-hiremind_dev}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hiremind"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hiremind-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: hiremind-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-hiremind}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:-hiremind_dev}
    ports:
      - "9000:9000"
      - "9001:9001"  # Console
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ========== 应用层（开发模式） ==========
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: hiremind-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://hiremind:${DB_PASSWORD:-hiremind_dev}@postgres:5432/hiremind
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_USER:-hiremind}
      MINIO_SECRET_KEY: ${MINIO_PASSWORD:-hiremind_dev}
      JWT_SECRET: ${JWT_SECRET:-dev_secret_change_in_prod}
      LITELLM_CONFIG: /app/litellm_config.yaml
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app  # 热重载
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: hiremind-frontend
    ports:
      - "8648:8648"
    volumes:
      - ./frontend/packages:/app/packages  # 热重载
    depends_on:
      - backend
    command: pnpm --filter server dev  # Koa BFF

  # ========== 监控层 ==========
  prometheus:
    image: prom/prometheus:latest
    container_name: hiremind-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: hiremind-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - prometheus

  loki:
    image: grafana/loki:latest
    container_name: hiremind-loki
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki

volumes:
  postgres_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
  loki_data:
```

### 3.2 生产环境补充

```yaml
# docker-compose.prod.yml (overlay)
services:
  caddy:
    image: caddy:2-alpine
    container_name: hiremind-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile  # 多阶段构建
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: "2.0"

  postgres:
    # 生产：主从复制
    command: >
      postgres
      -c shared_preload_libraries='pgvector'
      -c wal_level=replica
      -c max_wal_senders=3

volumes:
  caddy_data:
  caddy_config:
```

---

## 四、CI/CD 流水线设计

### 4.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: HireMind CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_DB: hiremind_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          cd backend
          pip install -r requirements.txt -r requirements-dev.txt
      - name: Lint (ruff)
        run: cd backend && ruff check .
      - name: Type check (mypy)
        run: cd backend && mypy app/
      - name: Test (pytest)
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/hiremind_test

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - name: Install deps
        run: pnpm install
      - name: Lint
        run: pnpm run lint
      - name: Type check
        run: pnpm run type-check
      - name: Unit test
        run: pnpm run test

  deploy:
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        run: |
          ssh ${{ secrets.SERVER_HOST }} "
            cd /opt/hiremind &&
            git pull &&
            docker compose -f docker-compose.dev.yml -f docker-compose.prod.yml up -d --build
          "
```

---

## 五、监控方案

### 5.1 指标采集

| 服务 | 指标 | 采集方式 |
|------|------|---------|
| FastAPI | 请求数/延迟/错误率/QPS | `prometheus-fastapi-instrumentator` |
| PostgreSQL | 连接数/查询延迟/死锁 | `postgres_exporter` |
| Redis | 内存/命中率/连接数 | `redis_exporter` |
| MinIO | 存储用量/请求延迟 | MinIO内置Prometheus端点 |
| Hermes Agent | Tool调用次数/LLM延迟/Token消耗 | OTel SDK + custom metrics |

### 5.2 关键告警规则

```yaml
# monitoring/alerts.yml
groups:
  - name: hiremind
    rules:
      # FastAPI 5xx > 5%
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "FastAPI 5xx错误率超过5%"

      # PostgreSQL连接数 > 80%
      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning

      # LLM调用延迟 > 30s
      - alert: LLMLatencyHigh
        expr: histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m])) > 30
        for: 3m
        labels:
          severity: warning

      # 简历MinIO存储 > 80%
      - alert: StorageNearFull
        expr: minio_cluster_capacity_usable_free_bytes / minio_cluster_capacity_usable_total_bytes < 0.2
        for: 10m
        labels:
          severity: warning
```

### 5.3 Grafana Dashboard模板

```
招聘运营Dashboard:
  ├── 岗位统计（活跃/暂停/关闭）
  ├── 候选人漏斗（投递→筛选→面试→Offer）
  ├── AI调用成本（Token消耗趋势）
  ├── API性能（P50/P95/P99延迟）
  └── 错误追踪（Top 10错误端点）
```

---

## 六、备份与恢复

### 6.1 PostgreSQL备份策略

```bash
# 每日全量备份 + pgvector
#!/bin/bash
BACKUP_DIR="/backup/postgres/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 全量备份（含pgvector扩展数据）
pg_dump -h localhost -U hiremind -Fc hiremind > "$BACKUP_DIR/hiremind.dump"

# 保留30天
find /backup/postgres -mtime +30 -type f -delete

# 恢复测试（每周自动执行）
# pg_restore -h localhost -U hiremind -d hiremind_test "$BACKUP_DIR/hiremind.dump"
```

### 6.2 MinIO备份策略

```bash
# mc mirror 同步到备份存储
mc alias set backup http://backup-minio:9000 $ACCESS_KEY $SECRET_KEY
mc mirror --watch --remove hiremind/resumes backup/hiremind-resumes
```

### 6.3 RTO/RPO目标

| 指标 | 目标 | 方案 |
|------|------|------|
| **RPO**（数据丢失） | < 1小时 | PostgreSQL WAL归档 + 每小时增量备份 |
| **RTO**（恢复时间） | < 30分钟 | Docker Compose一键拉起 + PG备份恢复 |
| **简历文件** | 0丢失 | MinIO多副本 + mc mirror实时同步 |

---

## 七、开发环境体验

### 7.1 一键启动

```bash
# 克隆项目
git clone https://github.com/HuangYet-Sam/HireMind.git
cd HireMind

# 复制环境变量
cp .env.example .env

# 启动全部服务
docker compose -f docker-compose.dev.yml up -d

# 等待健康检查通过
docker compose -f docker-compose.dev.yml ps  # 确认全部healthy

# 初始化数据库
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed  # 种子数据

# 访问：
# 前端：http://localhost:8648/hr/dashboard
# 后端API：http://localhost:8000/docs
# MinIO Console：http://localhost:9001
# Grafana：http://localhost:3000
```

### 7.2 热重载支持

| 服务 | 热重载方式 |
|------|----------|
| FastAPI (backend) | `uvicorn --reload` + volume mount |
| Vue 3 (frontend) | Vite HMR + volume mount |
| Hermes Agent | 修改tools/skills后 `/reload-skills` |
| PostgreSQL | Alembic auto-generate + upgrade |

### 7.3 数据库迁移

```bash
# 生成迁移脚本
docker compose exec backend alembic revision --autogenerate -m "add interviews table"

# 执行迁移
docker compose exec backend alembic upgrade head

# 回滚
docker compose exec backend alembic downgrade -1
```

---

## 八、当前docs/devops文档审计

### 8.1 现有文档

| 文档 | 内容 | 质量 | 建议 |
|------|------|------|------|
| `docs/devops/deployment.md` | §11.8部署架构图+§11.4可扩展性+§11.1a并发控制 | ✅ 优秀 | 保留，补充Docker配置 |
| `docs/devops/monitoring-and-logging.md` | 监控方案 | ✅ 良好 | 保留，补充告警规则 |

### 8.2 需新增的DevOps文档

| 文档 | 优先级 | 说明 |
|------|--------|------|
| `docker-compose.dev.yml` | P0 | 开发环境一键启动 |
| `docker-compose.prod.yml` | P1 | 生产环境overlay配置 |
| `.github/workflows/ci.yml` | P0 | CI/CD流水线 |
| `backend/Dockerfile` | P0 | FastAPI多阶段构建 |
| `frontend/Dockerfile` | P0 | hermes-web-ui构建 |
| `monitoring/` | P1 | Prometheus/Grafana/Loki配置 |
| `Caddyfile` | P1 | 生产反向代理配置 |
| `backup/` | P2 | 备份脚本 |

---

## 九、OPC（一人公司）部署策略

### 9.1 单机部署方案（V1.0）

```
硬件：8C16G + 100G SSD（~¥300/月云服务器）
┌──────────────────────────────────────────┐
│  单机 Docker Compose                      │
│  ├── Caddy (:80/:443)     反向代理        │
│  ├── FastAPI × 2 (:8000)  业务API         │
│  ├── Koa BFF (:8648)      前端+BFF        │
│  ├── Hermes Agent (:8642) AI引擎          │
│  ├── PostgreSQL 17        主库(含pgvector) │
│  ├── Redis 7              缓存            │
│  ├── MinIO                文件存储         │
│  ├── Prometheus + Grafana 监控            │
│  └── Loki                 日志            │
│                                          │
│  资源预估：                               │
│  - PostgreSQL: 2GB RAM, 20GB磁盘         │
│  - Redis: 512MB RAM                      │
│  - MinIO: 1GB RAM, 50GB磁盘(简历)        │
│  - FastAPI×2: 2GB RAM                    │
│  - Hermes: 1GB RAM                       │
│  - 监控栈: 1GB RAM                       │
│  - 系统+缓存: ~3GB RAM                   │
│  合计: ~11GB RAM / 70GB磁盘              │
│  ✅ 16GB RAM 可承受                       │
└──────────────────────────────────────────┘
```

### 9.2 成本估算

| 阶段 | 基础设施 | 月成本 | 说明 |
|------|---------|--------|------|
| 开发期 | 本地Docker | ¥0 | 开发者电脑运行 |
| 测试期 | 4C8G云服务器 | ~¥150 | 测试环境 |
| V1.0上线 | 8C16G云服务器 | ~¥300 | 含pgvector的PG实例 |
| V2.0扩展 | 应用2节点+PG主从 | ~¥800 | 高可用 |

---

## 十、结论

### 关键风险

| # | 风险 | 缓解措施 |
|---|------|---------|
| 1 | Docker配置从零开始 | M0基建模块（15天）优先完成 |
| 2 | pgvector Docker镜像兼容性 | 使用官方 `pgvector/pgvector:pg17` |
| 3 | Hermes Agent容器化 | Gateway模式支持Docker部署 |
| 4 | 监控栈资源占用 | 开发期可关闭，仅生产环境启用 |

### 优先级建议

```
M0基建期（D1-D15）：
  D1-D3:  docker-compose.dev.yml + PostgreSQL/Redis/MinIO
  D5-D6:  FastAPI Dockerfile + 热重载
  D8-D10: Hermes Agent Docker配置
  D11-D12: GitHub Actions CI Pipeline
  D13-D15: Prometheus + Grafana基础Dashboard
```

### 总体评分：部署架构设计 7/10

PRD的部署架构设计完整（Caddy反向代理、FastAPI多worker、监控栈齐全），但缺乏具体的Docker配置和CI/CD实现。M0基建模块（15天）足以补齐所有DevOps基础设施。
