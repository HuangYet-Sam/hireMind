# HireMind — AI原生招聘系统

> 基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) + [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) Fork 构建的智能招聘管理平台。

## 项目架构

```
┌─────────────────────────────────────────────────────────────┐
│  用户交互层                                                   │
│  ├── Hermes Agent (:8642) — AI引擎 + IM接入(微信/飞书/钉钉)  │
│  └── Web前端 (hireMind Fork, :8648)                          │
│      ├── 招聘业务(8-10页自研): /hr/* 路由                     │
│      └── 管理后台(16页复用): /hermes/* 路由                   │
├─────────────────────────────────────────────────────────────┤
│  FastAPI API Gateway (:8000) — 业务API + AI能力端点          │
├─────────────────────────────────────────────────────────────┤
│  Service层 — 唯一业务逻辑归属 (Python)                        │
├─────────────────────────────────────────────────────────────┤
│  HR招聘工具层 (Hermes Agent 扩展)                             │
│  ├── Tools (12个 hr_* tools)                                 │
│  ├── MCP Servers (boss-zhipin / feishu-calendar)             │
│  └── Skills (8个招聘流程 Skill)                               │
├─────────────────────────────────────────────────────────────┤
│  数据层: PostgreSQL(pgvector) + Redis + MinIO                │
└─────────────────────────────────────────────────────────────┘
```

## Fork 信息

- **上游仓库**: [EKKOLearnAI/hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui)
- **Fork 仓库**: [HuangYet-Sam/hireMind](https://github.com/HuangYet-Sam/hireMind) (`base` 分支)
- **技术栈**: Vue 3.5 + Vite 8 + Naive UI + Pinia 3 + Vue Router 4 + Koa 2
- **Monorepo**: `packages/client` + `packages/server`

## 目录结构

```
hireMind/                    ← Fork自 hermes-web-ui
├── packages/
│   ├── client/              ← Vue 3 前端 (Vite + Naive UI)
│   │   └── src/
│   │       ├── views/hermes/  ← 16页管理后台(复用)
│   │       ├── views/hr/      ← 招聘业务页面(自研)
│   │       ├── components/
│   │       ├── stores/
│   │       ├── api/
│   │       └── router/
│   ├── server/              ← Koa 2 BFF
│   │   └── src/
│   └── api/                 ← FastAPI 招聘业务API
│       ├── app/             ← FastAPI应用
│       ├── alembic/         ← 数据库迁移
│       ├── tests/           ← 测试
│       └── Dockerfile
├── docs/                    ← 项目设计文档
├── prd/                     ← PRD V3.6 + 审计报告
└── scripts/                 ← 开发/部署脚本
```

## 开发指南

详见 [CLAUDE.md](./CLAUDE.md) 或 PRD V3.6 (`prd/HireMind-PRD-V3.6.md`)

## 许可证

MIT (继承 hermes-web-ui 许可证)
