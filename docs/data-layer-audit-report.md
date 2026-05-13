# HireMind 数据层审计报告

> **审计角色**：数据架构师  
> **审计日期**：2026-05-12  
> **审计范围**：PRD V3.6 §7数据模型 vs 当前Prisma Schema + 数据基础设施  
> **审计结论**：**差距严重（Critical）** — 当前实现仅覆盖PRD目标数据层的约25%

---

## 0. 执行摘要

| 维度 | PRD V3.6 目标 | 当前状态 | 差距评级 |
|------|-------------|---------|---------|
| 数据表 | 19+核心表+19扩展实体 | 11个Prisma Model | 🔴 Critical |
| 向量检索 | pgvector + pgvectorscale + HNSW | Unsupported("Vector")占位 | 🔴 Critical |
| 对象存储 | MinIO（简历/录音/合同/附件） | 无（.env引用Supabase但未实现） | 🔴 Critical |
| 缓存 | Redis（会话/热查询/限流/JD缓存） | 无 | 🔴 Critical |
| 审计日志 | audit_log + ai_decisions表 | 无 | 🟡 High |
| SSE实时推送 | 面试状态/匹配结果/审批通知 | 无 | 🟡 High |
| ORM/迁移 | Prisma → SQLAlchemy（FastAPI） | 当前Next.js+Prisma（与PRD架构不一致） | 🔴 Critical |

---

## 1. Schema完整性审计

### 1.1 缺失的核心表（PRD §7.2 五大核心实体）

| # | PRD定义的表 | 当前Schema | 状态 | 优先级 |
|---|-----------|-----------|------|--------|
| 1 | `positions`（岗位画像） | `Job` model（字段大量缺失） | ⚠️ 部分存在 | P0 |
| 2 | `candidates`（人才画像） | `Candidate` model（字段大量缺失） | ⚠️ 部分存在 | P0 |
| 3 | `resumes`（简历文件） | `Resume` model（字段大量缺失） | ⚠️ 部分存在 | P0 |
| 4 | `interviews`（面试记录） | ❌ 不存在 | 🔴 缺失 | P0 |
| 5 | `matches`（匹配记录） | `Application` model（设计不符） | ⚠️ 概念冲突 | P0 |

### 1.2 完全缺失的表（PRD §7.7 19个扩展实体）

| # | 表名 | 用途 | 优先级 |
|---|------|------|--------|
| 1 | `tenants` | 多租户隔离（D2） | P0（Phase 1至少需默认行） |
| 2 | `departments` | 组织架构树（D1） | P0 |
| 3 | `offers` | Offer全生命周期 | P0 |
| 4 | `onboarding_tasks` | 入职任务清单 | P0 |
| 5 | `evaluation_templates` | 面试评估模板（B4） | P0 |
| 6 | `channels` | 招聘渠道（C3） | P1 |
| 7 | `profile_updates` | 画像更新溯源 | P1 |
| 8 | `conflict_resolutions` | 数据冲突裁决 | P1 |
| 9 | `match_feedback` | 匹配反馈 | P1 |
| 10 | `share_links` | 共享链接 | P1 |
| 11 | `ai_decisions` | AI决策审计（§7.8a） | P1 |
| 12 | `consent_records` | 候选人知情同意（P2-31） | P1 |
| 13 | `interviewer_profiles` | 面试官评分偏差校准 | P2 |
| 14 | `referrers` | 内推奖励追踪 | P2 |
| 15 | `headhunter_agencies` | 猎头机构 | P2 |
| 16 | `requisitions` | 招聘需求单（B1） | P1 |
| 17 | `communication_logs` | 沟通记录（B8） | P1 |
| 18 | `match_configurations` | 匹配配置（C2） | P1 |
| 19 | `user_preferences` | AI记忆L1用户偏好 | P2 |

### 1.3 已有表的字段差距分析

#### 1.3.1 `jobs` vs PRD `positions`

| PRD字段 | 类型 | 当前Schema | 状态 |
|---------|------|-----------|------|
| `id` UUID PK | UUID | `id` String @default(cuid()) | ⚠️ 类型不符（cuid→UUID） |
| `department_id` UUID FK | FK → departments | ❌ 缺失 | 🔴 |
| `required_skills` JSONB | JSONB | ❌ 缺失 | 🔴 |
| `required_exp_min/max` INT | INT | ❌ 缺失 | 🔴 |
| `salary_currency` VARCHAR(3) | VARCHAR | ❌ 缺失 | 🟡 |
| `profile_summary` TEXT | TEXT | ❌ 缺失 | 🔴 |
| `profile_keywords` JSONB | JSONB | ❌ 缺失 | 🔴 |
| `jd_text` TEXT | TEXT | `description` String（不等价） | ⚠️ |
| `headcount` INT | INT | ❌ 缺失 | 🔴 |
| `filled_count` INT | INT | ❌ 缺失 | 🔴 |
| `priority` ENUM | urgent/high/normal/low | ❌ 缺失 | 🟡 |
| `embedding_id` VARCHAR | 向量行ID | ❌ 缺失（仅在JobEmbedding中） | 🔴 |
| `published_at` TIMESTAMPTZ | TIMESTAMP | ❌ 缺失 | 🟡 |
| `closed_at` TIMESTAMPTZ | TIMESTAMP | ❌ 缺失 | 🟡 |
| `created_by` UUID FK | FK → users | ❌ 缺失 | 🔴 |
| `tenant_id` UUID FK | FK → tenants | ❌ 缺失 | 🔴 |
| `version` INT | 乐观锁 | ❌ 缺失 | 🟡 |
| `status` CHECK | draft/open/paused/closed/filled | DRAFT/OPEN/PAUSED/CLOSED/ARCHIVED | ⚠️ 枚举值不一致（缺filled，多ARCHIVED） |
| `salary_min/max` NUMERIC(12,2) | NUMERIC | `salaryMin/salaryMax` Int | ⚠️ 精度不符（Int→NUMERIC） |

**差距**：PRD定义25+字段，当前Schema仅约10个字段且类型不一致。

#### 1.3.2 `candidates` vs PRD `candidates`

| PRD字段 | 类型 | 当前Schema | 状态 |
|---------|------|-----------|------|
| `email` AES-256加密 | VARCHAR(255)密文 | `email` String?（明文） | 🔴 安全违规 |
| `email_hash` SHA256 | VARCHAR(64) | ❌ 缺失 | 🔴 |
| `phone` AES-256加密 | VARCHAR(255)密文 | `phone` String?（明文） | 🔴 安全违规 |
| `phone_hash` SHA256 | VARCHAR(64) | ❌ 缺失 | 🔴 |
| `name_encrypted` AES-256 | VARCHAR(512)密文 | `name` String（明文） | 🔴 安全违规 |
| `name_hash` SHA256 | VARCHAR(64) | ❌ 缺失 | 🔴 |
| `profile` JSONB（7类子结构） | JSONB | ❌ 缺失（仅有summary） | 🔴 |
| `source_refs` JSONB | JSONB | ❌ 缺失 | 🔴 |
| `credibility_score` FLOAT | FLOAT | ❌ 缺失 | 🔴 |
| `credibility_grade` ENUM A/B/C/D | CHAR(1) | ❌ 缺失 | 🔴 |
| `inference_data` JSONB | JSONB | ❌ 缺失（在AiProfile中部分覆盖） | 🟡 |
| `embedding_id` VARCHAR | 向量行ID | ❌ 缺失 | 🔴 |
| `tenant_id` UUID FK | FK → tenants | `companyId` FK → Company | ⚠️ 概念不同 |
| `status` ENUM | active/inactive/blacklisted/onboarded | ❌ 缺失 | 🔴 |
| `version` INT | 乐观锁 | ❌ 缺失 | 🟡 |
| UNIQUE约束 | (phone_hash, email_hash) | (email, companyId) | 🔴 不符合（明文+非安全去重） |

**关键安全风险**：PII字段（姓名/手机/邮箱）明文存储，违反个保法§51条数据分类分级要求（PRD要求L3级AES-256加密）。

#### 1.3.3 `applications` vs PRD `matches`

当前 `Application` 模型与 PRD `matches` 表设计存在**概念冲突**：

| 差异项 | 当前 Application | PRD matches | 状态 |
|--------|-----------------|-------------|------|
| 表名语义 | "申请/投递" | "匹配记录"（双向） | ⚠️ 不对齐 |
| 状态枚举 | APPLIED/SCREENING/INTERVIEW/OFFER/REJECTED/HIRED/WITHDRAWN（7值线性） | pending/screening/shortlisted/interview_scheduled/interviewed/offered/hired/rejected/withdrawn（9值非线性有向图） | 🔴 严重不符 |
| 评分字段 | `matchScore` Float? + `matchReason` String? | overall_score + skill_score + experience_score + education_score + inference_score + salary_score + score_breakdown(JSONB) + vector_similarity | 🔴 缺失5个分维评分 |
| 发起方向 | 无 | `initiated_by` system/candidate/hr | 🔴 缺失 |
| 匹配详情 | 无 | match_details(JSONB) + candidate_feedback(JSONB) | 🔴 缺失 |

#### 1.3.4 `resumes` vs PRD `resumes`

| PRD字段 | 当前Schema | 状态 |
|---------|-----------|------|
| `position_id` UUID FK | ❌ 缺失 | 🔴 |
| `source` ENUM | ❌ 缺失（仅有Candidate.source） | 🟡 |
| `parsed_data` JSONB（immutable） | `parsedText` String? | ⚠️ 类型不符（String→JSONB） |
| `source_refs` JSONB | ❌ 缺失 | 🟡 |
| `credibility` JSONB | ❌ 缺失 | 🟡 |
| `uploaded_by` UUID FK | ❌ 缺失 | 🔴 |
| `tenant_id` UUID | ❌ 缺失 | 🔴 |
| `file_url` MinIO路径 | `fileUrl`（注释写Supabase） | ⚠️ 存储后端不符 |
| `file_type` CHECK约束 | `fileType` String（无CHECK） | ⚠️ |
| CHECK约束 | parse_status=completed AND candidate_id IS NOT NULL | ❌ 缺失 | 🟡 |

#### 1.3.5 `users` vs PRD `users`

| PRD字段 | 当前Schema | 状态 |
|---------|-----------|------|
| `tenant_id` UUID FK | `companyId` FK → Company | ⚠️ 概念不同 |
| `email` VARCHAR(255) | `email` String @unique | ⚠️ 缺UNIQUE(tenant_id, email)组合约束 |
| `name_encrypted` TEXT（AES-256） | `name` String（明文） | 🔴 安全违规 |
| `role` hr_admin/hr_recruiter | OWNER/ADMIN/MEMBER | 🔴 枚举值完全不符 |
| `is_active` BOOLEAN | ❌ 缺失 | 🟡 |
| `last_login_at` TIMESTAMPTZ | ❌ 缺失 | 🟡 |

### 1.4 缺失的索引

| 表 | PRD要求的索引 | 当前状态 |
|----|-------------|---------|
| positions | idx_positions_department, idx_positions_status, idx_positions_tenant | ❌ 无 |
| candidates | idx_candidates_email_hash, idx_candidates_status, idx_candidates_tenant | ❌ 仅有@@unique([email, companyId]) |
| matches | idx_matches_position, idx_matches_candidate, idx_matches_status, idx_matches_score(DESC) | ❌ 无 |
| interviews | 6个索引 | ❌ 表不存在 |
| resumes | idx_resumes_candidate, idx_resumes_position, idx_resumes_parse, idx_resumes_tenant | ❌ 无 |
| offers | 3个索引 | ❌ 表不存在 |
| conflict_resolutions | 2个索引（含部分索引） | ❌ 表不存在 |

### 1.5 现有但PRD中不存在的模型

| 当前Schema模型 | PRD中是否有对应 | 建议 |
|---------------|-----------------|------|
| `Company` | PRD用`tenants`替代 | 迁移时映射Company→tenants |
| `Tag` + `CandidateTag` | PRD无对应（使用profile JSONB内的skills/keywords） | 评估是否保留或迁移到JSONB |
| `AiProfile` | PRD中画像数据直接存在candidates.profile字段 | 合并AiProfile→candidates.profile |
| `AiInference` | PRD无对应独立表 | 评估是否合并到ai_decisions |
| `JobEmbedding` | PRD用positions.embedding_id关联 | 迁移时需重新设计向量存储 |
| `CandidateEmbedding` | PRD用candidates.embedding_id关联 | 迁移时需重新设计向量存储 |

---

## 2. 向量检索方案审计

### 2.1 当前状态

```prisma
// 当前 schema.prisma 中的向量实现
model JobEmbedding {
  embedding Unsupported("Vector")? // pgvector占位
}
model CandidateEmbedding {
  embedding Unsupported("Vector")?
}
```

**问题**：
- `Unsupported("Vector")` 仅是类型占位，Prisma无法执行向量检索（无 `$queryRaw` 的 pgvector 操作符支持）
- 缺少维度声明（PRD要求1536维，text-embedding-3-large经降维）
- 缺少 HNSW 索引（PRD V3.2明确要求pgvectorscale + HNSW）
- 向量存储在独立表中，PRD设计是在主表中用 `embedding_id` 关联

### 2.2 PRD要求的向量架构

```
PostgreSQL 17 + pgvector + pgvectorscale
├── positions.embedding_id → 关联pgvector中的向量行
├── candidates.embedding_id → 关联pgvector中的向量行
├── HNSW索引（余弦距离）
├── 混合检索RRF（向量+关键词+结构化过滤）
├── 增量更新（JD字段修改时）+ 全量重建（模型升级时）
└── 1536维 Embedding（text-embedding-3-large降维）
```

### 2.3 Prisma不支持pgvector的替代方案

**方案A：Prisma + 原生SQL（混合方案，推荐过渡期）**

```typescript
// 使用 Prisma $queryRawUnsafe 执行向量操作
const results = await prisma.$queryRawUnsafe(`
  SELECT id, title, 1 - (embedding <=> $1::vector) as similarity
  FROM position_embeddings
  WHERE tenant_id = $2
  ORDER BY embedding <=> $1::vector
  LIMIT 20
`, queryVector, tenantId);
```

- 优点：保持Prisma生态，改动最小
- 缺点：无法利用pgvectorscale高级特性，手动管理向量索引

**方案B：SQLAlchemy + pgvector-python（PRD目标方案）**

```python
# models/position.py
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Position(Base):
    __tablename__ = 'positions'
    id = Column(UUID, primary_key=True)
    embedding = Column(Vector(1536))  # 直接存储向量
    # ...
    
# 查询
from sqlalchemy import text
results = session.query(Position).order_by(
    Position.embedding.cosine_distance(query_vector)
).limit(20).all()
```

- 优点：PRD目标架构，pgvector/pgvectorscale原生支持
- 缺点：需完整ORM迁移（Prisma→SQLAlchemy）

**方案C：双ORM共存（过渡方案）**

- Prisma管理非向量CRUD，SQLAlchemy管理向量操作
- 共享同一个PostgreSQL数据库
- 适合逐步迁移

### 2.4 修复建议

| 优先级 | 动作 | 说明 |
|--------|------|------|
| P0 | 安装 pgvector + pgvectorscale 扩展 | `CREATE EXTENSION vector; CREATE EXTENSION vectorscale;` |
| P0 | 创建 position_embeddings 和 candidate_embeddings 原生SQL表 | 使用HNSW索引 |
| P0 | 切换到方案B（SQLAlchemy） | PRD架构目标，FastAPI天然支持 |
| P1 | 实现混合检索RRF | 向量+关键词+结构化过滤融合 |
| P1 | 实现向量全量重建ARQ异步任务 | `POST /api/v1/positions/rebuild-vectors` |

---

## 3. 对象存储方案审计

### 3.1 当前状态

- Resume模型中 `fileUrl` 注释为 "Supabase Storage URL"
- `.env` 文件中无Supabase配置（仅有占位 `DATABASE_URL`）
- 无MinIO/S3相关配置
- 无docker-compose定义MinIO服务

### 3.2 PRD要求的MinIO存储架构

```
MinIO 对象存储
├── 简历文件桶 (resumes/)
│   ├── {tenant_id}/{candidate_id}/{resume_id}.pdf
│   └── 加密桶（AES-256服务端加密）
├── 面试录音桶 (recordings/)
│   ├── {tenant_id}/{interview_id}/audio.webm
│   └── 30天自动删除策略
├── 入职材料桶 (onboarding/)
│   ├── contracts/{offer_id}/labor_contract.pdf
│   └── materials/{offer_id}/id_card.jpg
├── Offer附件桶 (offers/)
│   └── {tenant_id}/{offer_id}/offer_letter.pdf
└── 访问方式：签名URL（7天有效期，不暴露存储路径）
```

### 3.3 MinIO vs S3 选型分析

| 维度 | MinIO | AWS S3 / 阿里云 OSS |
|------|-------|---------------------|
| 部署模式 | 自部署（Docker） | 云服务 |
| 数据主权 | 100%本地控制 | 数据在云上 |
| 成本 | 仅服务器成本 | 按存储+请求计费 |
| S3兼容 | S3 API兼容 | 原生S3 |
| 适用场景 | 开发/测试/私有化部署 | 生产环境/大规模 |
| PRD要求 | **MinIO（开发+私有化）** | S3兼容API（生产可切） |

**建议**：使用MinIO作为默认（S3 API兼容），生产环境可无缝切换到S3/OSS。

### 3.4 修复建议

| 优先级 | 动作 | 说明 |
|--------|------|------|
| P0 | 添加MinIO到docker-compose | 端口9000/9001 |
| P0 | 实现存储Service层 | `storage_service.py`（上传/下载/签名URL/删除） |
| P0 | 修改resumes.file_url指向MinIO路径 | 替换Supabase引用 |
| P1 | 实现面试录音上传 | interviews.recording_url → MinIO |
| P1 | 实现入职材料上传 | onboarding_tasks.checklist_data.file_url → MinIO |
| P2 | 实现自动删除策略 | 录音30天自动清理（Cron任务） |

---

## 4. 缓存策略审计

### 4.1 当前状态

**完全无Redis集成**。package.json中无Redis客户端依赖，无Redis配置。

### 4.2 PRD要求的Redis使用场景

#### 场景1：会话缓存

```
Key: session:{session_id}
Value: {tenant_id, user_id, role, permissions, preferences}
TTL: 24h（滑动过期）
用途：Agent会话上下文、用户登录态
```

#### 场景2：热查询缓存

| 缓存项 | Key模式 | TTL | 说明 |
|--------|---------|-----|------|
| Dashboard数据 | `dashboard:{tenant_id}` | 5min | 待办/指标/日程 |
| 岗位列表 | `positions:{tenant_id}:*` | 10min | 热门岗位查询 |
| 候选人画像 | `candidate:profile:{id}` | 15min | 频繁访问的画像数据 |
| 匹配结果 | `match:result:{position_id}:{candidate_id}` | 30min | 避免重复计算 |
| JD生成缓存 | `jd:cache:{jd_hash}` | 24h | LRU 1000条，相似JD命中直接返回 |
| 技能标准化 | `skill:normalize:{raw_skill}` | 永久 | 技能名归一结果 |

#### 场景3：限流

| 场景 | Key模式 | 算法 | 限制 |
|------|---------|------|------|
| API速率限制 | `ratelimit:api:{tenant_id}:{user_id}` | 滑动窗口 | 100 req/min |
| AI调用计量 | `ai:quota:{tenant_id}:{yyyy-mm}` | 计数器 | 免费版200次/月 |
| 面试反馈Token | `feedback:rate:{token_id}` | 计数器 | 5min内3次 |
| Token黑名单 | `feedback:used:{token_id}` | SET | TTL=Token有效期 |
| IM审批OTP | `otp:approval:{user_id}` | TTL | 5min有效 |

#### 场景4：分布式锁

```
Key: lock:vector_rebuild:{tenant_id}
用途：全量向量重建互斥，防止并发重建
TTL: 30min（安全过期）
```

### 4.3 修复建议

| 优先级 | 动作 | 说明 |
|--------|------|------|
| P0 | 添加Redis到docker-compose | redis:7-alpine |
| P0 | 实现Redis连接池 | FastAPI lifespan中初始化 |
| P0 | 实现限流中间件 | API + AI调用限流 |
| P1 | 实现热查询缓存层 | Service层透明缓存 |
| P1 | 实现JD生成缓存 | LRU + 30天去重 |
| P2 | 实现分布式锁 | 向量重建等互斥操作 |

---

## 5. 审计日志审计

### 5.1 当前状态

**完全缺失**。无审计日志表、无操作记录机制。

### 5.2 PRD要求的审计体系

#### 5.2.1 操作审计（audit_log概念，PRD §8.1中间件层）

PRD §8.1架构图中明确列出"审计日志"作为FastAPI统一中间件的一部分：
> 统一中间件：JWT认证 + RBAC权限 + 参数校验(Pydantic) + **审计日志** + SSE流支持

**记录内容**：
- 操作人（user_id + tenant_id）
- 操作时间（timestamp）
- 操作类型（CREATE/UPDATE/DELETE/READ）
- 操作对象（entity_type + entity_id）
- 变更前后数据（old_value/new_value，PII脱敏）
- 调用来源（source: fastapi/tool）
- IP + User-Agent

#### 5.2.2 AI决策审计（ai_decisions表，PRD §7.8a）

```sql
CREATE TABLE ai_decisions (
    id              UUID PRIMARY KEY,
    session_id      UUID,               -- Agent会话
    decision_type   VARCHAR(50) NOT NULL, -- match/score/recommend/parse/generate_jd/...
    input_summary   JSONB,              -- 脱敏输入
    output_summary  JSONB,              -- 脱敏输出
    model           VARCHAR(50) NOT NULL, -- gpt-4.1/gpt-4.1-mini
    prompt_version  VARCHAR(32) NOT NULL, -- generate_jd_v2
    token_usage     JSONB,              -- {prompt, completion, total}
    latency_ms      INTEGER,
    tenant_id       UUID NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
-- 索引：(tenant_id, decision_type, created_at) + (session_id)
-- 保留期限：雇佣关系终止后2年
```

#### 5.2.3 画像变更溯源（profile_updates表，PRD §7.7a）

记录候选人画像每次字段级变更的完整溯源链。

#### 5.2.4 合规要求

- 《个保法》第24条：自动化决策透明度
- 《劳动争议调解仲裁法》第27条：AI决策记录保留2年
- PRD §5.7：LLM数据脱敏Pipeline

### 5.3 修复建议

| 优先级 | 动作 | 说明 |
|--------|------|------|
| P0 | 创建 `audit_logs` 表 | 通用操作审计，FastAPI中间件自动写入 |
| P0 | 创建 `ai_decisions` 表 | AI决策审计，Service层LLM调用后自动写入 |
| P1 | 创建 `profile_updates` 表 | 画像变更溯源 |
| P1 | 实现FastAPI审计中间件 | AOP装饰器自动拦截 |
| P2 | 实现审计报告导出 | CSV格式，支持按时间/操作人/实体筛选 |
| P2 | 实现审计数据保留策略 | 自动归档（90天+）和清理 |

---

## 6. SSE实时推送审计

### 6.1 当前状态

**完全缺失**。无SSE端点、无事件推送机制。

### 6.2 PRD要求的SSE场景

#### 6.2.1 推送事件清单

| 事件类型 | 触发条件 | 推送目标 | 优先级 |
|---------|---------|---------|--------|
| 匹配完成 | `matches`评分计算完成 | HR（岗位负责人） | P0 |
| 简历解析完成 | `resumes.parse_status` → completed | 上传者HR | P0 |
| 面试状态变更 | `interviews.status` 变更 | 相关面试官+HR | P0 |
| Offer审批通知 | `offers.status` → pending_approval | 审批人 | P1 |
| AI任务进度 | ARQ异步任务进度更新 | 发起者 | P1 |
| Dashboard刷新 | 新数据/待办变化 | Dashboard页面 | P2 |
| 候选人状态变更 | `candidates.status` 变更 | HR | P2 |

#### 6.2.2 SSE认证方案（P1-34修复）

```
认证方式：Header传递一次性Token
1. 客户端先调 GET /api/v1/sse/token → 获取5分钟一次性SSE Token
2. 连接SSE：GET /api/v1/sse/stream?token={sse_token}
3. Token验证通过 → 建立 EventSource 连接
4. 降级方案：若Header方式失败 → 降级到query参数（5分钟Token自动过期）
```

#### 6.2.3 数据流架构

```
业务事件 → Redis Pub/Sub → SSE Gateway → 客户端
                         ↓
                   事件持久化（可选，审计用）

Key设计：
  Publish: sse:events:{tenant_id}:{user_id}
  Subscribe: sse:subscribe:{user_id}（SSE Gateway订阅）
```

### 6.3 修复建议

| 优先级 | 动作 | 说明 |
|--------|------|------|
| P0 | 实现SSE Token端点 | `GET /api/v1/sse/token` |
| P0 | 实现SSE流端点 | `GET /api/v1/sse/stream` |
| P0 | 实现Redis Pub/Sub事件总线 | Service层事件发布 |
| P1 | 业务事件接入 | 匹配/解析/面试/Offer |
| P2 | 重连机制 | Last-Event-ID + 事件回放 |

---

## 7. 数据迁移策略（Prisma → SQLAlchemy）

### 7.1 迁移背景

PRD V3.6架构明确要求：
- **后端**：FastAPI（Python）+ SQLAlchemy + Alembic
- **前端**：Vue 3（hermes-web-ui Fork），非当前Next.js

当前实现：
- **全栈**：Next.js + Prisma（TypeScript）
- **偏离度**：技术栈与PRD完全不匹配

### 7.2 迁移路线图

#### Phase 0：基线确认（1天）

```bash
# 导出当前Prisma migrate状态
npx prisma migrate diff \
  --from-empty \
  --to-schema-datamodel prisma/schema.prisma \
  --script > prisma_baseline.sql
```

#### Phase 1：SQLAlchemy模型构建（3-5天）

1. 按PRD §7.2-7.7a DDL创建SQLAlchemy模型
2. 使用Alembic生成初始migration
3. 不直接映射当前Prisma模型，而是直接按PRD DDL构建

```python
# 目标结构
models/
├── __init__.py
├── base.py          # Base, engine, session
├── tenant.py        # Tenant
├── user.py          # User
├── department.py    # Department
├── position.py      # Position（含pgvector）
├── candidate.py     # Candidate（含加密字段）
├── resume.py        # Resume
├── interview.py     # Interview
├── match.py         # Match
├── offer.py         # Offer
├── onboarding.py    # OnboardingTask
├── ai_decision.py   # AiDecision
├── audit_log.py     # AuditLog
├── consent.py       # ConsentRecord
└── share_link.py    # ShareLink

alembic/
├── env.py
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_pgvector_extension.py
│   └── 003_indexes_and_constraints.py
```

#### Phase 2：数据迁移脚本（2-3天）

```python
# scripts/migrate_prisma_to_sqlalchemy.py
"""
迁移策略：
1. Prisma导出 → JSON/CSV 中间格式
2. 数据清洗（PII加密、类型转换）
3. SQLAlchemy批量导入
4. 校验一致性
"""

async def migrate_candidates():
    # 1. 读取Prisma数据
    prisma_candidates = await prisma.candidate.find_many()
    
    # 2. 转换并加密
    for c in prisma_candidates:
        sa_candidate = Candidate(
            id=c.id,
            email=encrypt_aes256(c.email),      # 明文→密文
            email_hash=hash_sha256(c.email),     # 新增hash字段
            phone=encrypt_aes256(c.phone),
            phone_hash=hash_sha256(c.phone),
            name_encrypted=encrypt_aes256(c.name),
            name_hash=hash_sha256(c.name),
            tenant_id=default_tenant_id,         # 映射companyId→tenantId
            status='active',
            profile={},                           # 从AiProfile迁移
            # ...
        )
        session.add(sa_candidate)
    
    # 3. 批量提交
    await session.commit()
```

#### Phase 3：向量迁移（1-2天）

```python
# 重新生成所有向量（不迁移旧向量）
async def rebuild_all_vectors():
    positions = session.query(Position).filter(Position.status == 'open').all()
    for p in positions:
        embedding = await generate_embedding(p.jd_text)
        # 写入pgvector（SQLAlchemy + pgvector-python）
        p.embedding = embedding
    await session.commit()
```

#### Phase 4：切换与回退（1天）

```
切换策略：
1. 双写模式（Prisma + SQLAlchemy同时写入，3天验证）
2. 读切换（API读从SQLAlchemy）
3. 写切换（API写从SQLAlchemy）
4. Prisma只读模式（保留1周）
5. Prisma下线

回退方案：
- 任何阶段失败 → 切回Prisma
- 数据不一致 → 从PostgreSQL备份恢复
```

### 7.3 迁移风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 数据类型不兼容（cuid→UUID） | FK关联断裂 | 映射表 + 渐进迁移 |
| PII加密迁移 | 数据不可逆 | 先迁移后加密，批量加密脚本 |
| 向量维度变化 | 匹配失效 | 全量重建向量（ARQ异步任务） |
| 枚举值不一致 | 状态机混乱 | 映射函数 + 数据清洗 |
| 停机时间 | 业务中断 | 蓝绿部署 + 双写过渡 |

### 7.4 时间估算

| 阶段 | 工时 | 累计 |
|------|------|------|
| Phase 0 基线 | 1天 | 1天 |
| Phase 1 SA模型 | 3-5天 | 4-6天 |
| Phase 2 数据迁移 | 2-3天 | 6-9天 |
| Phase 3 向量迁移 | 1-2天 | 7-11天 |
| Phase 4 切换 | 1天 | 8-12天 |
| **总计** | **8-12个工作日** | |

---

## 8. 差距优先级汇总

### P0（阻塞M1里程碑，必须立即修复）

| # | 差距 | 预估工时 |
|---|------|---------|
| 1 | 创建SQLAlchemy项目骨架（FastAPI + Alembic） | 2天 |
| 2 | 按PRD DDL创建5大核心表（positions/candidates/resumes/interviews/matches） | 3天 |
| 3 | 创建tenants + departments + users表 | 1天 |
| 4 | 安装pgvector/pgvectorscale扩展 | 0.5天 |
| 5 | 创建向量存储表 + HNSW索引 | 1天 |
| 6 | 添加MinIO到docker-compose | 0.5天 |
| 7 | 添加Redis到docker-compose | 0.5天 |
| 8 | 创建offers + onboarding_tasks表 | 1天 |
| **P0总计** | | **约9.5天** |

### P1（M2-M3里程碑前完成）

| # | 差距 | 预估工时 |
|---|------|---------|
| 1 | 创建evaluation_templates表 | 0.5天 |
| 2 | 创建channels表 | 0.5天 |
| 3 | 创建ai_decisions + audit_logs表 | 1天 |
| 4 | 创建profile_updates + conflict_resolutions表 | 1天 |
| 5 | 创建consent_records + share_links + match_feedback表 | 1天 |
| 6 | 实现Redis缓存层（热查询+JD缓存） | 2天 |
| 7 | 实现Redis限流中间件 | 1天 |
| 8 | 实现SSE推送基础设施 | 2天 |
| 9 | 实现MinIO存储Service | 1天 |
| 10 | 实现FastAPI审计中间件 | 1天 |
| 11 | PII字段加密（AES-256） | 2天 |
| **P1总计** | | **约13天** |

### P2（V1.0-M4后逐步完善）

- 剩余扩展实体（interviewer_profiles/referrers/headhunter_agencies等）
- 分布式锁（Redis）
- 向量全量重建ARQ任务
- 审计报告导出
- 自动删除策略（录音30天）
- AI记忆系统表（三层记忆）

---

## 9. 架构决策记录

| # | 决策 | 理由 | 影响范围 |
|---|------|------|---------|
| ADR-001 | ORM从Prisma迁移到SQLAlchemy | PRD目标架构为FastAPI(Python) + SQLAlchemy，Prisma(Node.js)不兼容pgvector高级特性 | 全部数据层 |
| ADR-002 | 前端从Next.js迁移到Vue 3 | PRD明确"基于hermes-web-ui Fork扩展（路线B）"，Vue 3 + Naive UI | 前端+API层 |
| ADR-003 | 对象存储选用MinIO | S3 API兼容+自部署+数据不出境，生产可切S3/OSS | 文件存储层 |
| ADR-004 | 向量方案pgvector+pgvectorscale | PRD V3.2技术选型裁决，PG17原生支持 | 向量检索层 |
| ADR-005 | 缓存选用Redis | PRD §8.1架构图明确列出Redis，会话+缓存+限流+Pub/Sub | 缓存层 |
| ADR-006 | PII加密采用AES-256-GCM | 个保法§51条数据分类分级，L3级敏感数据 | 全部含PII表 |

---

## 附录A：PRD DDL完整表清单

| # | 表名 | PRD章节 | 类型 |
|---|------|---------|------|
| 1 | tenants | §7.7a | D2组织实体 |
| 2 | users | §7.7a | A类角色 |
| 3 | departments | §7.7a | D1组织实体 |
| 4 | positions | §7.2.1 | 核心实体 |
| 5 | candidates | §7.2.3 | 核心实体 |
| 6 | resumes | §7.2.2 | 核心实体 |
| 7 | interviews | §7.2.4 | 核心实体 |
| 8 | matches | §7.2.5 | 核心实体 |
| 9 | offers | §7.7a | B2业务实体 |
| 10 | onboarding_tasks | §7.7a | P0-09 |
| 11 | evaluation_templates | §7.7a | B4业务实体 |
| 12 | channels | §7.7a | C3流程实体 |
| 13 | profile_updates | §7.7a | 溯源 |
| 14 | conflict_resolutions | §7.2.3 | 冲突处理 |
| 15 | match_feedback | §7.7a | 反馈 |
| 16 | share_links | §7.7a | 共享 |
| 17 | ai_decisions | §7.8a | AI审计 |
| 18 | consent_records | §3.8 | 合规 |
| 19 | audit_logs | §8.1(中间件) | 操作审计（需新建） |

> **注**：audit_logs表PRD未给出DDL，但§8.1架构图明确要求审计日志中间件。需数据架构师补充DDL设计。

---

*报告完毕。核心结论：当前数据层与PRD V3.6目标存在系统性差距，需按上述优先级进行完整重建。建议M0预开发基建阶段（PRD §13）优先完成P0项。*
