# 确定性端点（CRUD）— 非AI能力端点

> **PRD来源**：§9.1 确定性端点（CRUD，无LLM，50-200ms）、§9.1 Dashboard端点、§9.1 AI任务中心端点、§9.1 主动式AI引擎端点

> **HTTP方法使用规范**：`POST`创建资源、`GET`查询资源、`PATCH`部分更新（字段级修改，如状态流转、配置调整）、`PUT`全量替换（完整资源覆盖）、`DELETE`删除资源。所有部分更新场景统一使用 `PATCH`，仅全量替换场景使用 `PUT`。

---

## 1. departments（部门）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/departments` | 创建部门 | Admin |
| GET | `/api/v1/departments` | 部门树（含岗位统计） | All |
| GET | `/api/v1/departments/:id` | 部门详情（含下属岗位列表+编制统计） | All |
| PATCH | `/api/v1/departments/:id` | 更新部门 | Admin |
| DELETE | `/api/v1/departments/:id` | 删除部门（需无在岗人员） | Admin |

---

## 2. positions（岗位）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/positions` | 创建岗位（必填department_id） | HR, Admin |
| POST | `/api/v1/positions/ai-interpret` | AI引导式创建-意图解读（自然语言→结构化JD草稿，§10.10第2步） | HR, Admin |
| POST | `/api/v1/positions/ai-confirm` | AI引导式创建-确认生成（用户确认后生成正式JD+向量化，§10.10第4-5步） | HR, Admin |
| GET | `/api/v1/positions` | 岗位列表（分页/筛选/排序） | All |
| GET | `/api/v1/positions/:id` | 岗位360°视图 | All |
| GET | `/api/v1/positions/:id/funnel` | 岗位招聘漏斗数据 | All |
| GET | `/api/v1/positions/:id/timeline` | 岗位生命周期时间线 | All |
| PATCH | `/api/v1/positions/:id` | 更新岗位 | HR, Admin |
| PATCH | `/api/v1/positions/:id/status` | 岗位状态流转 | HR, Admin |
| POST | `/api/v1/positions/rebuild-vectors` | 岗位向量全量重建（ARQ异步任务，触发条件：Embedding模型升级/季度质量修复/岗位需求大幅调整，§7.2.1） | Admin |

---

## 3. resumes（简历）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/resumes/upload` | 上传简历文件 | HR, Headhunter |
| GET | `/api/v1/resumes` | 简历列表 | HR, Admin |
| GET | `/api/v1/resumes/:id` | 简历详情 | HR, Admin |

---

## 4. candidates（候选人）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/candidates` | 创建候选人 | HR, Admin |
| GET | `/api/v1/candidates` | 候选人列表（高级筛选） | HR, Admin |
| GET | `/api/v1/candidates/:id` | 候选人360°视图 | HR, Admin |
| GET | `/api/v1/candidates/:id/profile` | 候选人画像详情（含更新历史） | HR, Admin |
| GET | `/api/v1/candidates/:id/communications` | 候选人沟通记录时间线 | HR, Admin |
| PATCH | `/api/v1/candidates/:id` | 更新候选人信息 | HR, Admin |
| DELETE | `/api/v1/candidates/:id` | 软删除候选人（status→inactive，保留数据7天后物理删除，§12.1数据删除SLA） | Admin |
| POST | `/api/v1/candidates/:id/blacklist` | 加入黑名单 | HR, Admin |
| DELETE | `/api/v1/candidates/:id/blacklist` | 移出黑名单 | HR, Admin |

---

## 5. matches（匹配）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/matches` | 匹配记录列表 | HR, Admin |
| GET | `/api/v1/matches/:id` | 匹配详情 | HR, Admin |
| PATCH | `/api/v1/matching/config` | 匹配算法配置（不调LLM，纯配置更新） | Admin |

---

## 6. interviews（面试）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/interviews` | 创建面试 | HR, Admin |
| GET | `/api/v1/interviews` | 面试列表（支持日历视图） | HR, Interviewer, Admin |
| GET | `/api/v1/interviews/:id` | 面试详情 | HR, Interviewer, Admin |
| POST | `/api/v1/interviews/:id/scores` | 提交面试评分（HR代填） | HR, Admin |
| GET | `/api/v1/interviews/workload-stats` | 面试官工作量统计 | HR, Admin |

---

## 7. offers（Offer）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/offers` | Offer列表查询（支持?status=&candidate_id=筛选） | HR, Admin |
| POST | `/api/v1/offers` | 创建Offer | HR, Admin |
| GET | `/api/v1/offers/:id` | Offer详情 | HR, HiringManager, Admin |
| POST | `/api/v1/offers/:id/approve` | 审批Offer | HiringManager, Approver |
| POST | `/api/v1/offers/:id/onboard` | 确认入职（HR手动确认入职日期，触发offered→hired→onboarded） | HR, Admin |
| GET | `/api/v1/offers/:id/onboard` | 获取入职信息（入职日期/onboarding_status） | HR, Admin |
| PATCH | `/api/v1/offers/:id/onboarding-materials` | 审核入职材料 | HR, Admin |
| PATCH | `/api/v1/offers/:id/status` | Offer状态流转（不调LLM，纯状态变更） | HR, Admin |

---

## 8. analytics（分析）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/analytics/funnel` | 招聘漏斗数据 | HR, Admin |
| GET | `/api/v1/analytics/channel-roi` | 渠道ROI数据 | HR, Admin |

---

## 9. onboarding（入职）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/onboarding/:token` | 入职自助页数据获取（候选人通过Token获取入职表单） | 无需认证（JWT自校验） |
| POST | `/api/v1/onboarding/:token/submit` | 入职材料提交（候选人提交入职材料） | 无需认证（JWT自校验） |
| GET | `/api/v1/onboarding/:token/status` | 入职进度查询（查询入职流程当前状态） | 无需认证（JWT自校验） |

---

## 10. share-links（共享链接）

> **PRD来源**：§9.1 + 共享链接端点补充（P2-32）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/share-links` | 创建共享链接（含有效期+权限范围） | HR, Admin |
| GET | `/api/v1/share-links` | 查询已创建的共享链接列表 | HR, Admin |
| DELETE | `/api/v1/share-links/:id/revoke` | **撤销共享链接（立即失效）** | HR, Admin |
| POST | `/api/v1/share-links/:id/renew` | **续期共享链接（延长7天）** | HR, Admin |
| GET | `/api/v1/share/:token/dashboard` | 用人经理通过共享链接访问Dashboard | 无需认证（JWT自校验） |

**共享链接安全机制**：

| 维度 | 要求 |
|------|------|
| 防篡改 | JWT签名校验，URL不含敏感信息 |
| 审计 | 共享链接访问记录审计日志（含IP/UA/时间/操作） |
| 撤销机制 | HR可随时撤销，撤销后Redis黑名单+JWT的jti校验 |
| 敏感数据保护 | 薪资等敏感数据在共享链接中默认隐藏（`***`），需点击「显示」按钮二次确认后展示 |
| 访问日志 | 每次访问记录：`{share_link_id, visitor_ip, user_agent, accessed_at, data_viewed}` |

---

## 11. feedback（面试反馈）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/feedback/:token` | **面试官通过JWT Token链接提交反馈（无需登录，频率限制5min/3次，提交后Token失效）** | 无需认证（JWT自校验） |
| GET | `/api/v1/feedback/:token` | 获取Token对应的反馈表单（无需登录，JWT签名+有效期校验） | 无需认证（JWT自校验） |

---

## 12. Dashboard端点（确定性，50-200ms）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/dashboard/todos` | 待办清单（新简历/面试/Offer/审批待处理等） | HR, Admin |
| GET | `/api/v1/dashboard/schedule` | 今日日程（面试/跟进/截止） | HR, Admin |
| GET | `/api/v1/dashboard/metrics` | 快捷指标（在招岗位数/候选人总数/本周面试数） | HR, Admin |
| GET | `/api/v1/dashboard/ai-insights` | AI洞察推送（主动式AI引擎触发的推荐） | HR, Admin |

---

## 13. AI任务中心端点（确定性，50-200ms）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/tasks` | 任务列表（分页/筛选：状态/类型/时间） | HR, Admin |
| GET | `/api/v1/tasks/:id` | 任务详情+进度百分比+子步骤 | HR, Admin |
| POST | `/api/v1/tasks/:id/cancel` | 取消运行中/排队中的任务 | HR, Admin |
| GET | `/api/v1/tasks/stats` | 任务统计（运行中/排队/已完成/失败） | HR, Admin |
| GET | `/api/v1/tasks/running` | 运行中任务列表 | HR |
| GET | `/api/v1/tasks/completed` | 已完成任务列表 | HR |
| GET | `/api/v1/tasks/queued` | 排队中任务列表 | HR |
| POST | `/api/v1/tasks/:id/retry` | 重试失败任务 | HR |
| GET | `/api/v1/tasks/:id/events` | 任务事件SSE流 | HR |

---

## 14. 主动式AI引擎端点（Agent触发+状态管理，50-500ms）

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/ai/proactive/trigger` | 手动触发主动式AI场景（传入`scene_id`+可选参数） | HR, Admin |
| GET | `/api/v1/ai/proactive/status/:task_id` | 查询主动式任务执行状态（含进度百分比+推送结果） | HR, Admin |
| GET | `/api/v1/ai/proactive/config` | 获取全部主动式场景配置（8场景开关+参数+调度时间） | HR, Admin |
| PATCH | `/api/v1/ai/proactive/config/:scene_id` | 更新单个场景开关/参数（如关闭"沉睡候选人激活"、调整推送时间） | Admin |

---

> **说明**：用人经理（Hiring Manager）非系统用户，通过HR生成的只读共享链接访问Dashboard，无需登录系统。共享链接含Token鉴权+有效期+权限范围限制。
