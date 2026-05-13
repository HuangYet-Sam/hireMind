# 组织架构与岗位管理

> **PRD来源**：§4.1 组织架构与岗位管理（L931-L1349）
> **PRD版本**：V3.6 | **最后更新**：2026-05-12

---

## 功能概述

**功能ID**：F1 | **优先级**：P0 | **角色**：HR Admin, HR Recruiter

组织架构与岗位管理是HireMind招聘系统的核心基础模块，提供部门管理、岗位CRUD、AI辅助JD生成、岗位360°视图等功能。

## 部门管理

### 部门树形结构
- 支持多级组织架构树（≥3级）
- 部门CRUD操作（增删改查）
- 层级约束与排序
- 部门与岗位的关联管理

### 端点

| 端点 | 用途 |
|------|------|
| `/api/v1/departments` | 部门列表（树形） |
| `/api/v1/departments/:id` | 部门详情/更新/删除 |

---

## 岗位管理

### 岗位状态机

```
draft → active → paused → closed
                 ↓
               archived
```

| 状态 | 说明 |
|------|------|
| `draft` | 草稿，未发布 |
| `active` | 在招中，接受简历 |
| `paused` | 暂停招聘 |
| `closed` | 已关闭（招满/取消） |
| `archived` | 已归档 |

### 岗位CRUD

- **创建岗位**：基础信息 + 任职要求 + AI引导式创建
- **编辑岗位**：支持草稿状态编辑，active状态下部分字段可编辑
- **关闭岗位**：招满自动关闭（filled_count ≥ headcount）或手动关闭

### 核心字段

- 岗位名称、所属部门、招聘人数（headcount）
- 薪资范围（salary_min/salary_max，L2内部信息，明文存储）
- 任职要求（技能/经验/学历）
- 岗位描述（JD）
- 岗位状态、创建时间、更新时间

### API端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/positions` | GET | 岗位列表（筛选/排序/分页） |
| `/api/v1/positions` | POST | 创建岗位 |
| `/api/v1/positions/:id` | GET | 岗位详情 |
| `/api/v1/positions/:id` | PATCH | 更新岗位 |
| `/api/v1/positions/:id` | DELETE | 删除岗位（仅draft状态） |
| `/api/v1/positions/:id/generate-jd` | POST | AI生成JD |
| `/api/v1/positions/:id/status` | PATCH | 岗位状态流转 |

---

## AI能力

### #6 JD智能生成
- **输入**：岗位名称 + 3-5关键要求
- **处理**：LLM生成结构化JD（gpt-4.1 + Few-shot）
- **输出**：完整JD文本（HTML）
- **Service方法**：`position_service.generate_jd()`
- **端点**：`POST /api/v1/positions/:id/generate-jd`

### #7 岗位画像构建
- **输入**：岗位描述 + 任职要求
- **处理**：结构化+向量化双模存储
- **输出**：岗位画像卡片 + embedding
- **Service方法**：`position_service.build_profile()`
- **模型**：text-embedding-3-small（1536维）

---

## 岗位360°视图

路由：`/hr/positions/:id`

### Tab式布局
1. **基本信息**：岗位描述、薪资范围、招聘人数、状态
2. **投递候选人**：投递到该岗位的候选人列表 + 批量匹配
3. **推荐候选人**：AI推荐的全量候选人匹配结果
4. **面试安排**：该岗位所有面试
5. **匹配统计**：岗位招聘漏斗、匹配分布

### AI Context Bar
- 详情页顶部AI洞察栏
- 随Tab动态刷新
- 展示岗位健康度、匹配建议等

---

## 乐观锁与并发控制

- 岗位编辑使用乐观锁（version字段）
- DDL：`version INTEGER NOT NULL DEFAULT 1`
- 更新时：`UPDATE ... SET version=version+1 WHERE id=:id AND version=:expected_version`
- 影响行数=0 → 抛ConcurrentModificationError(50003)

---

## OPC开发模块

**M1 — 组织架构 + 岗位管理（W3-W5，18天）**

| 阶段 | 天数 | 主要工作 |
|------|------|---------|
| 前端先行 | 5天 | 组织架构树、岗位列表、创建/编辑表单、360°详情页骨架、AI Context Bar |
| 后端开发 | 7天 | DB Schema、organization_service、position_service、API端点、Tool注册、AI能力#6#7 |
| 联调验收 | 6天 | Mock→真实API替换、状态机联调、AI JD生成E2E、向量化验证、单元测试 |

### 验收清单
- ✅ HR可创建/编辑/关闭岗位
- ✅ 组织架构树形展示正确（支持3级以上层级）
- ✅ AI JD生成功能可用（gpt-4.1 + Few-shot，生成时间<15s）
- ✅ 岗位状态机流转正确（draft→active→paused→closed）
- ✅ 岗位画像向量化存储正确（text-emb-3-small 1536维）
- ✅ 单元测试覆盖率>80%

---

*本文档从 HireMind PRD V3.6 §4.1 提取，完整PRD请参考 `/prd/HireMind-PRD-V3.6.md`*
