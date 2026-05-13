# Koa BFF端点清单

> **PRD来源**：§9.2 Koa BFF端点清单 + §9.2a BFF统一响应格式

---

## 1. BFF端点清单（hermes-web-ui管理功能）

> 以下端点由 hermes-web-ui 的 Koa BFF (:8648) 提供，代理到 Hermes API Server (:8642)。HireMind不修改这些端点。

| 类别 | 代理路径 | 目标 |
|------|---------|------|
| 对话 | `/dashboard-api/v1/*` | → Hermes `/v1/*` |
| Cron | `/dashboard-api/v1/cron/*` | → Hermes Cron API |
| 模型 | `/dashboard-api/v1/models/*` | → Hermes Models API |
| 配置 | `/dashboard-api/v1/config/*` | → Hermes Config API |
| 频道 | `/dashboard-api/v1/channels/*` | → Hermes Channels API |
| 文件 | `/dashboard-api/v1/files/*` | → Hermes Files API |
| 终端 | WebSocket `/api/pty` | → Hermes PTY WebSocket |

---

## 2. BFF统一响应格式（V3.6架构修复C-04）

所有通过Koa BFF层和FastAPI层返回的数据必须统一为以下格式，前端只需处理一套格式：

```typescript
// BFF统一响应格式
interface BFFResponse<T> {
  success: boolean;
  data: T | null;
  error?: { code: number; message: string; detail?: string };
  meta?: { total?: number; page?: number; page_size?: number };
  request_id: string;
}
```

### 2.1 转换规则

| 来源 | 转换目标 |
|------|---------|
| FastAPI 200 | `{success: true, data: response.data, meta: response.meta, request_id: "..."}` |
| FastAPI 4xx/5xx | `{success: false, error: {code, message, detail}, request_id: "..."}` |
| FastAPI超时 | `{success: false, error: {code: 40000, message: "AI服务暂时不可用"}, request_id: "..."}` |

### 2.2 设计原则

> 前端（Vue 3 + Pinia）所有API调用仅处理 `BFFResponse<T>` 格式，通过 `success` 字段分流成功/失败逻辑，无需关心底层是Koa BFF代理还是FastAPI直出。
