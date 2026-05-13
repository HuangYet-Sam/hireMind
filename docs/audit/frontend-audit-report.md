# HireMind 前端架构审计报告

> **审计角色**: 前端架构师
> **审计日期**: 2026-05-12
> **基准PRD**: HireMind-PRD-V3.6.md
> **审计范围**: src/ 前端资产、docs/frontend/ 和 docs/research/ 文档、目标架构一致性

---

## 一、当前前端资产评估

### 1.1 总览

当前 `src/` 目录包含 **48个文件**，全部基于 **Next.js 15 App Router + React + TypeScript** 技术栈。经逐一审查，**所有文件均为空壳或占位代码**，不含任何可复用的业务逻辑实现。

### 1.2 资产处置清单

#### ❌ 删除（42个文件）——技术栈不兼容

| 分类 | 文件 | 处置理由 |
|------|------|---------|
| **Next.js App Router 页面** (13个) | `src/app/layout.tsx` | React根布局，Vue 3需App.vue替代 |
| | `src/app/page.tsx` | Next.js默认首页，需删除 |
| | `src/app/globals.css` | Next.js全局样式，Naive UI+Tailwind 4替代 |
| | `src/app/(dashboard)/layout.tsx` | React JSX布局组件，Vue Layout替代 |
| | `src/app/(dashboard)/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/candidates/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/candidates/[id]/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/candidates/new/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/jobs/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/jobs/[id]/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/jobs/new/page.tsx` | 占位空壳 |
| | `src/app/(dashboard)/settings/page.tsx` | 占位空壳 |
| | `src/app/(auth)/login/page.tsx` | 占位空壳 |
| | `src/app/(auth)/register/page.tsx` | 占位空壳 |
| **Next.js API Routes** (6个) | `src/app/api/candidates/route.ts` | Next.js Server Route，BFF由Koa替代 |
| | `src/app/api/jobs/route.ts` | 同上 |
| | `src/app/api/tags/route.ts` | 同上 |
| | `src/app/api/upload/route.ts` | 同上 |
| | `src/app/api/ai/match/route.ts` | 同上 |
| | `src/app/api/ai/profile/route.ts` | 同上 |
| **React组件** (4个) | `src/components/ai/ai-provider.tsx` | React Context，Pinia替代 |
| | `src/components/ai/source-link.tsx` | 空壳，Vue SFC重写 |
| | `src/components/ai/inference-badge.tsx` | 空壳，Vue SFC重写 |
| | `src/components/ai/profile-card.tsx` | 空壳，Vue SFC重写 |
| **React Hooks** (3个) | `src/hooks/use-ai-profile.ts` | React Hook，Vue Composable替代 |
| | `src/hooks/use-jobs.ts` | React Hook，Vue Composable替代 |
| | `src/hooks/use-candidates.ts` | React Hook，Vue Composable替代 |
| **React lib层** (7个) | `src/lib/utils.ts` | `cn()` 函数(clsx+tailwind-merge)，Vue版可直接重写 |
| | `src/lib/db.ts` | Prisma Client单例，**后端用SQLAlchemy，前端不用ORM** |
| | `src/lib/validators/job.ts` | Zod空壳，**前端校验用Vuelidate/Naive UI Form Rules** |
| | `src/lib/validators/candidate.ts` | 同上 |
| | `src/lib/services/*.ts` (4个) | 空壳Service，**业务逻辑在Python后端** |
| | `src/lib/ai/gateway.ts` | 空壳，AI调用在FastAPI后端 |
| | `src/lib/ai/match.ts` | 空壳 |
| | `src/lib/ai/profile.ts` | 空壳 |
| | `src/lib/ai/embedding.ts` | 空壳 |
| | `src/lib/ai/providers/openai.ts` | 空壳 |
| **静态资源** | `src/app/favicon.ico` | 需替换为HireMind图标 |

#### 📋 概念迁移（保留设计思路，重写实现）

| 原文件 | 可迁移的概念 | 迁移目标 |
|--------|------------|---------|
| `src/types/api.ts` | ApiResponse/ApiErrorResponse/PaginatedData 类型结构 | Vue 3 TypeScript 接口定义（保持JSON结构一致） |
| `src/types/ai.ts` | InferenceNature/InferenceCategory 枚举 | Vue 3 TypeScript 枚举/类型 |
| `src/lib/utils/pagination.ts` | 分页参数计算逻辑 | Vue Composable `usePagination()` |
| `src/lib/utils/error.ts` | AppError 类 | Vue全局错误处理 |
| `src/lib/utils/api-response.ts` | success/error/paginated 辅助函数 | Vue HTTP Service层（axios instance） |

### 1.3 结论

> **当前 src/ 整体删除率：100%。** 没有任何文件可以直接复用。但 `types/` 和 `lib/utils/` 中的**类型定义和工具函数逻辑**可作为参考，在Vue 3项目中重新实现。

---

## 二、hermes-web-ui Fork策略评估

### 2.1 PRD目标架构（§8.5）

```
技术栈: Vue 3.5 + Vite 7 + Naive UI + Pinia 3 + Vue Router 4 + Koa 2 + Tailwind 4
架构: monorepo (packages/client + packages/server + packages/website)
模式: Fork hermes-web-ui → 保留15页管理后台 → 自研8+7=15页招聘业务
```

### 2.2 Fork后定制策略

#### ✅ 不改（保持与上游同步能力）

| 目录/文件 | 说明 |
|----------|------|
| `packages/client/src/views/chat/` | Chat页面——招聘业务通过Sidecar/Context Bar交互，全屏Chat完全复用 |
| `packages/client/src/views/cron/` | 定时任务管理 |
| `packages/client/src/views/models/` | 模型配置 |
| `packages/client/src/views/env/` | 密钥管理 |
| `packages/client/src/views/channels/` | 频道配置 |
| `packages/client/src/views/skills/` | 技能管理 |
| `packages/client/src/views/profiles/` | Agent人格 |
| `packages/client/src/views/plugins/` | 插件管理 |
| `packages/client/src/views/files/` | 文件管理 |
| `packages/client/src/views/logs/` | 日志查看 |
| `packages/client/src/views/terminal/` | Web终端 |
| `packages/client/src/views/analytics/` | Token分析 |
| `packages/client/src/views/sessions/` | 会话管理 |
| `packages/client/src/views/group-chat/` | 群聊 |
| `packages/server/` (Koa BFF) | 管理功能BFF层，原封不动 |
| Naive UI组件库引用方式 | `@nous-research/ui` npm包，零修改 |

#### 🔧 需改（注入招聘业务逻辑）

| 文件/目录 | 改动内容 |
|----------|---------|
| `packages/client/src/router/index.ts` | **新增招聘业务路由**（/hr/* 15页 + 5条Token URL） |
| `packages/client/src/layouts/MainLayout.vue` | **Sidebar导航扩展**——新增"📋招聘管理"分组（10项） |
| `packages/client/src/layouts/AppHeader.vue` | **新增CommandBar全局搜索**（⌘K） |
| `packages/client/src/stores/` | **新增招聘业务Pinia stores**（candidate/position/match/interview/offer/analytics） |
| `packages/client/src/api/` | **新增招聘业务API层**（指向FastAPI :8000） |
| `packages/client/src/locales/` | **新增招聘业务i18n词条** |
| `vite.config.ts` | **新增代理规则**：`/hr-api/*` → FastAPI :8000 |
| `packages/client/src/components/` | **新增招聘业务共享组件**（AiContextBar/AgentSidecar/CommandBar等） |

#### 🆕 全新自研（不碰上游代码）

| 目录 | 内容 |
|------|------|
| `packages/client/src/views/hr/` | 15个招聘业务页面 |
| `packages/client/src/components/hr/` | 招聘业务专属组件 |
| `packages/client/src/composables/hr/` | 招聘业务Composables |
| `packages/client/src/stores/hr/` | 招聘业务Pinia Stores |

### 2.3 招聘业务目录结构规划

```
packages/client/src/
├── views/hr/                          # 15个招聘业务页面
│   ├── dashboard/                     # 🎯工作台
│   │   └── index.vue
│   ├── positions/                     # 📋岗位管理
│   │   ├── index.vue                  # 岗位列表
│   │   └── [id]/                      # 岗位360°视图
│   │       └── index.vue
│   ├── resumes/                       # 📄简历库
│   │   ├── index.vue                  # 简历列表
│   │   └── [id]/                      # 简历详情
│   │       └── index.vue
│   ├── candidates/                    # 👤候选人管理
│   │   ├── index.vue                  # 候选人列表
│   │   └── [id]/                      # 候选人360°画像
│   │       └── index.vue
│   ├── matching/                      # 🧲智能匹配
│   │   └── index.vue
│   ├── interviews/                    # 📅面试管理
│   │   ├── index.vue                  # 面试列表/日历
│   │   └── [id]/                      # 面试详情
│   │       └── index.vue
│   ├── offers/                        # 💼Offer管理
│   │   ├── index.vue                  # Offer列表
│   │   └── [id]/                      # Offer详情
│   │       └── index.vue
│   ├── analytics/                     # 📊招聘分析
│   │   └── index.vue
│   ├── tasks/                         # 🤖AI任务中心
│   │   └── index.vue
│   └── org-chart/                     # 🏢组织架构
│       └── index.vue
│
├── views/public/                      # Token URL公开页面（无侧边栏布局）
│   ├── feedback/[token]/index.vue     # 面试反馈表单
│   ├── onboarding/[token]/index.vue   # 入职自助页
│   └── share/[token]/index.vue        # 共享招聘看板
│
├── components/hr/                     # 招聘业务共享组件
│   ├── common/                        # 通用业务组件
│   │   ├── AiOperationMenu.vue        # 🤖AI操作菜单
│   │   ├── DualModeCreator.vue        # 双模创建入口（AI引导/手动表单）
│   │   ├── AiGuidedInput.vue          # AI引导式输入组件
│   │   ├── ConfidenceTag.vue          # 置信度标记（🟢🟡🔴）
│   │   └── EntityStatusBadge.vue      # 实体状态徽章
│   ├── ai/                            # AI交互组件
│   │   ├── AiContextBar.vue           # 模式A: AI洞察栏
│   │   ├── AgentSidecar.vue           # 模式B: 右侧对话面板
│   │   ├── AiInsightCard.vue          # AI洞察卡片
│   │   └── AiTaskProgress.vue         # AI任务进度
│   ├── position/                      # 岗位专属组件
│   │   ├── PositionForm.vue           # 岗位表单
│   │   ├── PositionCard.vue           # 岗位卡片
│   │   ├── PositionFunnel.vue         # 岗位招聘漏斗
│   │   └── PositionTimeline.vue       # 岗位生命周期
│   ├── candidate/                     # 候选人专属组件
│   │   ├── ProfileCard.vue            # 画像卡片
│   │   ├── MatchScoreRadar.vue        # 匹配雷达图
│   │   └── ExperienceTimeline.vue     # 经验时间线
│   ├── resume/                        # 简历专属组件
│   │   ├── ResumeUploader.vue         # 简历上传（拖拽+批量）
│   │   ├── ResumePreview.vue          # 简历预览
│   │   └── SourceLink.vue             # 溯源链接
│   ├── interview/                     # 面试专属组件
│   │   ├── InterviewCalendar.vue      # 面试日历
│   │   ├── InterviewScoreForm.vue     # 面试评分表单
│   │   └── InterviewBriefing.vue      # 考察清单
│   ├── offer/                         # Offer专属组件
│   │   ├── OfferSteps.vue             # Offer审批流程
│   │   └── SalarySuggestion.vue       # 薪资建议
│   └── dashboard/                     # 工作台组件
│       ├── TodoList.vue               # 待办清单
│       ├── TodaySchedule.vue          # 今日日程
│       └── QuickMetrics.vue           # 快捷指标
│
├── composables/hr/                    # 招聘业务Composables
│   ├── usePagination.ts               # 分页
│   ├── usePosition.ts                 # 岗位数据操作
│   ├── useCandidate.ts                # 候选人数据操作
│   ├── useResume.ts                   # 简历操作
│   ├── useMatch.ts                    # 匹配操作
│   ├── useInterview.ts                # 面试操作
│   ├── useOffer.ts                    # Offer操作
│   ├── useAiInsight.ts                # AI洞察（Context Bar）
│   ├── useAgentChat.ts                # Agent对话（Sidecar）
│   ├── useCommandSearch.ts            # 全局搜索
│   └── usePageState.ts                # 统一页面状态管理
│
├── stores/hr/                         # 招聘业务Pinia Stores
│   ├── position.ts
│   ├── candidate.ts
│   ├── resume.ts
│   ├── match.ts
│   ├── interview.ts
│   ├── offer.ts
│   ├── analytics.ts
│   ├── navigation.ts                  # 跨页面导航状态
│   └── onboarding.ts                  # 新用户引导状态
│
└── api/hr/                            # 招聘业务API层
    ├── position.ts
    ├── candidate.ts
    ├── resume.ts
    ├── match.ts
    ├── interview.ts
    ├── offer.ts
    ├── analytics.ts
    ├── insight.ts                     # AI洞察
    └── search.ts                      # 全局搜索
```

### 2.4 Vue Router路由组织

```typescript
// router/index.ts — 招聘业务路由 + 管理后台路由共存
const routes: RouteRecordRaw[] = [
  // ─── 招聘业务路由（自研） ───
  {
    path: '/hr',
    component: () => import('@/layouts/HrLayout.vue'),  // 含AI Context Bar插槽
    meta: { requiresAuth: true },
    children: [
      { path: 'dashboard', name: 'hr-dashboard', component: () => import('@/views/hr/dashboard/index.vue') },
      { path: 'positions', name: 'hr-positions', component: () => import('@/views/hr/positions/index.vue') },
      { path: 'positions/:id', name: 'hr-position-detail', component: () => import('@/views/hr/positions/[id]/index.vue') },
      { path: 'resumes', name: 'hr-resumes', component: () => import('@/views/hr/resumes/index.vue') },
      { path: 'resumes/:id', name: 'hr-resume-detail', component: () => import('@/views/hr/resumes/[id]/index.vue') },
      { path: 'candidates', name: 'hr-candidates', component: () => import('@/views/hr/candidates/index.vue') },
      { path: 'candidates/:id', name: 'hr-candidate-detail', component: () => import('@/views/hr/candidates/[id]/index.vue') },
      { path: 'matching', name: 'hr-matching', component: () => import('@/views/hr/matching/index.vue') },
      { path: 'interviews', name: 'hr-interviews', component: () => import('@/views/hr/interviews/index.vue') },
      { path: 'interviews/:id', name: 'hr-interview-detail', component: () => import('@/views/hr/interviews/[id]/index.vue') },
      { path: 'offers', name: 'hr-offers', component: () => import('@/views/hr/offers/index.vue') },
      { path: 'offers/:id', name: 'hr-offer-detail', component: () => import('@/views/hr/offers/[id]/index.vue') },
      { path: 'analytics', name: 'hr-analytics', component: () => import('@/views/hr/analytics/index.vue') },
      { path: 'tasks', name: 'hr-tasks', component: () => import('@/views/hr/tasks/index.vue') },
      { path: 'org-chart', name: 'hr-org-chart', component: () => import('@/views/hr/org-chart/index.vue') },
    ]
  },

  // ─── 管理后台路由（复用hermes-web-ui） ───
  { path: '/chat', name: 'chat', component: () => import('@/views/chat/index.vue') },
  { path: '/cron', name: 'cron', component: () => import('@/views/cron/index.vue') },
  { path: '/models', name: 'models', component: () => import('@/views/models/index.vue') },
  // ... 其余管理页面

  // ─── 公开路由（Token URL，无侧边栏） ───
  {
    path: '/feedback/:token',
    name: 'feedback',
    component: () => import('@/views/public/feedback/[token]/index.vue'),
    meta: { public: true }
  },
  {
    path: '/onboarding/:token',
    name: 'onboarding',
    component: () => import('@/views/public/onboarding/[token]/index.vue'),
    meta: { public: true }
  },
  {
    path: '/share/:token/dashboard',
    name: 'share-dashboard',
    component: () => import('@/views/public/share/[token]/index.vue'),
    meta: { public: true }
  },
]
```

**路由设计要点**：
- 招聘业务路由统一 `/hr` 前缀，与hermes-web-ui管理页面路由（`/chat`、`/models`等）完全隔离
- 详情页使用 `?tab=` query参数切换内部视图，禁止L3嵌套L4
- Token URL路由使用独立Layout（无侧边栏），`meta.public = true` 跳过认证守卫
- 默认路由 `/` 重定向到 `/hr/dashboard`（工作台为系统首页）

### 2.5 Pinia状态管理方案

```
Store架构：

全局 Stores（跨业务）
├── navigationStore     # 跨页面状态保存（列表筛选/分页/滚动位置/选中项）
├── onboardingStore     # 新用户引导状态（not_started → completed/skipped）
├── authStore           # 认证状态（JWT Token + 用户信息 + RBAC角色）
└── commandSearchStore  # 全局搜索状态

招聘业务 Stores（按实体划分）
├── positionStore       # 岗位列表+当前岗位详情+CRUD状态
├── candidateStore      # 候选人列表+360°画像+画像Tab数据
├── resumeStore         # 简历列表+上传进度+解析状态
├── matchStore          # 匹配看板数据+匹配配置+批量匹配状态
├── interviewStore      # 面试列表+日历数据+面试详情+评分
├── offerStore          # Offer列表+审批流程+状态流转
└── analyticsStore      # 招聘漏斗+渠道ROI+AI洞察
```

**统一页面状态模式**（每个Store遵循）：
```typescript
interface PageState<T> {
  status: 'idle' | 'loading' | 'success' | 'error' | 'empty'
  data: T | null
  error: { code: string; message: string } | null
}
```

**navigationStore** 关键设计：
- 每个列表页维护独立状态key（`positions`/`candidates`/`resumes`等）
- 进入详情页时保存列表状态（筛选条件/分页/scrollTop/selectedIds）
- 返回列表页时从store恢复
- 30分钟自动清除缓存

---

## 三、Koa BFF层设计

### 3.1 双BFF架构

PRD §8.5 定义了双BFF架构：

| BFF | 技术栈 | 端口 | 职责 |
|-----|--------|------|------|
| **Koa BFF** | Koa 2 | :8648 | 管理功能（hermes-web-ui原有）→ 代理到Hermes API Server (:8642) |
| **FastAPI** | FastAPI | :8000 | 招聘业务API（JWT + RBAC + Pydantic + 审计日志） |

### 3.2 BFF职责边界

| 请求类型 | 走向 | 理由 |
|---------|------|------|
| `/dashboard-api/*` | Vue → Koa BFF(:8648) → Hermes API(:8642) | 管理功能，hermes-web-ui原有代理逻辑 |
| `/hr-api/*` (CRUD) | Vue → **FastAPI(:8000)** | 招聘业务确定性端点（50-200ms） |
| `/hr-api/*` (AI能力) | Vue → **FastAPI(:8000)** | AI能力端点（Service层LLM推理） |
| `/v1/*` (IM对话/SSE) | Vue → **Hermes API(:8642)** 直连 | Agent对话，保持SSE直通 |
| `/api/v1/insights` | Vue → **FastAPI(:8000)** 直出 | Context Bar洞察，不走Koa |
| 静态资源 | Caddy → Vue SPA | Caddy反向代理 |

**关键结论**：招聘业务前端**不经过Koa BFF**，直接调用FastAPI。Koa BFF仅服务于管理后台。

### 3.3 SSE流式响应处理

| SSE场景 | 数据链路 | 前端处理方式 |
|---------|---------|------------|
| **Agent对话（全屏Chat）** | Vue → Hermes API(:8642) `/v1/chat` | 复用hermes-web-ui的SSE处理逻辑 |
| **Agent对话（Sidecar）** | Vue → Hermes API(:8642) `/v1/chat` | 同上，但在Sidecar组件内渲染 |
| **Context Bar洞察** | Vue → FastAPI(:8000) `GET /api/v1/insights` → SSE流式 | 新增 `useAiInsight()` composable消费 |
| **AI引导式创建** | Vue → FastAPI(:8000) `POST /api/v1/positions/ai-interpret` → SSE | `useAiGuidedCreation()` composable |
| **AI操作菜单** | Vue → FastAPI(:8000) → Toast通知 | 异步任务 + ARQ队列 |

**SSE前端统一封装**：
```typescript
// composables/hr/useSseStream.ts
export function useSseStream<T>(url: string, params: Record<string, string>) {
  const data = ref<T[]>([])
  const status = ref<'idle' | 'streaming' | 'done' | 'error'>('idle')

  // 使用 fetch + ReadableStream（非EventSource）
  // 支持POST请求 + Header传递JWT Token
  // P1-34修复：SSE认证改Header + 一次性5分钟Token降级方案

  return { data, status, abort }
}
```

### 3.4 认证Token在BFF层的传递

```
认证链路：

Vue前端
  ├─ JWT存储：localStorage / HttpOnly Cookie（推荐后者）
  ├─ 请求拦截器（axios instance）
  │   ├─ /hr-api/* → 注入 Header: `Authorization: Bearer <JWT>`
  │   ├─ /dashboard-api/* → Koa BFF自动注入（从Cookie/session提取）
  │   └─ /v1/* → Header注入（Sidecar/Chat场景）
  │
FastAPI(:8000) 认证中间件
  ├─ JWT验证 → 提取 tenant_id + user_id + role
  ├─ RBAC权限检查（Admin/HR/Interviewer/Headhunter）
  └─ 注入 request.state.user

Koa BFF(:8648) 认证
  ├─ hermes-web-ui原有Session认证
  └─ 与FastAPI JWT独立，不互通
```

**P1-34安全修复**：SSE认证改用Header传Token（非URL参数），并增加一次性5分钟Token降级方案，避免JWT暴露在URL中。

---

## 四、Naive UI组件复用

### 4.1 招聘业务页面→Naive UI组件映射

| 页面 | 核心Naive UI组件 | 复用方式 |
|------|-----------------|---------|
| 工作台 | NCard + NTimeline + NStatistic + NGrid | 直接使用 |
| 岗位管理 | NDataTable + NForm + NModal + NSelect | 直接使用 |
| 岗位360° | NTab + NCard + NStatistic + NDescriptions | 直接使用 |
| 简历库 | NDataTable + NUpload + NProgress | 直接使用 |
| 简历详情 | NCard + NDescriptions + NTimeline + NTag | 直接使用 |
| 候选人管理 | NDataTable + NCard + NTimeline | 直接使用 |
| 候选人360° | NTab + NCard + NRate + NTimeline | 直接使用 |
| 智能匹配 | NCard + NProgress + NStatistic + NSlider | 直接使用 |
| 面试管理 | NCalendar + NForm + NRate + NDataTable | 直接使用 |
| 面试详情 | NTab + NCard + NRate + NInput | 直接使用 |
| Offer管理 | NDataTable + NForm + NSteps + NModal | 直接使用 |
| Offer详情 | NCard + NSteps + NTimeline + NDescriptions | 直接使用 |
| 招聘分析 | NStatistic + NGrid + 图表(需引入ECharts/vue-charts) | Naive UI + 第三方 |
| AI任务中心 | NCard + NProgress + NTimeline + NEmpty | 直接使用 |
| 组织架构 | NTree + NCard + NStatistic | 直接使用 |

### 4.2 与hermes-web-ui现有组件的复用点

| hermes-web-ui组件 | 招聘业务复用场景 | 复用方式 |
|------------------|----------------|---------|
| ChatDrawer/SidePanel | Agent Sidecar的对话面板基础 | **扩展**：增加上下文注入+页面感知 |
| MarkdownRenderer | AI洞察/面试报告/分析报告渲染 | **直接复用** |
| CodeEditor | 岗位JD编辑器 | **直接复用** |
| FileUploader | 简历上传组件基础 | **扩展**：增加拖拽+批量+去重 |
| DataTable通用封装 | 所有列表页 | **直接复用**（hermes-web-ui可能有封装好的NDataTable wrapper） |
| SessionList | AI任务中心列表参考 | **参考设计** |
| Terminal/xterm.js | 无直接复用 | 不涉及 |
| i18n框架（vue-i18n） | 招聘业务多语言 | **直接复用框架**，新增招聘词条 |

### 4.3 需自研的招聘专属组件

| 组件 | 复杂度 | 依赖 |
|------|--------|------|
| **AiContextBar** | ⭐⭐⭐ | SSE流式渲染 + Redis缓存策略 + Tab切换刷新 |
| **AgentSidecar** | ⭐⭐⭐⭐ | Chat面板扩展 + 上下文注入 + 页面感知 + 300ms动画 |
| **CommandBar** | ⭐⭐⭐ | NModal + 全局快捷键 + 防抖搜索 + 键盘导航 |
| **DualModeCreator** | ⭐⭐⭐⭐ | AI模式(5步交互) + 手动模式 + 降级矩阵 + 字段映射 |
| **AiOperationMenu** | ⭐⭐ | NDropdown + 异步任务触发 + Toast |
| **InterviewCalendar** | ⭐⭐⭐ | NCalendar扩展 + 日程渲染 + 拖拽排期 |
| **MatchScoreRadar** | ⭐⭐ | ECharts雷达图封装 |
| **ResumeUploader** | ⭐⭐⭐ | NUpload扩展 + 拖拽 + 批量 + 进度 + 去重 |
| **PositionFunnel** | ⭐⭐ | 漏斗图（ECharts或自绘） |
| **OrgTree** | ⭐⭐ | NTree扩展 + 岗位挂载 + 人员分布 |

---

## 五、前端文档差距分析

### 5.1 docs/frontend/ 文档评估

| 文档 | 当前内容 | 与目标架构一致性 | 处置建议 |
|------|---------|:---:|---------|
| `routes-and-pages.md` | 15页路由 + AI交互架构 + 导航结构 + Caddy路由 + Token URL | ✅ **高度一致** | **保留**，仅微调：①Caddy路由中Vue SPA端口从:8648确认 ②Token URL路由补充Vue Router实现参考 |
| `components-interaction.md` | AI操作菜单 + 双模创建 + 页面状态 + 面试视图 + Token页面 | ✅ **高度一致** | **保留**，补充Vue组件实现示例（当前仅描述规格） |
| `state-management.md` | 页面状态规范 + 跨页面传递 + Pinia Store设计 + Context Bar缓存 | ✅ **高度一致** | **保留**，已基于Vue/Pinia编写，无需修改 |
| `onboarding-and-navigation.md` | 新用户引导 + CommandBar + 跳转路径 + Chat嵌入 | ✅ **高度一致** | **保留**，已基于Vue Router + Pinia编写 |

> **总结**：docs/frontend/ 的4个文档**已经基于Vue 3 + Pinia + Vue Router目标架构编写**，与PRD V3.6高度一致，全部保留。仅建议补充Vue组件代码示例。

### 5.2 docs/research/ 文档评估

| 文档 | 内容 | 与目标架构一致性 | 处置建议 |
|------|------|:---:|---------|
| `nextjs15-app-router.md` | Next.js 15 App Router技术调研（479行） | ❌ **完全过时** | **归档/删除**——目标架构基于Vue 3 + Vite，不再使用Next.js |
| `zod-server-actions-error-handling.md` | Zod + Server Actions + useActionState错误处理（340行） | ❌ **完全过时** | **归档/删除**——目标架构使用Naive UI Form Rules + FastAPI Pydantic校验，不再使用Server Actions |

> **建议**：将两个Next.js专项研究文档移至 `docs/research/_archived/nextjs/` 目录归档，或直接删除。需新增Vue 3专项研究文档替代。

### 5.3 需新增的前端文档

| 优先级 | 文档 | 内容 |
|--------|------|------|
| P0 | `docs/frontend/hermes-web-ui-fork-guide.md` | Fork操作指南、目录映射、定制隔离策略、上游同步流程 |
| P0 | `docs/frontend/vue-project-structure.md` | Vue 3项目结构、monorepo配置、Vite代理配置 |
| P0 | `docs/frontend/api-layer-design.md` | 招聘业务API层设计（axios instance、JWT注入、SSE封装、错误处理） |
| P1 | `docs/frontend/naive-ui-component-spec.md` | 招聘业务Naive UI组件使用规范、主题定制、设计Token |
| P1 | `docs/frontend/sse-streaming-guide.md` | SSE流式响应前端处理指南（Context Bar / Sidecar / AI创建） |
| P1 | `docs/frontend/testing-strategy.md` | Vue组件测试策略（Vitest + @vue/test-utils） |
| P2 | `docs/frontend/performance-budget.md` | 前端性能预算（首屏 < 2s、TTI < 3s、Bundle < 500KB gzipped） |

---

## 六、重建建议

### 6.1 重建路线图

```
Phase 0: 基础搭建（M0，1周）
├── Fork hermes-web-ui → 验证构建 + 管理页面正常
├── 新增 /hr 路由骨架（15个空页面）
├── 配置 Vite proxy（/hr-api → FastAPI:8000）
├── 搭建 Pinia stores 骨架
└── 验证 Naive UI + Tailwind 4 协同

Phase 1: 核心页面（M1，3周）
├── 工作台 Dashboard（系统首页）
├── 岗位管理（列表 + 360°视图 + AI引导创建）
├── 简历库（上传 + 解析 + 详情）
├── 候选人管理（列表 + 360°画像）
└── 智能匹配（看板 + 配置）

Phase 2: 决策流程（M2，3周）
├── 面试管理（列表/日历 + 详情 + 创建）
├── Offer管理（列表 + 详情 + 审批）
├── 招聘分析（漏斗 + ROI + AI洞察）
├── AI任务中心
└── 组织架构视图

Phase 3: AI原生交互（M3，2周）
├── AI Context Bar（洞察栏）
├── Agent Sidecar（右侧对话面板）
├── CommandBar（全局搜索 ⌘K）
├── 双模创建完整降级矩阵
└── 新用户引导三步流程

Phase 4: Token URL + 收尾（2周）
├── 面试反馈页（/feedback/:token）
├── 入职自助页（/onboarding/:token）
├── 共享招聘看板（/share/:token/dashboard）
├── E2E测试 + 性能优化
└── 文档完善
```

### 6.2 关键技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| hermes-web-ui Fork后上游更新难合并 | 中 | 定制代码隔离在 `views/hr/` + `components/hr/` + `stores/hr/`，不动上游核心文件 |
| Naive UI组件不满足招聘场景（如日历、树形） | 中 | 提前PoC验证NCalendar/NTree能力，不足部分用ECharts/vuedraggable补充 |
| SSE流式响应在Vue中的处理复杂度 | 高 | 统一封装 `useSseStream()` composable，支持POST + Header认证 |
| Agent Sidecar上下文注入的BFF中间件 | 高 | 需在Koa层新增context-injection中间件（或走FastAPI直出） |
| 双模创建的AI→手动字段映射 | 中 | 封装 `useFieldMapper()` composable，统一处理字段自动映射 |

### 6.3 立即行动项

1. **删除 `src/` 目录**：48个Next.js文件全部废弃
2. **归档 `docs/research/`**：两个Next.js专项研究文档移入 `_archived/`
3. **Fork hermes-web-ui**：按 §8.5 方案执行Fork，验证构建成功
4. **编写 `hermes-web-ui-fork-guide.md`**：记录Fork定制策略和上游同步流程
5. **搭建Vue 3项目骨架**：按2.3目录结构创建空文件，配置路由和Pinia

---

## 七、总结

| 维度 | 评估结论 |
|------|---------|
| **当前资产可复用率** | **0%**（全部Next.js/React代码，技术栈不兼容） |
| **文档可复用率** | docs/frontend/ **4/4 可保留**；docs/research/ **0/2 需归档** |
| **Fork策略清晰度** | **高**（PRD §8.5已有明确路由图+页面清单） |
| **前端架构成熟度** | **中高**（docs/frontend/已详细规划Vue 3方案，但缺少实现级代码） |
| **最大风险** | hermes-web-ui上游耦合 + SSE流式交互复杂度 |
| **预估前端工期** | M0(1w) + M1(3w) + M2(3w) + M3(2w) + M4(2w) = **~11周**（2名前端） |
