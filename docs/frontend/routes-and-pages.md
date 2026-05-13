# 路由与页面清单

> **⚠️ 技术栈变更说明（2026-05-12）**：前端已从 Next.js 切换为 **Vue 3.5 + Vite 8 + Naive UI + Pinia 3**（基于 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) Fork）。本文件描述的页面结构、路由设计、交互逻辑均保持不变，但实现语言和组件库已变更。具体技术差异参见 `docs/architecture/tech-stack.md`。

> **PRD来源**: §10.1 页面清单 / §10.1b AI交互 / §10.2 导航融合 / §8.5 路由图

---

## 1. 15个招聘业务页面（§10.1，自研）

10个一级页面 + 5个详情子页面，含工作台+AI任务中心+组织架构视图。

| 页面 | 路由 | 核心组件(Naive UI) | 关键交互 |
|------|------|-------------------|---------|
| **🎯工作台** | `/hr/dashboard` | NCard + NTimeline + NStatistic | 待办清单+今日日程+快捷指标+AI洞察推送（系统首页） |
| **岗位管理** | `/hr/positions` | NDataTable + NForm + NModal | 列表+状态流转+🤖AI操作菜单。三模创建：🤖AI引导/📝手动表单/📋历史复制 |
| **岗位360°视图** | `/hr/positions/:id` | NTab + NCard + NStatistic | 投递候选人Tab+推荐候选人Tab+生命周期Tab+AI Context Bar |
| **简历库** | `/hr/resumes` | NDataTable + NUpload + NProgress | 拖拽上传+批量解析进度+去重标记 |
| **简历详情** | `/hr/resumes/:id` | NCard + NDescriptions + NTimeline | 结构化字段+溯源链接+解析置信度+AI操作菜单 |
| **候选人管理** | `/hr/candidates` | NDataTable + NCard + NTimeline | 列表+画像卡片+经验时间线+🤖AI操作菜单 |
| **候选人360°画像** | `/hr/candidates/:id` | NTab + NCard + NTimeline + NRate | 基本信息+岗位匹配+面试记录+简历文件+沟通记录 |
| **智能匹配** | `/hr/matching` | NCard + NProgress + NStatistic | 全局匹配看板+批量匹配+匹配配置+🤖AI操作菜单 |
| **面试管理** | `/hr/interviews` | NCalendar + NForm + NRate | 日历/列表切换+双模创建面试+🤖AI操作菜单 |
| **面试详情** | `/hr/interviews/:id` | NTab + NCard + NRate | 考察清单+面试实录+分析报告(3Tab)+「发起Offer」入口 |
| **Offer管理** | `/hr/offers` | NDataTable + NForm + NSteps | 列表+三入口创建(AI预填方案)+🤖AI操作菜单 |
| **Offer详情** | `/hr/offers/:id` | NCard + NSteps + NTimeline | Offer信息+审批流程+操作历史 |
| **招聘分析** | `/hr/analytics` | NStatistic + 图表组件 | 漏斗图+渠道ROI+AI洞察面板+🤖AI操作菜单 |
| **🤖AI任务中心** | `/hr/tasks` | NCard + NProgress + NTimeline | 运行中/已完成/队列任务可视化+进度 |
| **组织架构** | `/hr/org-chart` | NTree + NCard | 部门树+岗位挂载+人员分布 |

### 工作台待办跳转映射

| 待办类型 | 跳转目标 |
|---------|---------|
| N份新简历待筛选 | 岗位360°视图 Tab2投递候选人 |
| M场面试待确认 | 面试管理页(日历视图) |
| K个Offer待审批 | Offer详情页 Tab3审批链 |
| 今日面试 | 面试详情页 Tab1考察清单 |
| 岗位超期预警 | 岗位详情页 Tab5生命周期 |

---

## 2. AI原生交互架构（§10.1b）

三种模式并存，共享同一Agent Session：

| 模式 | 交互方式 | 适用场景 | 位置 |
|------|---------|---------|------|
| **A. AI Context Bar** | 内嵌洞察栏（随Tab刷新） | 被动获取AI建议 | 详情页顶部 |
| **B. Agent Sidecar** | 右侧对话面板（上下文感知） | 主动追问+多步任务 | 详情页右侧抽屉 |
| **C. 全屏Chat** | hermes-web-ui Chat页面 | 自由对话+无上下文 | /chat 路由 |

### 交互优先级矩阵

| 触发条件 | 优先模式 | 升级条件 | 移动端 |
|---------|---------|---------|--------|
| 页面加载 | Context Bar（被动） | 点击"详细分析"→ Sidecar | 底部Sheet |
| 用户主动触发 | Agent Sidecar | 关闭→退回Context Bar | 可拖拽全屏Sheet |
| 无页面上下文 | 全屏Chat | 提及实体→建议跳转详情 | 全屏页面 |

### Context Bar刷新规则

| 当前Tab | AI洞察内容 |
|---------|-----------|
| 画像与推理 | 匹配分析摘要+能力亮点/风险+薪资对标 |
| 岗位匹配 | 各岗位匹配差异+推荐排序+缺失技能 |
| 面试记录 | 面试表现趋势+关键观察+下一步建议 |
| 简历 | 可信度摘要+信息缺口+建议验证项 |
| 沟通 | 回复时效分析+候选人意向评估+跟进建议 |

**支撑端点**: `GET /api/v1/insights?entity_type=&entity_id=&tab=` → FastAPI直出（不走Koa BFF）

### Agent Sidecar规格

| 属性 | 规格 |
|------|------|
| 滑入动画 | 300ms ease-out |
| 固定宽度 | 480px |
| 关闭焦点返回 | 返回列表页第一个可聚焦元素 |
| 响应式断点 | <768px: 底部Sheet / ≥768px: Sidecar |
| 遮罩层 | rgba(0,0,0,0.3)，200ms淡入 |

---

## 3. 导航结构（§10.2）

### Sidebar 3级扁平导航

```
├── 📋 招聘管理
│   ├── 🎯工作台          ← 系统首页
│   ├── 岗位管理
│   ├── 简历库
│   ├── 候选人管理
│   ├── 智能匹配
│   ├── 面试管理
│   ├── Offer管理
│   ├── 招聘分析
│   └── 🤖AI任务中心      ← L1独立入口
│
├── 💬 AI助手            ← hermes-web-ui原有
│   ├── 对话 (Chat)
│   └── 群聊 (GroupChat)
│
├── ⚙️ 系统管理          ← hermes-web-ui原有
│   ├── 定时任务 (Cron)
│   ├── 模型配置 (Models)
│   ├── 密钥管理 (Env)
│   ├── 频道配置 (Channels)
│   ├── 技能管理 (Skills)
│   ├── Agent人格 (Profiles)
│   ├── 系统配置 (Config)
│   ├── 插件管理 (Plugins)
│   ├── 文件管理 (Files)
│   ├── 日志 (Logs)
│   └── 终端 (Terminal)
│
└── 📊 使用分析
    └── Token分析 (Analytics)
```

**设计原则**：核心业务7个入口扁平化（L1直达），辅助功能折叠到"更多"。禁止L3嵌套L4子页面——所有详情页通过URL参数`?tab=`切换内部视图。

### Caddy路由映射

| 路径 | 目标 | 说明 |
|------|------|------|
| `/hr/*` | Vue SPA :8648 | 招聘业务页面 |
| `/chat, /models, /env, ...` | Vue SPA :8648 | 管理页面（复用） |
| `/hr-api/*` | FastAPI :8000 | 招聘业务API |
| `/dashboard-api/*` | Koa BFF :8648 | 管理功能API |
| `/v1/*` | Hermes API :8642 | IM对话/SSE |

### 公开路由（Token URL）

| 路由 | 页面 | 用户 |
|------|------|------|
| `/feedback/:token` | 面试反馈表单 | 面试官（外部） |
| `/onboarding/:token` | 入职自助页 | 候选人（外部） |
| `/share/:token/dashboard` | 共享招聘看板 | 用人经理（外部） |
| `/candidate/:token/profile` | 候选人信息更新 | P2 |
| `/candidate/:token/offer` | 候选人Offer回应 | P2 |
