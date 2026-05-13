# 错误码体系

> **PRD来源**：§9.4 统一错误处理规范（V3.5核查修复）

---

## 1. 错误码范围

| 错误码范围 | 类别 | 示例 |
|-----------|------|------|
| 10000-19999 | 业务逻辑错误 | 10001=内部服务器错误, 10002=数据库错误, 候选人已存在、岗位已关闭 |
| 20000-29999 | 权限与认证错误 | 20001=未认证, 20002=权限不足, 20003=Token过期, RBAC拒绝 |
| 30000-39999 | 数据校验错误 | 30001=岗位不存在, 30002=简历解析失败, 字段缺失、格式非法, 乐观锁冲突 |
| 40000-49999 | AI服务错误 | 40001=LLM超时, 40002=Prompt渲染失败, 40003=降级触发, 输出校验失败 |
| 50000-59999 | 外部服务错误 | 50001=参数校验失败, 50002=DDL约束违反, Boss直聘API、OSS上传失败 |
| 60000-69999 | 异步任务错误 | 60001=ARQ任务失败, 60002=dead_letter, 60003=异步任务超时 |

---

## 2. 全局异常处理器（FastAPI）

### 2.1 异常继承层次

```
FastAPI exception_handler 继承层次：
BaseHTTPException → AppException → BusinessException / AuthException / ValidationException / AIServiceException / ExternalServiceException / AsyncTaskException
```

### 2.2 异常处理规则

- 每个异常类携带 `error_code`、`message`、`detail`（可选调试信息）
- HireMindBusinessError → 400 + 业务错误码
- HireMindAuthError → 401/403 + 认证错误码
- HireMindAIError → 503 + AI错误码（触发降级链）
- HireMindValidationError → 422 + 校验错误码
- HireMindExternalServiceError → 502 + 外部服务错误码
- HireMindAsyncTaskError → 500 + 异步任务错误码
- 未预期异常 → 500 + 10001（全量日志，脱敏响应）

### 2.3 统一API响应格式

```json
{
  "success": false,
  "error": {
    "code": 30001,
    "message": "岗位不存在",
    "detail": "Position ID xxx not found in tenant yyy",
    "trace_id": "abc-123"
  }
}
```

API响应统一格式：`{"success": false, "error": {"code": 40001, "message": "...", "detail": "..."}, "request_id": "..."}`

---

## 3. Tool层异常格式化

Agent Tool层捕获Service异常后格式化为Agent可理解的消息：

| 异常类型 | 格式化策略 |
|---------|-----------|
| BusinessException | 自然语言提示（"该岗位不存在，请确认后重试"） |
| AIException | 降级提示（"AI分析暂时不可用，已切换备用模型"） |
| 其他异常 | 通用错误提示（"操作失败，请稍后重试"） |

---

## 4. 异步任务失败感知链（V3.6架构修复C-01+C-06）

```
ARQ Worker → on_failure callback → 
  1. 写入 task_events 表（status=failed, error_code, retry_count）
  2. 触发 Redis Pub/Sub channel: `task:failed:{task_type}`
  3. SSE推送至在线用户（前端Toast + 任务中心红点）
  4. 若3次重试仍失败 → dead_letter队列 → 
     a. 写入 dead_letter_tasks 表
     b. 触发主动式AI通知（场景7：系统异常告警）
     c. Cron每小时扫描 dead_letter → 自动重试或人工介入提示
```

---

## 5. 异步任务触发链（V3.6架构修复C-01+C-02+C-03）

所有异步任务完成后必须通过 ARQ `on_complete` 回调触发下游，禁止使用 Redis Pub/Sub 或直接调用：

| 触发链 | on_complete 定义 |
|--------|-----------------|
| 简历解析完成 → 向量化 → 匹配刷新 | `parse_resume.on_complete = vectorize_resume` → `vectorize_resume.on_complete = refresh_match` |
| 岗位JD生成完成 → 岗位向量化 → 匹配刷新 | `generate_jd.on_complete = vectorize_position` → `vectorize_position.on_complete = refresh_match` |
| Offer接受 → 候选人状态级联 | `accept_offer.on_complete = cascade_hire`（关闭其他Offer + 归档候选人 + 删除候选人向量） |
| 面试反馈提交 → 匹配分数刷新 | `submit_feedback.on_complete = refresh_match_score` |

### 5.1 on_complete回调要求

每个 on_complete 回调必须：
- **幂等性保证**：通过 task_events 表去重
- **失败重试**：最多3次，指数退避
- **超时上限**：on_complete 执行不超过30s
