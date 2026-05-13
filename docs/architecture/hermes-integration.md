# Hermes集成方案

> **⚠️ 技术栈变更说明（2026-05-12）**：前端已从 Next.js 切换为 **Vue 3.5 + Vite 8 + Naive UI + Pinia 3**（基于 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) Fork）。本文件描述的页面结构、路由设计、交互逻辑均保持不变，但实现语言和组件库已变更。具体技术差异参见 `docs/architecture/tech-stack.md`。

> **PRD来源**: §8.3 Hermes源码复用清单 / §8.4 hermes-web-ui复用清单 / §8.5 前端架构

---

## 1. Hermes源码复用清单（§8.3，22项）

| # | Hermes能力 | 源码文件 | HR用途 |
|---|-----------|---------|--------|
| 1 | Agent推理循环 | `run_agent.py` | 所有招聘对话和决策推理 |
| 2 | Tool注册发现 | `tools/registry.py` | HR工具自动注册 |
| 3 | Tool分组 | `toolsets.py` | `"hr"` 工具集 |
| 4 | Tool分发 | `model_tools.py` | HR工具调用分发 |
| 5 | 微信接入 | `gateway/platforms/weixin.py` | HR微信对话交互 |
| 6 | 飞书接入 | `gateway/platforms/feishu.py` | HR飞书对话交互 |
| 7 | 钉钉接入 | `gateway/platforms/dingtalk.py` | HR钉钉对话交互 |
| 8 | 企业微信 | `gateway/platforms/wecom.py` | 企业微信通知 |
| 9 | 邮件收发 | `gateway/platforms/email.py` | 面试邀请/日报邮件 |
| 10 | API Server | `gateway/platforms/api_server.py` | IM对话接入Agent通道 |
| 11 | 定时任务 | `cron/jobs.py` + `cron/scheduler.py` | 日报/周报/人才库更新 |
| 12 | Webhook | `gateway/platforms/webhook.py` | Boss直聘/猎聘新简历推送 |
| 13 | 会话存储 | `hermes_state.py` SQLite | 对话历史FTS5搜索 |
| 14 | 子Agent批量 | `tools/delegate_tool.py` | 批量简历解析并行处理 |
| 15 | MCP协议 | `mcp_serve.py` + `tools/mcp_tool.py` | ATS等外部系统 |
| 16 | Skill系统 | `agent/skill_commands.py` | 招聘流程封装与加载 |
| 17 | 跨平台消息 | `tools/send_message_tool.py` | 面试通知多渠道推送 |
| 18 | 持久记忆 | `agent/memory_manager.py` | HR偏好/公司信息记忆 |
| 19 | 会话搜索 | `tools/session_search_tool.py` | 历史招聘记录检索 |
| 20 | Kanban | `tools/kanban_tools.py` | 招聘流水线状态管理 |
| 21 | Profile | `hermes_cli/profiles.py` | 多租户实例隔离 |
| 22 | SSE事件流 | `api_server.py` /v1/runs/events | Web前端实时进度 |

---

## 2. hermes-web-ui复用清单（§8.4）

### 基础管理页面（15个，直接复用）

| 页面 | 源码路径 | HireMind用途 |
|------|---------|-------------|
| Chat | src/pages/Chat.vue | Web端AI对话核心 |
| Cron | src/pages/Cron.vue | 招聘定时任务 |
| Models | src/pages/Models.vue | AI任务模型分配 |
| Env | src/pages/Env.vue | API Key管理 |
| Channels | src/pages/Channels.vue | 消息通道统一管理 |
| Sessions | src/pages/Sessions.vue | 历史记录查看 |
| Analytics | src/pages/Analytics.vue | Token成本监控 |
| Skills | src/pages/Skills.vue | 招聘Skill管理 |
| Profiles | src/pages/Profiles.vue | 招聘助手人格 |
| Config | src/pages/Config.vue | 参数配置 |
| Logs | src/pages/Logs.vue | 运维排障 |
| Plugins | src/pages/Plugins.vue | 扩展功能 |
| Files | src/pages/Files.vue | 简历文件浏览 |
| GroupChat | src/pages/GroupChat.vue | 多Agent协作 |
| Terminal | src/pages/Terminal.vue | 高级调试 |

### 共享组件复用

| 组件 | 用途 |
|------|------|
| Layout / Header / Sidebar | HireMind全局布局（扩展招聘导航） |
| ChatTerminal (xterm.js) | AI对话交互核心 |
| API层 (src/lib/api.ts) | Koa BFF通信基础 |
| Hooks (src/lib/hooks/) | Vue组合式函数 |
| i18n (8语言) | 国际化（含中文） |
| @nous-research/ui | 设计系统（npm直接引用） |

---

## 3. 前端架构 — Fork hermes-web-ui扩展（§8.5）

**决策依据**：hermes-web-ui提供15个通用管理页面（价值4-5个月开发量），Fork后扩展15个招聘业务页面（10个一级页面+5个详情子页面），总工期约2个月。

### 路由架构

```
┌─ Caddy 反向代理 ───────────────────────────────────────────────┐
│                                                                │
│  /hr/*          → Vue Router (招聘业务页面，自研，15页)         │
│                    ├── /hr/dashboard      🎯工作台（系统首页）  │
│                    ├── /hr/positions      岗位管理              │
│                    │   └── /hr/positions/:id    岗位360°视图    │
│                    ├── /hr/resumes        简历库                │
│                    │   └── /hr/resumes/:id      简历详情        │
│                    ├── /hr/candidates     候选人管理            │
│                    │   └── /hr/candidates/:id   候选人360°画像  │
│                    ├── /hr/matching        智能匹配             │
│                    ├── /hr/interviews     面试管理              │
│                    │   └── /hr/interviews/:id   面试详情页      │
│                    ├── /hr/offers         Offer管理             │
│                    │   └── /hr/offers/:id     Offer详情页      │
│                    ├── /hr/analytics      招聘分析              │
│                    ├── /hr/tasks          AI任务中心            │
│                    └── /hr/org-chart       组织架构             │
│                                                                │
│  /chat, /jobs,   → Vue Router (管理页面，复用hermes-web-ui)    │
│  /models, /env,                                                 │
│  /channels, ...                                                 │
│                                                                │
│  /hr-api/*      → FastAPI (:8000)      ← 招聘业务API           │
│  /dashboard-api/* → Koa BFF (:8648)    ← 管理功能API           │
│  /v1/*          → Hermes API Server (:8642)  ← IM对话/SSE      │
└────────────────────────────────────────────────────────────────┘
```

### 公开路由（Token URL，无需登录）

| 路由路径 | 页面 | 目标用户 |
|----------|------|----------|
| `/feedback/:token` | 面试反馈表单 | 面试官（外部） |
| `/onboarding/:token` | 入职自助页 | 候选人（外部） |
| `/share/:token/dashboard` | 共享招聘看板 | 用人经理（外部） |
| `/candidate/:token/profile` | 候选人信息更新 | 候选人（P2） |
| `/candidate/:token/offer` | 候选人Offer回应 | 候选人（P2） |

安全机制：Token验证（有效期7天/一次性）+ rate limiting（10次/分钟）+ CSP头部

### 技术栈

- 前端：Vue 3 + Naive UI + Pinia + TypeScript + Tailwind 4
- BFF：Koa 2（管理功能）+ FastAPI（招聘业务）
- 构建工具：Vite 7
- 设计系统：@nous-research/ui（npm直接引用，零修改）
- 国际化：vue-i18n（8语言，含中文）
- 终端：xterm.js + WebGL渲染
- 实时通信：SSE（AI流式）+ Socket.IO（群聊）

### BFF响应格式统一

```typescript
interface BFFResponse<T> {
  success: boolean;
  data: T | null;
  error?: { code: number; message: string; detail?: string };
  meta?: { total?: number; page?: number; page_size?: number };
  request_id: string;
}
```

前端所有API调用仅处理 `BFFResponse<T>` 格式。
