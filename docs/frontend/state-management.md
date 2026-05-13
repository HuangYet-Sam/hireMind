# 状态管理

> **⚠️ 技术栈变更说明（2026-05-12）**：前端已从 Next.js 切换为 **Vue 3.5 + Vite 8 + Naive UI + Pinia 3**（基于 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) Fork）。本文件描述的页面结构、路由设计、交互逻辑均保持不变，但实现语言和组件库已变更。具体技术差异参见 `docs/architecture/tech-stack.md`。

> **PRD来源**: §10.5 页面状态设计规范 / §10.8b 跨页面数据传递规范

---

## 1. 页面状态设计规范（§10.5）

### 状态类型

| 状态类型 | 触发条件 | UI规范 | 交互 |
|---------|---------|--------|------|
| **空状态** | 页面首次加载无数据 | 插画+引导文案+CTA按钮（如"创建第一个岗位"） | CTA触发创建流程 |
| **加载态** | API请求中 | 骨架屏（Skeleton），非Spinner | 不阻塞导航 |
| **错误态** | API失败/超时 | 错误图标+描述+重试按钮 | 重试按钮重新请求 |
| **部分数据** | 有数据但不完整 | 已有数据正常展示，缺省字段显示"待补充"灰色占位 | 点击"待补充"可编辑 |
| **权限不足** | 无访问权限 | 锁定图标+"您无权访问"+申请权限按钮 | 触发权限申请流程 |
| **离线态** | 网络断开 | 顶部黄色Banner"网络已断开，数据可能不是最新" | 自动重连后消失 |

### 实现约定

- 所有状态由前端统一的状态机管理（Pinia store）
- API层返回 `{status, data, error}` 标准结构
- 骨架屏占位与实际内容布局一致，避免闪烁
- 重试按钮调用相同API，最多自动重试3次后提示手动操作

---

## 2. 跨页面数据传递规范（§10.8b）

### 三种传递方式

| 传递方式 | 适用场景 | 示例 |
|----------|----------|------|
| **URL参数** | 仅传递实体ID和视图控制 | `/hr/candidates/:id?tab=ai-insights`、`/hr/offers?create=true&candidate_id=123` |
| **API获取** | 详情页业务数据一律通过GET接口获取 | 进入候选人360°→ `GET /api/v1/candidates/:id` 获取全量数据 |
| **Pinia navigationStore** | 列表页筛选条件/分页位置/滚动位置 | 岗位列表筛选后进入详情→返回恢复筛选状态 |

### 禁止规则

- ❌ **禁止通过URL传递业务数据**（如 `match_score=92`），一律通过API实时查询
- ❌ **禁止通过URL传递敏感信息**（如薪资、身份证号）
- 列表页批量选中项通过 `navigationStore.selectedIds` 保存，返回时恢复勾选，已删除记录自动清除

### 多匹配岗位选择

候选人360°→创建面试时，若候选人匹配多个岗位，弹出岗位选择Modal（列表展示岗位名+匹配分数，单选确认）。

---

## 3. Pinia Store设计要点

### navigationStore

```typescript
interface NavigationState {
  // 列表页状态保存
  listStates: Record<string, {
    filters: Record<string, any>;
    page: number;
    pageSize: number;
    scrollTop: number;
    selectedIds: string[];
  }>;
}
```

- 每个列表页维护独立状态key（如 `positions`, `candidates`, `resumes`）
- 进入详情页时保存当前列表状态
- 返回列表页时从store恢复状态
- 超过30分钟的缓存自动清除

### 页面状态Store模式

```typescript
// 统一的页面状态管理模式
interface PageState<T> {
  status: 'idle' | 'loading' | 'success' | 'error' | 'empty';
  data: T | null;
  error: { code: number; message: string } | null;
}
```

- 每个页面/Tab维护独立的请求状态
- 加载中显示骨架屏
- 错误状态提供重试入口
- 空状态展示引导CTA

---

## 4. Context Bar缓存策略（P1-03/P1-18修复）

### 缓存流程

```
Tab切换 → 检查Redis缓存
  ├─ 命中 → 直接渲染（< 100ms）
  └─ 未命中 → 发起FastAPI请求
       ├─ 去重检查（pending请求共享）
       ├─ FastAPI → Hermes API Server → Agent生成洞察
       ├─ 写入Redis (TTL 5min)
       └─ SSE流式返回前端渲染
```

### 数据变更主动失效

| Service层数据变更事件 | 失效缓存Key模式 |
|---------------------|----------------|
| `candidate_profile_updated` | `insight:candidate:{id}:*` |
| `match_score_updated` | `insight:*:{entity_id}:matches` + `insight:candidate:{id}:*` |
| `interview_feedback_submitted` | `insight:candidate:{id}:interviews` + `insight:candidate:{id}:profile` |
| `offer_status_changed` | `insight:candidate:{id}:*` + `insight:position:{id}:*` |
| `position_requirements_updated` | `insight:position:{id}:*` |

**技术链路**：Service数据变更 → `publish_event()` → Redis Pub/Sub → SSE推送 → 前端显示"洞察已过期"标记。

### AI调用降权

- 每次Context Bar的AI洞察计为 **0.5次AI调用**（降权）
- 同一实体+Tab的洞察请求去重（pending请求共享）
- 🔄手动刷新按钮：传 `force_refresh=true` 绕过缓存
