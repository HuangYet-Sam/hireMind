# Offer管理

> **PRD来源**：§4.6 Offer管理（L2459-L2680）
> **PRD版本**：V3.6 | **最后更新**：2026-05-12

---

## 功能概述

**功能ID**：F6 | **优先级**：P0 | **角色**：HR Admin, HR Recruiter, 用人经理 | **映射**：US-019~023

Offer管理模块覆盖Offer方案创建、AI薪资建议、多级审批流、候选人接受/拒绝、入职闭环全流程。支持IM端审批交互，Agent解析"同意/拒绝/修改"意图。

---

## 核心功能

| 功能项 | 描述 | Web端 | IM端 | 端点 |
|--------|------|:---:|:---:|------|
| Offer创建 | 候选人+岗位+薪资方案 | ✅表单 | ✅对话 | `POST /api/v1/offers` |
| AI薪资建议 | 市场数据+内部薪酬+候选人画像 | ✅面板 | ✅对话 | `POST /api/v1/offers/generate` |
| 薪资对标 | 市场分位+内部公平性检验 | ✅面板 | — | `GET /api/v1/offers/:id/benchmark` |
| 审批流 | 多级审批（最多3级） | ✅流程图 | ✅对话审批 | `POST /api/v1/offers/:id/approve` |
| 发送Offer | 发送Offer给候选人 | ✅按钮 | ✅对话 | `POST /api/v1/offers/:id/send` |
| 候选人反馈 | 接受/拒绝/Counter-offer | — | ✅外部链接 | `GET /api/v1/offers/:id/respond/:token` |
| AI谈判策略 | Counter-offer后的AI谈判建议 | ✅面板 | ✅对话 | `POST /api/v1/offers/:id/negotiation-advice` |
| 入职管理 | 入职材料+试用期+关怀提醒 | ✅Tab页 | — | 见入职子模块 |

---

## Offer状态机

```
draft → pending_approval → approved → sent → accepted → hired(由offers.onboarding_status管理)
                ↓              ↓         ↓       ↓
           rejected       rejected  expired  rejected(candidate拒绝)
```

---

## AI能力

### #9 Offer方案建议
- **Service方法**：`offer_service.generate()`
- **模型**：gpt-4.1
- **输入**：候选人画像+薪酬预算
- **输出**：建议薪资结构

### #15 薪资对标分析
- **Service方法**：`offer_service.benchmark()`
- **模型**：gpt-4.1-mini
- **输出**：市场P值+公平性预警+调整建议

### AI谈判策略支持（P1-26新增）
- **触发条件**：候选人提交counter-offer时自动触发
- **AI自动生成**：
  1. 谈判建议：基于候选人画像生成个性化策略
  2. 薪资区间建议：可接受的薪资调整区间
  3. 历史成功案例参考
- **端点**：`POST /api/v1/offers/:id/negotiation-advice`

---

## 业务规则

- Offer决策看画像不看简历（画像100%）
- Offer被拒时，拒绝原因存入`matches.candidate_feedback`
- 同一人Offer一个岗位后，其他岗位matches自动标记withdrawn
- 审批链支持多级（最多3级：HR Recruiter → 用人经理 → HR Admin）
- 审批通过IM消息交互，Agent解析意图
- 内部公平性预警阈值：高于同组均值10%红色预警，5-10%黄色提醒
- 薪资对标数据：Phase 1使用内部历史数据；Phase 2接入第三方API

---

## 入职Onboarding子模块

### 1. 入职材料清单（8项）

| # | 材料项 | 必选/可选 | 收集方式 |
|---|--------|:---:|---------|
| 1 | 劳动合同 | 必选 | 上传扫描件/PDF |
| 2 | 学历证明 | 必选 | 上传毕业证/学位证 |
| 3 | 离职证明 | 必选 | 上传扫描件 |
| 4 | 体检报告 | 必选 | 上传扫描件 |
| 5 | 身份证复印件 | 必选 | 上传正反面 |
| 6 | 银行卡信息 | 必选 | 填写表单（加密） |
| 7 | 社保/公积金转移单 | 可选 | 上传扫描件 |
| 8 | 照片（工牌用） | 可选 | 上传电子版 |

### 2. 试用期目标与考核节点

| 节点 | 时间 | 责任人 | 系统行为 |
|------|------|--------|---------|
| 入职确认 | Day 0 | HR | `onboarding_status`→`onboarded` |
| 7天Check-in | Day 7 | HR/用人经理 | 自动提醒 |
| 30天Check-in | Day 30 | 用人经理 | 评估表填写 |
| 60天Check-in | Day 60 | 用人经理 | 综合评估+调整建议 |
| 90天转正评估 | Day 90 | 用人经理+HR | `onboarding_status`→`probation`完成 |

### 3. 入职后联动
1. 候选人画像status→`onboarded`
2. 其他进行中matches自动withdrawn
3. 简历文件归档（`resumes.status='archived'`）
4. Dashboard统计更新
5. 若filled_count≥headcount，岗位自动流转为`filled`

### 4. 候选人入职自助页（P1-32）
- Token URL（JWT，7天有效，一次性）
- 候选人无需登录，自助上传入职材料
- 端点：`GET /api/v1/onboarding/:token`、`POST /api/v1/onboarding/:token/submit`

---

## 候选人拒绝Offer处理规则（P1-33）

- 候选人拒绝后Offer状态→`rejected`
- AI自动分析拒绝原因
- HR选择下一步：
  ① 重新谈判（AI生成策略）
  ② 启动备选候选人（AI推荐下一候选人）
  ③ 关闭岗位/暂停招聘
- **"启动备选"才推荐**：AI仅在HR选择此选项时推荐

---

## OPC开发模块

**M6 — Offer管理（W22-W25，20天）** 🟢 低风险

| 阶段 | 天数 | 主要工作 |
|------|------|---------|
| 前端先行 | 6天 | Offer列表页、创建表单、详情页、审批流程可视化、审批操作组件、模板管理 |
| 后端开发 | 8天 | DB Schema、offer_service、AI薪资建议、审批流引擎、IM审批交互、模板引擎、Tool注册 |
| 联调验收 | 6天 | Mock→真实API、审批流E2E、AI薪资建议质量、IM审批测试、模板渲染、全流程E2E |

### 验收清单
- ✅ Offer审批流通过IM完成
- ✅ AI薪资建议合理（偏差<20%）
- ✅ 多级审批正确（2-4级）
- ✅ Offer状态机全链路正确
- ✅ IM审批交互延迟<3s

---

*本文档从 HireMind PRD V3.6 §4.6 提取，完整PRD请参考 `/prd/HireMind-PRD-V3.6.md`*
