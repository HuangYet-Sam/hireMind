# 简历库

> **PRD来源**：§4.2 简历库（L1350-L1687）
> **PRD版本**：V3.6 | **最后更新**：2026-05-12

---

## 功能概述

**功能ID**：F2 | **优先级**：P0 | **角色**：HR Admin, HR Recruiter | **映射**：US-003~005

简历库模块是候选人数据的入口，负责简历上传、AI解析、去重、可信度检测、多版本管理等功能。基于SmartResume二开引擎，支持PDF/Word/图片格式简历的结构化抽取。

---

## 核心功能

### 简历上传

| 功能项 | 描述 | Web端 | IM端 | 端点 |
|--------|------|:---:|:---:|------|
| 单文件上传 | 拖拽/点击上传PDF/Word/图片 | ✅上传组件 | ✅文件发送 | `POST /api/v1/resumes/upload` |
| 批量上传 | 多文件并行上传+进度 | ✅批量 | ✅多文件 | `POST /api/v1/resumes/batch-upload` |
| 文件限制 | 单文件<10MB，支持PDF/Word/JPG/PNG | ✅前端校验 | ✅提示 | 中间件 |

### 简历AI解析

| 功能项 | 描述 | 端点 |
|--------|------|------|
| 结构化抽取 | 7类字段抽取（基本信息/工作经历/教育/技能/证书/语言/项目） | `POST /api/v1/resumes/:id/parse` |
| 字段溯源 | 每个抽取字段附带原文位置标注 | 解析结果内嵌 |
| OCR兜底 | 图片简历→OCR→结构化抽取 | 自动触发 |
| 解析状态 | pending → parsing → completed / failed | `GET /api/v1/resumes/:id/parse-status` |

### 简历去重

| 功能项 | 描述 | 端点 |
|--------|------|------|
| 自动去重 | phone+email组合唯一校验 + 相似度预检 | 上传时自动执行 |
| 多版本管理 | 同一候选人多次投递→版本关联 | `GET /api/v1/resumes/:id/versions` |
| 手动合并 | HR手动合并重复简历 | `POST /api/v1/resumes/merge` |

### 简历可信度检测

| 功能项 | 描述 | 端点 |
|--------|------|------|
| 内部一致性 | 日期交叉验证、薪资合理性、学历-岗位匹配度 | `GET /api/v1/resumes/:id/credibility` |
| 跨简历一致性 | 多简历同字段值对比，检测矛盾 | 自动检测 |
| 外部合理性 | 行业常识验证 | Phase 2 |

### 简历搜索与筛选

| 功能项 | 描述 | 端点 |
|--------|------|------|
| 多条件筛选 | 按状态/来源/日期/解析结果筛选 | `GET /api/v1/resumes` |
| 全文搜索 | 关键词搜索简历内容 | `GET /api/v1/resumes/search` |
| 自然语言搜索 | LLM提取条件→DB查询 | Agent对话 |

---

## 数据模型

### resumes 表核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID | 租户ID |
| candidate_id | UUID | 关联候选人（去重后关联） |
| file_path | VARCHAR | MinIO存储路径 |
| file_hash | VARCHAR(64) | 文件SHA256哈希 |
| status | ENUM | pending/parsing/completed/failed |
| source | VARCHAR | 来源渠道 |
| version | INTEGER | 乐观锁版本号 |
| created_at | TIMESTAMP | 创建时间 |

### 解析结果 JSONB 结构（7类）

```json
{
  "basic_info": { "name": "...", "phone": "...", "email": "...", ... },
  "work_experience": [...],
  "education": [...],
  "skills": [...],
  "certifications": [...],
  "languages": [...],
  "projects": [...],
  "_source_refs": [
    { "field": "basic_info.name", "type": "text", "page": 1, "para": 2, "confidence": 0.95 }
  ]
}
```

---

## AI能力

### #1 简历AI解析（SmartResume二开）
- **输入**：PDF/Word文件
- **处理**：文本提取→LLM结构化抽取（gpt-4.1-mini）
- **输出**：姓名/技能/经验/学历 JSON
- **Service方法**：`resume_service.parse()`
- **降级方案**：纯文本提取+正则兜底
- **评估指标**：字段准确率>90%

### #14 简历可信度检测
- **输入**：简历文本+同人多版简历+行业常识
- **处理**：三层验证（内部一致性+跨简历一致性+外部合理性）
- **输出**：可信度等级+矛盾清单+面试验证建议
- **Service方法**：`resume_service.verify_credibility()`
- **模型**：gpt-4.1

---

## SmartResume二开说明

SmartResume（https://github.com/alibaba/SmartResume）作为简历解析引擎，Fork二开为 `hr_agent/resume_parser` 子包。

### 二开内容
1. **增加中文模型权重**：EasyOCR中文扩展 + Qwen3-0.6B中文微调权重
2. **对接HireMind profile JSONB schema**：映射到7类子结构
3. **输出source_refs溯源信息**：`{type, id, page, para, confidence}` 溯源标注

### 二开工作量
2-3天（1名Python开发）

---

## 文件存储

- **存储**：MinIO加密桶（私有化）
- **访问**：签名URL
- **限制**：单文件<10MB
- **格式**：PDF/Word/JPG/PNG

---

## OPC开发模块

**M2 — 简历解析（W6-W8，17天）** 🔴 高风险

| 阶段 | 天数 | 主要工作 |
|------|------|---------|
| 前端先行 | 5天 | 简历库列表页、上传组件、详情页、360°视图骨架、可信度指示器 |
| 后端开发 | 7天 | DB Schema、resume_service、SmartResume解析引擎、去重引擎、可信度检测、Tool注册 |
| 联调验收 | 5天 | Mock→真实API、Golden Dataset验证（50份简历）、去重检测、OCR兜底 |

### 验收清单
- ✅ PDF/Word/图片简历上传成功（单文件<10MB）
- ✅ 结构化抽取准确率>85%（Golden Dataset 50份简历）
- ✅ 去重检测正常工作（phone+email重复→自动合并）
- ✅ 解析失败简历有明确错误提示 + 人工编辑入口
- ✅ OCR兜底流程可用
- ✅ 解析耗时<30s/份

### 风险缓解
- 🔴 准备50份多语言、多格式Golden Dataset
- 🔴 准确率不达标时增加Few-shot示例（5→10个）
- 🔴 预留2天buffer用于Prompt调优

---

*本文档从 HireMind PRD V3.6 §4.2 提取，完整PRD请参考 `/prd/HireMind-PRD-V3.6.md`*
