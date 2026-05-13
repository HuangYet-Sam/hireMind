# 引导与导航设计

> **⚠️ 技术栈变更说明（2026-05-12）**：前端已从 Next.js 切换为 **Vue 3.5 + Vite 8 + Naive UI + Pinia 3**（基于 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) Fork）。本文件描述的页面结构、路由设计、交互逻辑均保持不变，但实现语言和组件库已变更。具体技术差异参见 `docs/architecture/tech-stack.md`。

> **PRD来源**: §10.4 新用户引导 / §10.7 CommandBar / §10.8 跳转 / §10.8a CTA路径 / §10.3 Chat面板

---

## 1. 新用户引导设计（§10.4）

### 首次登录三步引导

新HR用户首次登录自动触发AI引导流程（全屏模态+Step指示器）：

**Step 1：AI引导创建第一个岗位**
- 🤖「你好！我是HireMind招聘助手。我们先创建第一个岗位吧？」
- 自动打开岗位创建页面的🤖AI模式
- 完成标记：成功创建第一个岗位

**Step 2：引导上传第一份简历**
- 🤖「岗位创建完成！🎉 试试上传一份简历」
- 跳转简历库页面，上传区域高亮
- 完成标记：成功上传并解析一份简历

**Step 3：引导查看智能匹配**
- 🤖「简历已解析！✨ 点击「智能匹配」查看推荐候选人」
- 跳转匹配结果页
- 完成标记：查看至少一条匹配结果

### 工作台AI洞察持续引导

三步引导完成后，Dashboard的AI洞察推送持续引导：

| 用户阶段 | 推送内容 |
|---------|---------|
| 引导后第1天 | 「你有N份简历待处理，试试AI批量筛选？」 |
| 引导后第3天 | 「面试安排助手已就绪，点击体验AI智能排期」 |
| 引导后第7天 | 「人才画像功能已可用，查看候选人深度分析」 |
| 持续 | 基于行为推荐未使用的AI功能 |

### 引导状态持久化

- 存储在 `user_preferences.onboarding_status`（JSON字段）
- 状态模型：`not_started → step1_completed → step2_completed → step3_completed → completed`
- 用户可随时跳过（Skip），标记为`skipped`

### Skip后功能卡片推送（P2-19修复）

跳过引导后，Dashboard首页以功能卡片格式推送核心功能引导：
- 🤖 **AI匹配** — "一键为岗位筛选最佳候选人" → [立即试用]
- 📋 **简历解析** — "上传简历自动提取关键信息" → [上传简历]
- 💬 **AI助手** — "随时对话，一句话完成招聘操作" → [开始对话]

卡片推送策略：Skip后首次登录展示3张核心卡片，后续基于行为动态推荐。

---

## 2. CommandBar全局搜索（§10.7）

| 维度 | 规格 |
|------|------|
| **触发** | `Cmd+K`(Mac) / `Ctrl+K`(Win)，或点击顶部搜索栏 |
| **搜索范围** | 全局（岗位/候选人/简历/面试/Offer） |
| **搜索能力** | 结构化字段模糊匹配（名称/技能/公司/岗位标题），**不支持**自然语言搜索（Agent独有） |
| **结果排序** | 相关度(60%) > 最近访问时间(20%) > 实体类型权重(20%)，类型权重基于30天点击频率自动调整 |
| **结果展示** | 最多10条，按实体类型分组，每组最多3条 |
| **键盘导航** | ↑↓选择 + Enter跳转 + Esc关闭 |
| **搜索历史** | 最近5条记录，展示在搜索框下方 |
| **无结果** | "未找到" + 「🤖让AI帮你找」→ 打开Sidecar将关键词作为AI输入 |
| **性能** | Debounce 300ms + 后端搜索<500ms |

---

## 3. Dashboard待办跳转参数（§10.8）

| 待办类型 | 跳转URL | 参数说明 |
|---------|---------|---------|
| 简历待筛选（多条） | `/hr/positions/:id?tab=applied&filter=unmatched` | 按岗位分组 |
| 简历待筛选（汇总） | `/hr/resumes?filter=unmatched` | "查看全部" |
| 面试待反馈 | `/hr/interviews/:id?tab=briefing` | 跳考察清单 |
| Offer待跟进 | `/hr/offers/:id?tab=approval` | 跳审批链 |
| 岗位超期预警 | `/hr/positions/:id?tab=lifecycle` | 按岗位逐条 |
| 今日面试 | `/hr/interviews/:id` | 默认Tab1 |

多岗位分组规则：按紧急度排序（超期>即将到期>正常），每条显示所属岗位名称。

---

## 4. 核心CTA跳转路径（§10.8a，15条）

| # | CTA描述 | From | To | 返回策略 |
|---|---------|------|----|---------|
| 1 | 工作台待办→简历筛选 | `/hr/dashboard` | `/hr/positions/:id?tab=applied&filter=unmatched` | 面包屑：工作台>岗位详情 |
| 2 | 工作台日程→面试详情 | `/hr/dashboard` | `/hr/interviews/:id?tab=briefing` | 面包屑：工作台>面试详情 |
| 3 | 岗位列表→岗位360° | `/hr/positions` | `/hr/positions/:id` | 保留筛选状态 |
| 4 | 岗位360°→创建面试 | `/hr/positions/:id` | `/hr/interviews?create=true&candidate_id=X&position_id=:id` | 面包屑 |
| 5 | 候选人360°→创建面试 | `/hr/candidates/:id` | `/hr/interviews?create=true&candidate_id=:id&position_id=X` | 面包屑 |
| 6 | 面试详情→发起Offer | `/hr/interviews/:id` | `/hr/offers?create=true&candidate_id=X&position_id=Y` | 面包屑 |
| 7 | Offer详情→候选人360° | `/hr/offers/:id` | `/hr/candidates/:candidate_id` | 面包屑 |
| 8 | Offer详情→面试详情 | `/hr/offers/:id` | `/hr/interviews/:interview_id?tab=report` | 返回Offer |
| 9 | 匹配结果→候选人360° | `/hr/matching` | `/hr/candidates/:id?tab=matches` | 面包屑 |
| 10 | 匹配结果→岗位360° | `/hr/matching` | `/hr/positions/:id?tab=applied` | 返回匹配 |
| 11 | 简历列表→候选人360° | `/hr/resumes` | `/hr/candidates/:candidate_id?tab=resume` | 保留筛选 |
| 12 | 简历详情→创建岗位 | `/hr/resumes/:id` | `/hr/positions?create=true&skill_tags=Java,Python` | 返回简历详情 |
| 13 | 分析页→岗位详情 | `/hr/analytics` | `/hr/positions/:id?tab=lifecycle` | 返回分析页 |
| 14 | 组织架构→岗位360° | `/hr/org-chart` | `/hr/positions/:id` | 返回组织架构 |
| 15 | 全局搜索→任意详情页 | 任意 | `/hr/{type}/:id` | `history.back()` |

### 通用跳转规则

1. 所有跳转通过 `<router-link>` + `query params`，不硬编码
2. 来源页状态通过 Pinia `navigationStore` 保存，返回时恢复
3. 面包屑格式：`L1列表页 > L2详情页`（最多2级）
4. 创建类跳转（`?create=true`）打开Modal而非新页面
5. `history.back()` 作为最后兜底

---

## 5. Chat面板嵌入（§10.3）

招聘业务页面支持右侧抽屉打开AI对话面板（ChatDrawer），自动注入当前页面上下文。

```
候选人在看张三的画像卡片
  → 点击右下角"AI助手"按钮
  → 抽屉打开，自动注入：
    "当前正在查看候选人 张三 (ID: xxx)，岗位匹配：高级Java工程师 (匹配度78%)"
  → 用户可直接问："为什么匹配度只有78%？"
  → Agent基于上下文回答
```

### 隐私隔离（P2-18安全修复）

- **独立Session**：每个HR用户独立Chat Session，绑定 `tenant_id + user_id`，完全隔离
- **上下文脱敏过滤器**：自动注入的页面上下文经RBAC校验，仅注入当前HR有权限查看的数据
- **跨HR数据屏蔽**：即使页面包含多个HR数据，上下文仅保留当前HR负责的候选人子集
- 实现方式：`build_chat_context(tenant_id, user_id, page_type, entity_id)` → RBAC校验 → 仅返回授权数据
