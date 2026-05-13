# 智能匹配

> **PRD来源**：§4.4 智能匹配（L1968-L2031）
> **PRD版本**：V3.6 | **最后更新**：2026-05-12

---

## 功能概述

**功能ID**：F4 | **优先级**：P0 | **角色**：HR Admin, HR Recruiter | **映射**：US-010, US-011, US-013, US-014

智能匹配模块保留为**批量匹配与高级配置入口**，日常匹配已深度嵌入岗位360°视图和候选人360°视图。本模块服务于「一键全量匹配」「跨岗位批量匹配」「匹配配置调优」等场景。

---

## 日常匹配（嵌入式，不走本页面）

- **岗位360°视图 → Tab2投递候选人** → 点击「批量匹配」→ 为投递候选人生成匹配分数
- **岗位360°视图 → Tab3推荐候选人** → 点击「执行新一轮匹配」→ 从全量候选人库中重新匹配
- **候选人360°视图 → Tab2岗位匹配** → 点击「匹配其他岗位」→ 反向匹配

---

## 本模块功能（批量匹配高级入口）

| 功能项 | 描述 | Web端 | IM端 | 端点 |
|--------|------|:---:|:---:|------|
| 批量匹配 | 选择多个岗位 → 一键全量匹配 | ✅批量操作 | ✅对话 | `POST /api/v1/matching/run` |
| 匹配进度 | SSE实时进度 | ✅进度条 | ✅文字 | SSE |
| 匹配配置 | 调整匹配阈值/维度权重 | ✅配置面板 | ✅对话 | `PATCH /api/v1/matching/config` |
| 匹配解释 | AI详细分析为什么匹配/不匹配 | ✅按钮 | ✅对话 | `GET /api/v1/matches/:id/explain` |
| 全局匹配看板 | 所有岗位的匹配结果总览 | ✅表格 | ✅对话 | `GET /api/v1/matches` |

---

## 匹配技术架构

### 混合检索 RRF 架构

```
第一阶段（向量召回）：
  pgvector HNSW+SQ8向量检索 + PG tsvector全文检索
  → RRF(Reciprocal Rank Fusion)融合两路结果

第二阶段（LLM精排）：
  gpt-4.1对Top-30候选重排序
  → 输出Top-10 + 匹配解释
```

### 分维评分

- `skill_score` — 技能匹配分
- `experience_score` — 经验匹配分
- `salary_score` — 薪资匹配分
- `overall_score` — 综合分
- `inference_score` — 推理增强分（AI能力#18输出）

### 推理增强评分
- `inferred_overall`：推理增强总分
- `inference_contributions[]`：各推理贡献项 `{factor, description, delta}`
- `inference_delta`：推理增强分差

---

## 匹配生命周期

非线性有向图，支持分支和回退：

```
pending → screening → shortlisted → interview_scheduled → interviewed → offered → hired
              ↓            ↓                ↓                ↓           ↓
         rejected     rejected          rejected          rejected    rejected
                                                                          ↑
                                                        所有状态均可 → withdrawn（候选人主动撤回）
```

### 状态枚举（9值）

| 状态 | 说明 |
|------|------|
| `pending` | 初始匹配，待筛选 |
| `screening` | 简历筛选中 |
| `shortlisted` | 筛选通过，入围 |
| `interview_scheduled` | 面试已安排 |
| `interviewed` | 面试完成 |
| `offered` | 已发Offer |
| `hired` | 已录用（matches终态） |
| `rejected` | 不合适（任何阶段可拒绝） |
| `withdrawn` | 候选人主动撤回 |

### P2-30修复
- matches状态机终点为 `hired`，**不再包含`onboarded`状态**
- 入职相关状态由 `offers.onboarding_status` 统一管理
- Dashboard统计"已入职"指标来源为 `offers.onboarding_status='completed'`

---

## 匹配排序反馈机制

> P1-34新增，M2交付基础版

### 功能描述
HR对匹配排序进行👍/👎反馈，系统收集反馈数据用于后续算法优化。

### 交互方式
- 👍正确：AI匹配排序合理
- 👎错误：展开可选原因（技能不匹配/经验不符/薪资差距大/其他）

### 数据存储
`match_feedback` 表：`match_id` + `feedback_type` + `reason` + `created_by` + `created_at`

### 端点
- `POST /api/v1/matches/:id/feedback` — 提交反馈
- `GET /api/v1/matches/feedback-stats` — 反馈统计

### 里程碑
- **M2基础版**：仅收集反馈数据，展示反馈统计
- **M3+进阶版**（Phase 2）：基于反馈数据自动调整匹配权重

---

## 冷启动策略

候选人无画像时用简历向量做初始筛选，5-15分钟异步构建画像后切换。

---

## AI能力

### #4 人岗智能匹配
- **Service方法**：`matching_service.run()`
- **模型**：gpt-4.1（精排）+ text-embedding-3-small（向量）
- **降级方案**：纯向量检索（无LLM精排）
- **评估指标**：Top10命中率>70%

### #5 匹配解释生成
- **Service方法**：`matching_service.explain()`
- **模型**：gpt-4.1-mini
- **输出**：分维度差距+改进建议

### #18 岗位匹配推理增强
- **Service方法**：`matching_service.infer_match()`
- **模型**：gpt-4.1
- **输出**：增强匹配度+新增贡献分解+面试建议

---

## OPC开发模块

**M4 — 智能匹配（W13-W16，21天）** 🔴 高风险

| 阶段 | 天数 | 主要工作 |
|------|------|---------|
| 前端先行 | 6天 | 匹配结果列表、看板视图、匹配详情页、反向匹配页、反馈组件、批量匹配进度条 |
| 后端开发 | 8天 | DB Schema、matching_service、岗位/候选人向量化、RRF混合检索、Rerank层、匹配解释、Tool注册 |
| 联调验收 | 7天 | Mock→真实API、RRF端到端验证、匹配解释质量评估、反向匹配、性能优化、准确率基准测试 |

### 验收清单
- ✅ 向量匹配准确率>70%（人工评估Top10命中率）
- ✅ 匹配解释可读性强，HR可理解
- ✅ 匹配响应时间<2s（100候选人×10岗位）
- ✅ 反向匹配正常工作
- ✅ 匹配反馈端点正常
- ✅ RRF融合优于纯向量检索

### 风险缓解
- 🔴 准备人工标注数据集（10岗位×100候选人）
- 🔴 准备Cohere Rerank备选方案
- 🔴 预留3天buffer用于算法调优

---

*本文档从 HireMind PRD V3.6 §4.4 提取，完整PRD请参考 `/prd/HireMind-PRD-V3.6.md`*
