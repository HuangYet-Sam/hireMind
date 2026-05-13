# 技术栈

> 源自 PRD V3.6 §12 + hireMind Fork 实际版本核实  
> 更新日期：2026-05-12

---

## 1. 前端技术栈（来自 hireMind Fork）

| 技术 | 版本 | 用途 | 来源 |
|------|------|------|------|
| Vue | ^3.5.32 | 前端框架 | hermes-web-ui |
| Vite | ^8.0.4 | 构建工具 | hermes-web-ui |
| Naive UI | ^2.44.1 | UI组件库 | hermes-web-ui |
| Pinia | ^3.0.4 | 状态管理 | hermes-web-ui |
| Vue Router | ^4.6.4 | 路由 | hermes-web-ui |
| vue-i18n | ^11.3.2 | 国际化(8语言含中文) | hermes-web-ui |
| Socket.IO | ^4.8.3 | 实时通信 | hermes-web-ui |
| Monaco Editor | ^0.55.1 | 代码编辑器 | hermes-web-ui |
| xterm.js | ^6.0.0 | 终端模拟器 | hermes-web-ui |
| Mermaid | ^11.14.0 | 图表渲染 | hermes-web-ui |
| TypeScript | ~6.0.2 | 类型系统 | hermes-web-ui |
| Node.js | >=23.0.0 | 运行时 | hermes-web-ui |

## 2. BFF层技术栈（来自 hireMind Fork packages/server）

| 技术 | 版本 | 用途 |
|------|------|------|
| Koa | ^2.15.3 | BFF框架 |
| @koa/router | ^15.4.0 | 路由 |
| @koa/cors | ^5.0.0 | CORS |
| @koa/bodyparser | ^5.0.0 | 请求解析 |
| Pino | ^10.3.1 | 日志 |
| ts-node | ^10.9.2 | TypeScript运行 |

## 3. 后端技术栈（待创建）

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 后端语言 |
| FastAPI | 0.115+ | API框架 |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.13+ | 数据库迁移 |
| Pydantic | 2.0+ | 数据校验 |
| asyncpg | 0.30+ | PostgreSQL异步驱动 |
| LiteLLM | 1.50+ | LLM多Provider路由 |
| structlog | 24.0+ | 结构化日志 |
| httpx | 0.27+ | HTTP客户端 |
| python-jose | 3.3+ | JWT |
| minio | 7.2+ | 对象存储客户端 |
| redis | 5.0+ | 缓存客户端 |

## 4. AI引擎（Hermes Agent）

| 组件 | 说明 |
|------|------|
| Hermes Agent | AI引擎框架（直接使用，不Fork） |
| Tools扩展 | 12个 hr_* 工具文件 |
| Skills扩展 | 8个招聘流程Skill |
| MCP Servers | boss-zhipin-mcp + feishu-calendar-mcp |
| Cron Jobs | 定时招聘任务 |
| Memory | 三层记忆体系(L1偏好/L2组织/L3决策) |

## 5. 数据存储

| 技术 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 17 | 主数据库 |
| pgvector | 0.8+ | 向量检索(HNSW+SQ8) |
| Redis | 7 | 缓存+限流+Pub-Sub |
| MinIO | latest | 简历文件+附件存储 |
| SQLite | 内置 | Session存储+Kanban(hermes-web-ui) |

## 6. 监控与运维

| 技术 | 用途 |
|------|------|
| Prometheus | 指标采集 |
| Grafana | 监控Dashboard |
| Loki | 日志聚合 |
| Sentry | 错误追踪 |
| AlertManager | 告警(→微信) |
| OTel SDK | 分布式追踪 |

## 7. 部署

| 技术 | 用途 |
|------|------|
| Docker | 容器化 |
| Docker Compose | 多服务编排 |
| Caddy | 反向代理+自动HTTPS |
| GitHub Actions | CI/CD |

## 8. 开发工具

| 技术 | 用途 |
|------|------|
| pnpm | 前端包管理 |
| pip / poetry | 后端包管理 |
| Vitest | 前端单元测试 |
| pytest | 后端单元测试 |
| ruff | Python Lint |
| mypy | Python类型检查 |
| ESLint | TypeScript Lint |
