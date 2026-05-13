# 系统架构总览

> 源自 PRD V3.6 §8 + 用户提供的架构图 + Fork仓库核实  
> 更新日期：2026-05-12（基于 hireMind Fork 实际结构修订）

---

## 1. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户交互层                                   │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ 微信 ✅   │ │ 飞书 ✅   │ │ 钉钉 ✅   │ │ 邮件 ✅              │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┬───────────┘  │
│       └──────┬─────┘           │                    │              │
│              │                 │                    │              │
│  ┌───────────▼──────┐  ┌──────▼────────────────────▼──────────┐  │
│  │ Hermes Agent      │  │  Web前端 (hireMind Fork)              │  │
│  │ (:8642)           │  │  Vue 3 + Naive UI + Koa BFF (:8648)  │  │
│  │                   │  │                                       │  │
│  │ • Agent Loop      │  │  ┌─ 招聘业务(~10页自研)──────────┐   │  │
│  │ • Webhook消费     │  │  │ /hr/dashboard 工作台            │   │  │
│  │ • Cron定时        │  │  │ /hr/positions  岗位管理         │   │  │
│  │                   │  │  │ /hr/resumes    简历库           │   │  │
│  │ 操作路由：         │  │  │ /hr/candidates 候选人          │   │  │
│  │ ┌───────────────┐│  │  │ /hr/matching   智能匹配         │   │  │
│  │ │ CRUD → Tools  ││  │  │ /hr/interviews 面试管理         │   │  │
│  │ │   → FastAPI   ││  │  │ /hr/offers     Offer管理        │   │  │
│  │ ├───────────────┤│  │  │ /hr/analytics  招聘分析         │   │  │
│  │ │ AI推理        ││  │  │ /hr/tasks      AI任务中心       │   │  │
│  │ │ → Service层   ││  │  │ /hr/org-chart  组织架构         │   │  │
│  │ └───────┬───────┘│  │  └──────────┬───────────────────┘   │  │
│  └─────────┼────────┘  │             │                        │  │
│            │           │  ┌─ 管理后台(16页复用hermes-web-ui)┐ │  │
│            │           │  │ /hermes/chat      Chat          │ │  │
│            │           │  │ /hermes/jobs      Cron          │ │  │
│            │           │  │ /hermes/models    Models        │ │  │
│            │           │  │ /hermes/settings  Settings      │ │  │
│            │           │  │ /hermes/channels  Channels      │ │  │
│            │           │  │ /hermes/history   Sessions      │ │  │
│            │           │  │ /hermes/skills    Skills        │ │  │
│            │           │  │ /hermes/profiles  Profiles      │ │  │
│            │           │  │ /hermes/usage     Analytics     │ │  │
│            │           │  │ /hermes/logs      Logs          │ │  │
│            │           │  │ /hermes/gateways  Gateways      │ │  │
│            │           │  │ /hermes/terminal  Terminal      │ │  │
│            │           │  │ /hermes/group-chat GroupChat    │ │  │
│            │           │  │ /hermes/files     Files         │ │  │
│            │           │  │ /hermes/memory    Memory        │ │  │
│            │           │  │ /hermes/agents    Agents        │ │  │
│            │           │  └──────────┬───────────────────┘   │  │
│            │           │             │                        │  │
│            │           └─────────────┼────────────────────────┘  │
│            │                         │                            │
│  ┌─────────▼─────────────────────────▼──────────────────────┐    │
│  │          FastAPI API Gateway (:8000)                       │    │
│  │          Web前端唯一后端入口                                 │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │          Service层（唯一业务逻辑归属）                     │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │          HR招聘工具层（Agent专用扩展）                      │    │
│  │  Tools (12个) / MCP Servers (2个) / Skills (8个)          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │          数据存储层                                        │    │
│  │  PostgreSQL / pgvector / MinIO / Redis                   │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 仓库结构

### 2.1 hireMind Fork（前端 + BFF）

**来源**: Fork 自 [EKKOLearnAI/hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui)  
**GitHub**: [HuangYet-Sam/hireMind](https://github.com/HuangYet-Sam/hireMind) (`base` 分支)

```
hireMind/                           ← hermes-web-ui Fork
├── packages/
│   ├── client/                     ← Vue 3 前端
│   │   ├── src/
│   │   │   ├── views/
│   │   │   │   ├── LoginView.vue       登录页
│   │   │   │   ├── hermes/             ← 管理后台16页(复用)
│   │   │   │   │   ├── ChatView.vue
│   │   │   │   │   ├── JobsView.vue        (Cron定时任务)
│   │   │   │   │   ├── ModelsView.vue
│   │   │   │   │   ├── ProfilesView.vue
│   │   │   │   │   ├── SettingsView.vue
│   │   │   │   │   ├── GatewaysView.vue
│   │   │   │   │   ├── ChannelsView.vue
│   │   │   │   │   ├── HistoryView.vue     (Sessions)
│   │   │   │   │   ├── SkillsView.vue
│   │   │   │   │   ├── UsageView.vue       (Analytics)
│   │   │   │   │   ├── LogsView.vue
│   │   │   │   │   ├── TerminalView.vue
│   │   │   │   │   ├── GroupChatView.vue
│   │   │   │   │   ├── FilesView.vue
│   │   │   │   │   ├── MemoryView.vue
│   │   │   │   │   └── AgentsView.vue
│   │   │   │   └── hr/                 ← 招聘业务页面(待创建)
│   │   │   │       ├── DashboardView.vue
│   │   │   │       ├── PositionsView.vue
│   │   │   │       ├── ResumesView.vue
│   │   │   │       ├── CandidatesView.vue
│   │   │   │       ├── MatchingView.vue
│   │   │   │       ├── InterviewsView.vue
│   │   │   │       ├── OffersView.vue
│   │   │   │       ├── AnalyticsView.vue
│   │   │   │       ├── TasksView.vue
│   │   │   │       └── OrgChartView.vue
│   │   │   ├── components/
│   │   │   │   ├── hermes/             ← 管理后台组件(复用)
│   │   │   │   │   ├── chat/
│   │   │   │   │   ├── jobs/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── settings/
│   │   │   │   │   ├── skills/
│   │   │   │   │   ├── profiles/
│   │   │   │   │   ├── usage/
│   │   │   │   │   ├── files/
│   │   │   │   │   ├── group-chat/
│   │   │   │   │   ├── agents/
│   │   │   │   │   └── kanban/
│   │   │   │   ├── layout/            ← 全局布局(复用)
│   │   │   │   └── hr/                ← 招聘业务组件(待创建)
│   │   │   ├── stores/
│   │   │   │   ├── hermes/            ← Pinia stores(复用, 12个)
│   │   │   │   └── hr/               ← 招聘stores(待创建)
│   │   │   ├── api/
│   │   │   │   ├── hermes/           ← API层(复用, 20个)
│   │   │   │   ├── hr/              ← 招聘API(待创建)
│   │   │   │   ├── client.ts        ← Axios实例(复用)
│   │   │   │   └── auth.ts          ← 认证(复用)
│   │   │   ├── router/
│   │   │   │   └── index.ts         ← 路由(需扩展/hr/*)
│   │   │   ├── composables/          ← Vue组合式函数(复用, 9个)
│   │   │   ├── i18n/                 ← 国际化(复用)
│   │   │   └── styles/               ← 样式(复用)
│   │   └── index.html
│   └── server/                       ← Koa 2 BFF
│       └── src/
│           ├── index.ts              ← Koa入口
│           ├── config.ts             ← 配置
│           ├── routes/
│           │   ├── hermes/           ← 管理后台路由(复用)
│           │   └── hr/              ← 招聘BFF路由(待创建)
│           ├── services/
│           │   ├── hermes/           ← 管理后台服务(复用)
│           │   └── hr/              ← 招聘BFF服务(待创建)
│           ├── controllers/
│           │   ├── hermes/           ← 控制器(复用)
│ │       └── hr/              ← 招聘控制器(待创建)
│           └── db/
│               └── hermes/           ← SQLite存储(复用)
├── packages/api/                ← FastAPI 招聘业务API
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml                ← Docker编排
├── Dockerfile                        ← 多阶段构建
├── CLAUDE.md                         ← AI开发指南
├── package.json                      ← v0.5.9, hermes-web-ui
└── vite.config.ts                    ← Vite配置
```

### 2.2 FastAPI API（packages/api/）

```
packages/api/                        ← 招聘业务API（Python独立包）
├── app/
│   ├── main.py                      ← FastAPI入口
│   ├── config.py                    ← 配置
│   ├── dependencies.py              ← 依赖注入
│   ├── middleware/                   ← 中间件
│   │   ├── auth.py                  ← JWT认证
│   │   ├── rbac.py                  ← RBAC权限
│   │   ├── tenant.py                ← 多租户注入
│   │   ├── audit.py                 ← 审计日志
│   │   └── rate_limit.py            ← 限流
│   ├── routers/                     ← API路由
│   │   ├── positions.py
│   │   ├── candidates.py
│   │   ├── resumes.py
│   │   ├── matching.py
│   │   ├── interviews.py
│   │   ├── offers.py
│   │   ├── analytics.py
│   │   └── departments.py
│   ├── services/                    ← 业务逻辑
│   │   ├── position_service.py
│   │   ├── candidate_service.py
│   │   ├── resume_service.py
│   │   ├── matching_service.py
│   │   ├── interview_service.py
│   │   ├── offer_service.py
│   │   └── analytics_service.py
│   ├── models/                      ← SQLAlchemy模型
│   ├── schemas/                     ← Pydantic schemas
│   └── decorators/
│       └── ai_capability.py         ← @AiCapability装饰器
├── alembic/                         ← DB迁移
├── tests/
├── requirements.txt
└── Dockerfile
```

### 2.3 Hermes Agent 扩展（hermes-agent tools/skills目录）

```
hermes-agent/
├── tools/
│   ├── hr_resume.py                 ← 简历操作
│   ├── hr_profile.py                ← 画像操作
│   ├── hr_matching.py               ← 匹配操作
│   ├── hr_position.py               ← 岗位操作
│   ├── hr_interview.py              ← 面试操作
│   ├── hr_talent_pool.py            ← 人才库
│   ├── hr_vector.py                 ← 向量操作
│   ├── hr_storage.py                ← 文件操作
│   ├── hr_auth.py                   ← 认证操作
│   ├── hr_analytics.py              ← 统计分析
│   ├── hr_db.py                     ← 数据查询(白名单)
│   └── hr_offer.py                  ← Offer操作
└── skills/
    ├── hr-daily-briefing/
    ├── hr-candidate-screen/
    ├── hr-interview-prep/
    ├── hr-interview-debrief/
    ├── hr-offer-strategy/
    ├── hr-funnel-diagnosis/
    ├── hr-talent-pool-scan/
    └── hr-weekly-review/
```

---

## 3. 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Caddy | 80/443 | 反向代理+自动HTTPS |
| FastAPI | 8000 | 业务API Gateway |
| Koa BFF | 8648 | 前端+BFF（hermes-web-ui默认端口） |
| Hermes Agent | 8642 | AI引擎 API Server |
| PostgreSQL | 5432 | 主数据库(含pgvector) |
| Redis | 6379 | 缓存+队列 |
| MinIO | 9000/9001 | 文件存储+Console |
| Prometheus | 9090 | 指标采集 |
| Grafana | 3000 | 监控Dashboard |
| Loki | 3100 | 日志聚合 |

---

## 4. 数据流

### 4.1 Web前端路径

```
用户浏览器 → Vue组件 → api/hr/*.ts → FastAPI(:8000) → Service层 → DB
                                                    → LLM(AI推理)
```

招聘业务**直接调FastAPI**，不经Koa BFF转发。

### 4.2 管理后台路径

```
用户浏览器 → Vue组件 → api/hermes/*.ts → Koa BFF(:8648) → Hermes Agent(:8642)
```

管理后台(16页)复用原hermes-web-ui的Koa BFF → Hermes Agent链路。

### 4.3 IM路径

```
HR微信/飞书 → Hermes Gateway → Agent Loop → hr_* Tools → Service层 → DB
```

### 4.4 主动式AI路径

```
Cron/Webhook → Hermes Agent → hr_* Tools → Service层 → send_message → 微信/Web
```
