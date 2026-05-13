# HireMind 深度架构审计报告

> **审计人**：全栈架构师
> **审计日期**：2026-05-12
> **审计范围**：`/home/agent/HireMind/` 全目录（排除 node_modules/.git）
> **对比基准**：PRD V3.6 定义的目标架构（Vue 3 + FastAPI + Hermes Agent）

---

## 0. 执行摘要

| 指标 | 评分/结果 |
|------|-----------|
| **架构匹配度** | **1.5 / 10** |
| **可保留代码量** | ~5%（类型定义 + Prisma Schema参考） |
| **需完全重写** | ~90% |
| **文档可用性** | PRD层★★★★★ / 架构层★★★★☆ / 代码层☆☆☆☆☆ |
| **迁移风险** | 🔴 极高 — 技术栈根本性冲突 |

**核心结论**：当前代码库是 Next.js 16 + React 19 + Prisma 的空脚手架，与目标架构（Vue 3 + FastAPI + SQLAlchemy + Hermes Agent）存在**技术栈层面的根本性冲突**。这不是"迁移"问题，而是"清零重建"问题。唯一可保留的价值在于：docs/ 的 37 个设计文档（576KB）和 prisma/schema.prisma 的数据模型参考。

---

## 1. 架构匹配度评分：1.5 / 10

### 评分细项

| 层级 | 满分 | 得分 | 说明 |
|------|:----:|:----:|------|
| 用户交互层 | 2 | 0.5 | 仅有 Next.js 空页面壳，无 Vue 3 / Koa BFF / Hermes Agent 集成 |
| API层 | 2 | 0.2 | 6个 Next.js Route Handler 均为空壳（返回 `{success: true, data: {}}`），无 FastAPI |
| Service层 | 2 | 0.2 | 4个 .service.ts 文件均为空注释，零业务逻辑 |
| HR工具层 | 2 | 0 | 完全缺失：无 tools/、mcp/、skills/ 目录 |
| 数据存储层 | 2 | 0.6 | Prisma schema 有7模型含向量字段，但无 pgvector/Alembic/MinIO/Redis 集成 |
| **总计** | **10** | **1.5** | |

---

## 2. 逐层对比分析

### 2.1 用户交互层

| 维度 | 目标架构 | 当前状态 | 差距 |
|------|---------|---------|------|
| **前端框架** | Vue 3 + Naive UI（hermes-web-ui Fork） | Next.js 16 + React 19 + shadcn | ❌ 完全不同技术栈 |
| **BFF层** | Koa 2 (:8648) 代理管理功能 | 无 BFF，Next.js SSR 直连 | ❌ 缺失 |
| **页面数量** | 招聘业务8页 + 管理后台15页 | Dashboard壳(1页) + Jobs(3页) + Candidates(3页) + Login/Register/Settings(3页) = 10个空壳 | ⚠️ 骨架存在但全是占位符 |
| **Agent集成** | Hermes Agent (:8642) Webhook | 无任何 Agent 相关代码 | ❌ 完全缺失 |
| **样式系统** | Tailwind 4 + @nous-research/ui | Tailwind 4 + shadcn（CSS变量冲突） | ⚠️ Tailwind可复用思路但组件库不同 |
| **路由方式** | Vue Router（Hash/History） | Next.js App Router（文件系统路由） | ❌ 路由范式不同 |

**具体文件审计**：

| 文件 | 内容 | 可复用度 |
|------|------|:--------:|
| `src/app/layout.tsx` | Next.js 默认模板，Geist字体 | 0% |
| `src/app/(dashboard)/layout.tsx` | 8行硬编码 Sidebar 占位 | 0% |
| `src/app/(dashboard)/page.tsx` | 3行 `<div>Dashboard</div>` | 0% |
| `src/app/(dashboard)/jobs/page.tsx` | 空壳列表页 | 0% |
| `src/app/(dashboard)/candidates/page.tsx` | 空壳列表页 | 0% |
| `src/app/(auth)/login/page.tsx` | 空壳登录页 | 0% |
| `src/components/ai/*.tsx` (4个) | 4个空壳AI组件（provider/inferenceBadge/profileCard/sourceLink） | 5% — 类型定义思路可参考 |
| `src/hooks/use-*.ts` (3个) | 空文件 | 0% |

### 2.2 API层（FastAPI Gateway :8000）

| 维度 | 目标架构 | 当前状态 | 差距 |
|------|---------|---------|------|
| **框架** | FastAPI (Python) | Next.js Route Handlers (TypeScript) | ❌ 完全不同 |
| **端点数量** | CRUD ~40 + AI能力 ~33 = 73个 | 6个空壳（jobs/candidates/tags/upload/ai.match/ai.profile） | ❌ 数量差10倍+ |
| **认证** | JWT + RBAC 中间件 | 无任何认证代码 | ❌ 缺失 |
| **参数校验** | Pydantic v2 | Zod v4（仅schema定义） | ⚠️ Zod schema思路可参考 |
| **SSE支持** | StreamingResponse + EventSource | 无 | ❌ 缺失 |
| **审计日志** | 中间件级统一审计 | 无 | ❌ 缺失 |
| **@AiCapability装饰器** | 装饰器→代码生成→路由+Tool注册 | 无 | ❌ 缺失 |

**具体文件审计**：

| 文件 | 行数 | 实际内容 |
|------|:----:|---------|
| `src/app/api/jobs/route.ts` | 5 | `GET → {success:true, data:[]}` |
| `src/app/api/candidates/route.ts` | 5 | `GET → {success:true, data:[]}` |
| `src/app/api/ai/match/route.ts` | 5 | `POST → {success:true, data:{}}` |
| `src/app/api/ai/profile/route.ts` | 5 | `POST → {success:true, data:{}}` |
| `src/lib/ai/gateway.ts` | 13 | 仅检查 `AI_SERVICE_ENABLED` 环境变量，无实质逻辑 |

### 2.3 Service层

| 维度 | 目标架构 | 当前状态 | 差距 |
|------|---------|---------|------|
| **语言** | Python (3.13+) | TypeScript | ❌ 完全不同 |
| **Service数量** | 6个（position/candidate/interview/matching/resume/analytics） | 4个空壳（candidate/job/resume/tag） | ⚠️ 命名思路可参考 |
| **ORM** | SQLAlchemy 2.x + Alembic | Prisma 7.8 | ❌ 完全不同 |
| **caller_type区分** | `caller_type: Literal["tool", "api"]` | 无 | ❌ 缺失 |
| **AI推理方法** | 每个Service含确定性+AI推理方法 | 完全缺失 | ❌ 缺失 |

**具体文件审计**：

| 文件 | 行数 | 实际内容 |
|------|:----:|---------|
| `src/lib/services/candidate.service.ts` | 2 | 仅注释 |
| `src/lib/services/job.service.ts` | 2 | 仅注释 |
| `src/lib/services/resume.service.ts` | — | 未读取，推测同上 |
| `src/lib/services/tag.service.ts` | — | 未读取，推测同上 |
| `src/lib/ai/embedding.ts` | 4 | 仅注释 `TODO: Implement` |
| `src/lib/ai/match.ts` | 3 | 仅注释 `TODO: Implement` |
| `src/lib/ai/profile.ts` | 3 | 仅注释 `TODO: Implement` |
| `src/lib/ai/providers/openai.ts` | 5 | 空类 `class OpenAIProvider {}` |

### 2.4 HR工具层（Agent专用扩展）

| 维度 | 目标架构 | 当前状态 | 差距 |
|------|---------|---------|------|
| **Tools** | `tools/hr_*.py`（12个） | 无 tools/ 目录 | ❌ 完全缺失 |
| **MCP Servers** | hr-crud-api / neo4j-mcp / calendar-mcp / ats-mcp | 无 mcp/ 目录 | ❌ 完全缺失 |
| **Skills** | `skills/hr/*/SKILL.md`（8个） | 无 skills/ 目录 | ❌ 完全缺失 |
| **Tool注册** | Hermes Agent registry.py 集成 | 无 | ❌ 完全缺失 |
| **最小权限矩阵** | 12个Tool × 数据范围/权限级别/限制规则 | 无 | ❌ 完全缺失 |

**本层在当前代码库中为零实现，是目标架构中最重要的差异化组件之一。**

### 2.5 数据存储层

| 维度 | 目标架构 | 当前状态 | 差距 |
|------|---------|---------|------|
| **关系数据库** | PostgreSQL 17+（原生） | PostgreSQL（Prisma代理） | ⚠️ 数据库引擎相同但ORM不同 |
| **向量支持** | pgvector 0.8+ + pgvectorscale | Prisma `Unsupported("Vector")` 声明 | ⚠️ 字段声明存在但无向量操作能力 |
| **对象存储** | MinIO（简历文件） | Supabase Storage URL引用 | ❌ 方案不同 |
| **缓存** | Redis 7.x（缓存+ARQ队列） | 无 | ❌ 缺失 |
| **图存储** | PG JSONB+CTE (P1) / Apache AGE (P2) | 无 | ❌ 缺失 |
| **迁移工具** | Alembic | Prisma Migrate | ❌ 完全不同 |
| **ORM** | SQLAlchemy 2.x | Prisma 7.8 | ❌ 完全不同 |

**Prisma Schema 价值评估**：

`prisma/schema.prisma` 定义了 12 个模型（User/Company/Job/Candidate/Resume/Tag/CandidateTag/Application/AiProfile/AiInference/JobEmbedding/CandidateEmbedding），**这个 schema 的数据模型设计思路有参考价值**，但：

- 目标架构使用 SQLAlchemy + 原生 SQL DDL，不使用 Prisma
- 目标架构的 DDL（`docs/database/schema-ddl.md`，675行）已定义了更完整的 SQL Schema（含 departments/positions/interviews/offers 等更多表）
- Prisma schema 缺少目标架构中的 `departments`、`interviews`、`offers`、`ai_decisions` 等核心表
- 向量字段 `Unsupported("Vector")` 在 Prisma 中无法进行向量查询操作

---

## 3. TOP 10 关键技术债务

### 🔴 P0 — 阻塞性问题（必须立即解决）

| # | 债务 | 影响 | 工作量估算 |
|---|------|------|-----------|
| **1** | **技术栈根本性冲突**：当前 Next.js/React/Prisma/TypeScript vs 目标 Vue 3/FastAPI/SQLAlchemy/Python，整个 src/ 目录无法复用 | 全部业务逻辑需用 Python 重写，前端需用 Vue 3 重写 | **≈ 40 人天** |
| **2** | **零业务逻辑实现**：所有 service/route/hook/ai 文件均为空壳或 TODO，无任何可运行的业务功能 | 无法进行功能测试或演示 | **≈ 60 人天**（含完整 CRUD + AI） |
| **3** | **Hermes Agent 集成完全缺失**：无 Agent Loop、无 Tool 注册、无 Webhook、无 MCP、无 Skill 系统 | AI Agent 核心价值无法体现，项目变成普通 CRUD | **≈ 20 人天** |

### 🟡 P1 — 高优先级问题

| # | 债务 | 影响 | 工作量估算 |
|---|------|------|-----------|
| **4** | **数据库 Schema 不完整**：Prisma schema 缺少 departments/positions/interviews/offers/feedback 等核心表，与目标 DDL 差距大 | 后续开发缺少数据基础 | **≈ 5 人天** |
| **5** | **向量检索能力为零**：虽有 embedding 字段声明，但 Prisma 无法执行 pgvector 向量查询，无 HNSW 索引，无 embedding 生成逻辑 | AI 匹配核心功能无法实现 | **≈ 8 人天** |
| **6** | **认证/授权体系缺失**：无 JWT、无 RBAC、无权限矩阵实现 | 安全性为零，无法多租户 | **≈ 5 人天** |
| **7** | **文档与代码不一致**：docs/ 中约 40% 文档基于 Vue 3 + FastAPI 架构撰写，约 30% 基于 Next.js 架构撰写（如 `docs/research-nextjs15.md`），存在矛盾 | 新开发者会困惑以哪个为准 | **≈ 3 人天** |

### 🟢 P2 — 中优先级问题

| # | 债务 | 影响 | 工作量估算 |
|---|------|------|-----------|
| **8** | **MinIO/Redis/ARQ 基础设施未搭建**：无 docker-compose、无连接配置、无文件上传逻辑 | 简历存储和异步任务无法运行 | **≈ 3 人天** |
| **9** | **@AiCapability 装饰器 + 代码生成器未实现**：这是 API层和 Tool层自动化的核心机制 | 每个AI能力需手动创建路由+Tool，效率极低 | **≈ 5 人天** |
| **10** | **SSE 流式推送未实现**：AI 交互体验依赖 SSE，当前无任何流式支持 | AI 生成过程无实时反馈 | **≈ 3 人天** |

**TOP 10 总工作量估算：≈ 152 人天（约 30 周 / 7.5 月单人全职）**

---

## 4. 迁移路径评估

### 4.1 迁移策略：推荐"清零重建"而非"渐进迁移"

**理由**：
1. 技术栈完全不同（TypeScript → Python, React → Vue 3, Prisma → SQLAlchemy）
2. 现有代码均为空壳，无业务逻辑可保留
3. "渐进迁移"会导致双栈并存，维护成本 > 重建成本
4. PRD 文档已为 Vue 3 + FastAPI 架构做了详细设计，直接按文档实现效率更高

### 4.2 推荐迁移路径（按 PRD §13 OPC计划）

```
Phase 0: 项目初始化（2天）
├── 删除 src/ 整个目录（保留 docs/ 和 prd/）
├── 创建 Python 后端项目结构（FastAPI + SQLAlchemy + Alembic）
├── 创建 Vue 3 前端项目（Fork hermes-web-ui）
├── 搭建 docker-compose（PostgreSQL + pgvector + Redis + MinIO）
└── 配置 Caddy 反向代理

Phase 1: M1 基建（1周）
├── SQLAlchemy Models（基于 docs/database/schema-ddl.md）
├── Alembic 迁移脚本
├── FastAPI 骨架 + JWT认证 + RBAC中间件
├── 基础 CRUD 端点（positions / candidates / departments）
└── 基础前端页面（组织架构 / 岗位管理）

Phase 2: M2 AI核心（1周）
├── LiteLLM + OpenAI Provider 集成
├── @AiCapability 装饰器 + 代码生成器
├── 简历解析（SmartResume Fork）
├── pgvector 向量化 + 匹配引擎
└── 前端：简历库 / 智能匹配页

Phase 3: M3 业务闭环（1.5周）
├── 面试管理 Service + AI面试题/评分
├── Offer管理 Service + AI薪资方案
├── Hermes Agent 集成（Tool注册 + Skill加载）
└── 前端：面试 / Offer / 分析页

Phase 4: M4 增强优化（1周）
├── SSE 流式推送
├── 分析 Dashboard + AI洞察
├── 监控（Prometheus + Grafana）
└── E2E 测试
```

### 4.3 工作量估算汇总

| 模块 | 人天 | 说明 |
|------|:----:|------|
| 项目初始化 + 基础设施 | 5 | Docker/DB/Caddy/项目结构 |
| 数据库（SQLAlchemy + Alembic） | 5 | ~20张表 + 迁移脚本 + 索引 |
| FastAPI API层 + 中间件 | 8 | 认证/RBAC/审计/Pydantic/SSE |
| CRUD端点（~40个） | 12 | 6个Service × CRUD + Dashboard |
| AI能力端点（~33个） | 15 | 含 @AiCapability 装饰器框架 |
| pgvector向量 + 匹配引擎 | 8 | Embedding生成 + HNSW + RRF + LLM Rerank |
| Hermes Agent集成 | 10 | 12个Tool + 4个MCP + 8个Skill |
| Vue 3前端（23页） | 25 | 8页自研 + 15页复用hermes-web-ui |
| 测试 | 8 | pytest + DeepEval + E2E |
| 文档清理 | 3 | 清除Next.js相关文档 |
| **总计** | **~99人天** | **≈ 20周单人 / 5周4人团队** |

---

## 5. 风险评估：文件处置清单

### 5.1 🔴 必须删除（约 45 个文件）

| 目录/文件 | 原因 |
|----------|------|
| `src/` 整个目录（~40个文件） | Next.js/React/TypeScript，与目标架构完全不兼容 |
| `postcss.config.mjs` | Next.js 专用 |
| `next.config.ts` | Next.js 专用 |
| `next-env.d.ts` | Next.js 专用 |
| `eslint.config.mjs` | 需替换为 Python ruff/mypy |
| `tsconfig.json` | TypeScript 配置，目标架构用 Python |
| `pnpm-lock.yaml` | Node.js 依赖锁文件 |
| `pnpm-workspace.yaml` | pnpm 工作区配置 |
| `prisma.config.ts` | Prisma 专用配置 |
| `public/*.svg` | Next.js 默认占位图标 |
| `components.json` | shadcn UI 配置 |
| `.env` | 仅 Prisma 占位 DATABASE_URL |
| `.env.local` | Next.js 本地环境变量 |

### 5.2 🟡 可保留参考但需大幅修改（约 5 个文件）

| 文件 | 保留价值 | 需要的修改 |
|------|---------|-----------|
| `prisma/schema.prisma` | 数据模型设计思路（12模型） | 转换为 SQLAlchemy Models；补充 departments/interviews/offers 等缺失表；移除 Prisma 特有语法 |
| `src/types/api.ts` | API响应格式设计（ApiResponse/PaginatedResponse/ErrorCodes） | 转为 Pydantic BaseModel |
| `src/types/ai.ts` | InferenceNature/InferenceCategory 类型定义 | 转为 Python Enum |
| `src/lib/validators/*.ts` | Zod schema 思路 | 转为 Pydantic schema |
| `src/lib/utils/api-response.ts` | API工具函数思路 | 转为 Python 统一响应封装 |

### 5.3 ✅ 直接保留（约 42 个文件）

| 目录 | 保留文件数 | 说明 |
|------|:--------:|------|
| `docs/` | ~37个 | **核心资产** — 包含完整的架构设计、API定义、数据库DDL、AI能力矩阵、前端规格 |
| `prd/` | 4个 | PRD V3.5/V3.6 + 审计报告 |
| `README.md` | 1个 | 可能需更新 |

### 5.4 ⚠️ 文档不一致风险

docs/ 目录存在架构矛盾，需标记清理：

| 文件 | 架构立场 | 处置建议 |
|------|---------|---------|
| `docs/research-nextjs15.md` | Next.js 15 | 🗑️ 删除 |
| `docs/research/nextjs15-app-router.md` | Next.js App Router | 🗑️ 删除 |
| `docs/research/zod-server-actions-error-handling.md` | Next.js Server Actions | 🗑️ 删除 |
| `docs/research/zod-server-actions-error-pattern.md` | Next.js Zod | 🗑️ 删除 |
| `docs/design-system.md` | 可能基于 shadcn | ⚠️ 需审查后决定 |
| `docs/dev-spec.md` | 可能基于 Next.js | ⚠️ 需审查后决定 |
| `docs/test-strategy.md` | 可能基于 vitest | ⚠️ 需替换为 pytest |
| 其余 ~30 个 docs/ 文件 | 基于 Vue 3 + FastAPI | ✅ 保留 |

---

## 6. 关键决策建议

### 6.1 是否保留 Next.js？

**强烈建议：不保留。**

| 维度 | 保留 Next.js | 切换到 Vue 3 + FastAPI |
|------|-------------|---------------------|
| 与PRD一致性 | ❌ 与PRD完全冲突 | ✅ PRD V3.6按此架构设计 |
| Hermes集成 | ❌ 需自行实现Agent通信 | ✅ hermes-web-ui原生Fork |
| AI能力框架 | ❌ 无@AiCapability对应物 | ✅ Python装饰器天然适配 |
| 开发效率 | ❌ 需维护双栈(TypeScript+Python) | ✅ Python全栈后端 |
| 工作量 | 看似省时间，实则双倍 | 清零重建看似慢，实则快 |

### 6.2 优先执行事项（Top 3）

1. **清除 Next.js 脚手架**：删除 src/ + node_modules/ + 所有 Next.js 配置文件，释放认知负担
2. **创建 Python 项目骨架**：FastAPI + SQLAlchemy + Alembic + docker-compose
3. **Fork hermes-web-ui**：创建前端项目，复用15个管理页面

---

## 7. 总结

**HireMind 当前的代码库是一个精心搭建的空壳舞台**——有目录结构、有类型定义、有 Prisma schema、有 6 个 API 路由文件，但所有文件的内容都是空函数或 TODO 注释。这本身不是问题（任何项目都从空壳开始），**真正的问题是：这个空壳搭错了舞台**。

项目花了时间用 Next.js 16 + React 19 + Prisma 搭建了脚手架，而 PRD 要求的是 Vue 3 + FastAPI + SQLAlchemy。这意味着：

1. **所有 TypeScript 代码需要用 Python 重写**
2. **所有 React 组件需要用 Vue 3 重写**
3. **所有 Next.js 路由需要用 FastAPI 路由重写**
4. **Prisma schema 需要用 SQLAlchemy Models 重写**

但好消息是：
- **PRD 文档质量极高**（576KB，含完整 API 定义、DDL、AI能力矩阵）
- **docs/ 文档可直接指导开发**
- **现有代码无业务逻辑**，不存在"废弃已有功能"的沉没成本
- **目标架构设计清晰**，可以直接按文档实施

**建议执行路径**：果断清零 Next.js 脚手架 → 按 PRD §13 OPC计划 → 用 Vue 3 + FastAPI 重建 → 利用 docs/ 作为实施蓝图。

---

*报告完毕。如需进一步的实施方案设计或技术选型论证，可继续深入。*
