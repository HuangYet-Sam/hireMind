# 监控告警与日志规范

> 源自 PRD V3.6 §11.5 监控与告警 + §11.6 日志规范（L6273-L6303）
> PRD原文：`prd/HireMind-PRD-V3.6.md`

---

## §11.5 监控与告警

| 监控项 | 工具 | 告警阈值 |
|--------|------|---------|
| API响应时间 | Prometheus + Grafana | P95 > 5s |
| 错误率 | Prometheus | 5xx > 1% |
| LLM调用成本 | hermes-web-ui Analytics面板 | 日消费 > 预算120% |
| 简历解析队列 | 自定义指标 | 积压 > 500份 |
| Agent可用性 | 健康检查 | 心跳丢失 > 3min |

---

## §11.6 日志规范

| 日志类别 | 格式 | 存储位置 | 保留期限 |
|---------|------|---------|---------|
| API访问日志 | JSON: `{timestamp, method, path, status, duration_ms, user_id, tenant_id}` | `/var/log/hiremind/api.log` + Loki | 30天 |
| Agent决策日志 | JSON: `{timestamp, task, input_hash, model, tokens, output_hash, confidence}` | PostgreSQL `ai_decisions` 表 | 永久（可审计） |
| 错误日志 | JSON: `{timestamp, level, module, message, stack_trace, request_id}` | `/var/log/hiremind/error.log` + Sentry | 90天 |
| 审计日志 | JSON: `{timestamp, user_id, action, entity_type, entity_id, before, after}` | PostgreSQL `audit_log` 表 | 永久 |
| 前端日志 | Sentry Breadcrumb | Sentry | 30天 |

**敏感信息处理**：所有日志写入前经过脱敏过滤器（正则匹配手机号/身份证/银行卡号→`***`）。

**错误分级与响应策略**：

| 级别 | 定义 | 典型场景 | 响应措施 |
|------|------|---------|---------|
| **P0-Critical** | 服务不可用/核心业务中断 | 数据库宕机、LLM大面积故障(>50%请求失败)、认证服务崩溃 | 立即通知（邮件+IM），5min内响应 |
| **P1-Error** | 单个功能失败 | 单个API 5xx、LLM单次超时/限流、文件上传失败 | 记录日志 + 5min内聚合告警（同类型>3次触发通知） |
| **P2-Warning** | 性能下降/非关键异常 | API响应P95超阈值但可用、LLM重试后成功、队列积压 | 仅记录，日报汇总 |
| **P3-Info** | 正常业务日志 | CRUD操作、AI推理完成、定时任务执行 | 仅记录，用于审计追踪 |
