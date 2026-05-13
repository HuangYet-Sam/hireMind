# 部署架构

> 源自 PRD V3.6 §11.8 部署架构 + §11.4 可扩展性 + §11.1a 并发控制（L6131-L6190）
> PRD原文：`prd/HireMind-PRD-V3.6.md`

---

## §11.8 部署架构

```
┌─ 生产环境部署架构 ──────────────────────────────────────────────┐
│                                                                   │
│  ┌─ Caddy (反向代理+自动HTTPS) ─────────────────────────────────┐ │
│  │  :443 → /api/*     → FastAPI :8000                           │ │
│  │        /hr/*       → Vue SPA  :8648                          │ │
│  │        /socket.io  → Koa BFF  :8648                          │ │
│  │        /agent/*    → Hermes API Server :8642                 │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ 应用层 ────────────────────────────────────────────────────┐ │
│  │  FastAPI × 2 (Gunicorn + Uvicorn workers)                    │ │
│  │  Koa BFF × 1  (hermes-web-ui)                               │ │
│  │  Hermes Agent × 1 (Gateway模式)                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ 数据层 ────────────────────────────────────────────────────┐ │
│  │  PostgreSQL 17 (主从, 含pgvector向量索引) │ MinIO (简历文件存储)      │ │
│  │  Redis 7 (缓存+队列)                       │ SQLite (Session+Kanban)    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ 监控层 ────────────────────────────────────────────────────┐ │
│  │  Prometheus + Grafana (指标) │ Loki (日志)                    │ │
│  │  Sentry (错误追踪)           │ AlertManager (告警→微信)       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  部署：单机（8C16G+100G SSD）                                  │
│  V1.0部署：应用2节点+数据库主从（pgvector向量索引随PG主从自动同步）  │
└───────────────────────────────────────────────────────────────────┘
```

---

## §11.4 可扩展性

| 维度 | 策略 |
|------|------|
| 水平扩展 | FastAPI无状态，可多实例 + Caddy负载均衡 |
| 数据库 | PostgreSQL读写分离，按tenant_id分库（V2.0阶段） |
| 向量库 | Phase 1：pgvector 0.8+（HNSW索引+SQ8量化，召回率>99%）；Phase 2：pgvectorscale StreamingDiskANN，百万级扩展路径 |
| Agent | Hermes Profile机制，每租户独立Agent实例 |
| 新渠道 | Webhook机制 + Skill编排，新增渠道零代码修改 |
| 新AI能力 | Service层新增方法 + FastAPI暴露端点 + Tool注册 |

---

## §11.1a 并发控制规范（V3.5核查修复）

### 11.1a.1 乐观锁策略

所有核心实体表增加version字段：
- DDL: `version INTEGER NOT NULL DEFAULT 1`
- 更新时: `UPDATE ... SET version=version+1 WHERE id=:id AND version=:expected_version`
- 影响行数=0 → 抛ConcurrentModificationError(50003)

适用范围：positions, candidates, offers, interviews

### 11.1a.2 幂等性保证

- 文件上传：客户端生成 `idempotency_key`（UUID），服务端基于 `file_hash + idempotency_key` 去重，24小时内相同key返回已上传文件ID
- 审批操作：状态机天然幂等（已批准→再批准=idempotent，重复审批请求返回当前状态）
- 反馈提交：`feedback_token` 一次性使用，提交后标记为used，重复提交返回409
- 异步任务：`task_events` 表基于 `task_id + task_type` 去重

### 11.1a.3 解析+匹配并行竞态保护（V3.6架构修复C-05）

简历解析进行中时（status=parsing），禁止触发该简历的匹配刷新。匹配刷新的 on_complete 回调中检查简历解析状态，若 status≠completed 则跳过本次刷新（记录日志），等待解析完成后的触发链再次刷新。

### 11.1a.4 行级锁场景

| 场景 | 锁策略 | 超时 |
|------|--------|------|
| 简历解析中 | SELECT FOR UPDATE SKIP LOCKED | 无需等待 |
| Offer审批 | 乐观锁(version) | — |
| 岗位编辑 | 乐观锁(version) | — |
| 候选人状态流转 | 乐观锁(version) | — |

### 11.1a.5 DDL变更

candidates, positions, offers, interviews表均新增:
`version INTEGER NOT NULL DEFAULT 1`
