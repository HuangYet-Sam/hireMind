# HireMind 开发文档

> 从 PRD V3.6（7754行）按开发关注点重组为独立文档，便于编码时快速查阅。
> PRD原文：`prd/HireMind-PRD-V3.6.md`

---

## 🏗️ 架构 (architecture/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [system-overview.md](architecture/system-overview.md) | 系统整体架构、Agent与BFF和API的关系 | 搭建项目/理解全局架构 |
| [hermes-integration.md](architecture/hermes-integration.md) | Hermes Agent集成方式、Tool/Skill/MCP注册规范 | 开发Agent交互功能 |
| [tech-stack.md](architecture/tech-stack.md) | 技术选型完整清单与选型理由 | 技术决策/环境搭建 |

## 🤖 AI 能力 (ai/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [capability-matrix.md](ai/capability-matrix.md) | 21项AI能力完整矩阵、模型选择与降级链 | 了解AI能力范围 |
| [rag-pipeline.md](ai/rag-pipeline.md) | RAG混合检索（pgvector+tsvector RRF融合）实现 | 开发匹配/向量检索 |
| [prompts.md](ai/prompts.md) | 所有Prompt模板（简历解析/JD生成/匹配解释等） | 调优Prompt |
| [skill-library.md](ai/skill-library.md) | 8个招聘Skill定义与编排流程 | 开发Skill |
| [memory-and-proactive.md](ai/memory-and-proactive.md) | AI记忆系统+主动式AI引擎（8场景） | 开发M10模块 |
| [degradation-chains.md](ai/degradation-chains.md) | LLM降级链与AI容错规范 | 处理LLM故障 |
| [safety-and-ethics.md](ai/safety-and-ethics.md) | AI安全伦理规范、数据脱敏Pipeline | 安全合规审查 |

## 🌐 前端 (frontend/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [routes-and-pages.md](frontend/routes-and-pages.md) | 所有页面路由、布局结构、导航设计 | 搭建前端路由 |
| [components-interaction.md](frontend/components-interaction.md) | 核心组件设计（Context Bar/Sidecar/CommandBar等） | 开发UI组件 |
| [state-management.md](frontend/state-management.md) | Pinia状态管理方案 | 管理前端状态 |
| [onboarding-and-navigation.md](frontend/onboarding-and-navigation.md) | 新手引导、全局搜索、外部Token页面 | 开发导航交互 |

## 📡 API (api/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [endpoints-crud.md](api/endpoints-crud.md) | CRUD端点完整定义（岗位/简历/候选人/面试/Offer） | 开发后端API |
| [endpoints-ai-capability.md](api/endpoints-ai-capability.md) | AI能力端点（解析/匹配/生成等） | 开发AI接口 |
| [sse-and-realtime.md](api/sse-and-realtime.md) | SSE流式输出+实时通信规范 | 开发Agent对话 |
| [auth-and-permissions.md](api/auth-and-permissions.md) | JWT认证+RBAC权限+多租户隔离 | 实现安全控制 |
| [bff-koa-endpoints.md](api/bff-koa-endpoints.md) | Koa BFF层端点定义 | 开发BFF接口 |
| [error-codes.md](api/error-codes.md) | 错误码定义与错误处理规范 | 处理错误响应 |

## 🗄️ 数据库 (database/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [schema-ddl.md](database/schema-ddl.md) | 完整DDL（所有表/字段/约束/索引） | 建表/写迁移 |
| [er-diagram.md](database/er-diagram.md) | ER关系图 | 理解数据模型 |
| [indexes-and-vectors.md](database/indexes-and-vectors.md) | pgvector HNSW索引+向量检索配置 | 优化查询性能 |
| [migration-guide.md](database/migration-guide.md) | Alembic迁移策略与规范 | 数据库变更 |

## ✨ 业务功能 (features/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [org-and-positions.md](features/org-and-positions.md) | 组织架构+岗位管理（M1） | 开发岗位模块 |
| [resume-parsing.md](features/resume-parsing.md) | 简历解析（M2），含SmartResume引擎 | 开发简历解析 |
| [candidate-management.md](features/candidate-management.md) | 候选人管理+360°画像（M3） | 开发候选人模块 |
| [intelligent-matching.md](features/intelligent-matching.md) | 智能匹配引擎（M4），RRF+Rerank | 开发匹配算法 |
| [interview-management.md](features/interview-management.md) | 面试管理（M5），含AI安排+题库 | 开发面试模块 |
| [offer-management.md](features/offer-management.md) | Offer管理+审批流（M6） | 开发Offer模块 |
| [dashboard.md](features/dashboard.md) | Dashboard+待办（M7） | 开发工作台 |
| [analytics.md](features/analytics.md) | 招聘分析+AI洞察（M8） | 开发分析模块 |

## 🗺️ 路线图 (roadmap/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [opc-plan.md](roadmap/opc-plan.md) | OPC模块化开发计划（M0-M10，~12个月） | 制定开发计划/跟踪进度 |
| [ai-delivery-matrix.md](roadmap/ai-delivery-matrix.md) | 21项AI能力×OPC模块映射+批次交付计划 | 规划AI能力开发 |
| [risks.md](roadmap/risks.md) | 风险评估与缓解（技术/业务/合规/OPC进度） | 风险管理 |

## ⚙️ DevOps (devops/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [deployment.md](devops/deployment.md) | 部署架构+可扩展性+并发控制规范 | 部署/扩容 |
| [monitoring-and-logging.md](devops/monitoring-and-logging.md) | 监控告警+日志规范+错误分级 | 配置监控 |

## 📚 参考 (reference/)

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [glossary.md](reference/glossary.md) | 术语表（28个核心术语） | 理解文档中的缩写 |

## 📋 其他

| 文件 | 用途 | 何时查阅 |
|------|------|----------|
| [TAD.md](TAD.md) | 技术架构决策记录 | 了解架构决策背景 |
| [dev-spec.md](dev-spec.md) | 开发规范 | 编码规范 |
| [test-strategy.md](test-strategy.md) | 测试策略 | 编写测试 |
| [design-system.md](design-system.md) | 设计系统 | UI设计参考 |
| [research/](research/) | 技术调研笔记 | 了解调研背景 |
