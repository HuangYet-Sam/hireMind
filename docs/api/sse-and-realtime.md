# SSE实时进度设计

> **PRD来源**：§9.5 SSE实时进度设计

---

## 概述

两类场景使用SSE：

---

## 场景1：Agent长任务（通过Hermes API Server）

```
前端 → POST /v1/runs { "messages": [{"role":"user","content":"匹配岗位123的候选人"}] }
     ← 202 { "run_id": "abc-123" }
前端 → GET /v1/runs/abc-123/events (SSE)
     ← event: hermes.tool.progress  data: {"tool":"hr_vector.search_similar","status":"running"}
     ← event: hermes.text.delta     data: {"content":"找到18位匹配候选人..."}
     ← event: [DONE]
```

---

## 场景2：FastAPI AI推理长任务（通过FastAPI SSE中间件）

```
前端 → POST /api/v1/matching/run { "position_id": "..." }
     ← 200 (SSE stream)
     ← event: progress  data: {"phase":"vector_search","message":"检索向量库..."}
     ← event: progress  data: {"phase":"llm_rank","message":"LLM精排(3/20)..."}
     ← event: complete  data: {"matches": [...]}
```

---

## SSE认证

> **PRD来源**：§11.2安全要求、P1-34安全修复

- SSE端点通过Header认证（`Authorization: Bearer <sse_jwt_token>`），不通过URL参数传递Token
- SSE JWT密钥：`hiremind/{tenant_id}/jwt/sse`，存储于HashiCorp Vault
- SSE Token有效期：5分钟，一次性使用
- 降级方案：如Header认证不可用，使用一次性5分钟Token通过URL query参数传递
