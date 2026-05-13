# 数据库Schema定义

> PRD来源：§7.2-§7.10, §11.1a, §3.8
> 最后更新：2026-05-12

---

## 核心实体（5张）

### positions — 岗位画像

```sql
-- 来源：§7.2.1
CREATE TABLE positions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id         UUID NOT NULL REFERENCES departments(id),
    title                 VARCHAR(200) NOT NULL,                  -- 岗位名称
    status                VARCHAR(20) NOT NULL DEFAULT 'draft'
                          CHECK(status IN ('draft','open','paused','closed','filled')),
    required_skills       JSONB DEFAULT '[]',                     -- 必备技能 [{skill, weight, required/bonus}]
    required_exp_min      INT,                                    -- 最低经验年限
    required_exp_max      INT,                                    -- 最高经验年限
    salary_min            NUMERIC(12,2),                          -- 【P0-01说明】岗位预算属L2公开信息，不需加密（非候选人PII，是组织内部岗位配置数据）
    salary_max            NUMERIC(12,2),                          -- 【P0-01说明】岗位预算属L2公开信息，不需加密（非候选人PII，是组织内部岗位配置数据）
    salary_currency       VARCHAR(3) DEFAULT 'CNY',
    profile_summary       TEXT,                                   -- 岗位画像摘要
    profile_keywords      JSONB DEFAULT '[]',                     -- 关键词标签
    jd_text               TEXT,                                   -- JD原文
    headcount             INT DEFAULT 1,                          -- 招聘人数
    filled_count          INT DEFAULT 0,                          -- 已入职人数
    priority              VARCHAR(10) DEFAULT 'normal'
                          CHECK(priority IN ('urgent','high','normal','low')),
    embedding_id          VARCHAR(255),                           -- pgvector向量行ID
    published_at          TIMESTAMPTZ,                            -- 发布时间
    closed_at             TIMESTAMPTZ,                            -- 关闭时间
    created_by            UUID NOT NULL REFERENCES users(id),
    tenant_id             UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',  -- 多租户隔离；Phase 1用默认值，Phase 2切换为真实租户ID
    version               INTEGER NOT NULL DEFAULT 1,             -- 乐观锁版本号（V3.5并发控制）
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_positions_department ON positions(department_id);
CREATE INDEX idx_positions_status     ON positions(status);
CREATE INDEX idx_positions_tenant     ON positions(tenant_id);
COMMENT ON TABLE positions IS '岗位画像——结构化能力需求模型，draft→filled全生命周期';
```

**实体定义**（§7.2.1）：

| 维度 | 说明 |
|------|------|
| **定义** | 有生命周期的结构化能力需求模型 |
| **核心字段** | `title`, `required_skills[]`, `required_exp_min/max`, `salary_range`, `profile_keywords[]`, `profile_summary` |
| **生命周期** | `draft → open → paused → closed → filled` |
| **可演进** | 面试反馈可能导致岗位要求调整（`updated_at`自动更新） |
| **向量化** | 发布时生成向量进入pgvector匹配池 |
| **向量重建策略** | 增量更新（JD字段修改时）+ 全量重建（Embedding模型升级/季度质量修复/岗位需求大幅调整时触发）。全量重建通过 `POST /api/v1/positions/rebuild-vectors` 批量触发，ARQ异步任务执行（§8.1c） |

---

### candidates — 人才画像

```sql
-- 来源：§7.2.3
CREATE TABLE candidates (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 VARCHAR(255),                           -- AES-256加密存储（密文），去重使用email_hash字段，不再使用UNIQUE约束
    phone_hash            VARCHAR(64) NOT NULL,                   -- 手机号SHA256哈希（去重键之一）
    email_hash            VARCHAR(64) NOT NULL,                   -- 邮箱SHA256哈希（去重键之二）
    phone                 VARCHAR(255),                           -- AES-256加密存储
    name_encrypted        VARCHAR(512),                           -- AES-256加密存储（L3敏感数据），展示时解密name_encrypted
    name_hash             VARCHAR(64),                            -- 姓名SHA256哈希（用于模糊匹配去重）
    profile               JSONB DEFAULT '{}',                     -- 画像核心数据，7类子结构
    source_refs           JSONB DEFAULT '[]',                     -- 全局溯源索引
    credibility_score     FLOAT DEFAULT 0 CHECK(credibility_score BETWEEN 0 AND 100),
    credibility_grade     CHAR(1) CHECK(credibility_grade IN ('A','B','C','D')),
    inference_data        JSONB DEFAULT '{}',                     -- AI推理结果
    embedding_id          VARCHAR(255),                           -- pgvector向量行ID
    status                VARCHAR(20) DEFAULT 'active'
                          CHECK(status IN ('active','inactive','blacklisted','onboarded')),
    tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,  -- 多租户隔离
    version               INTEGER NOT NULL DEFAULT 1,             -- 乐观锁版本号（V3.5并发控制）
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_candidate_identity UNIQUE (phone_hash, email_hash)
);
CREATE INDEX idx_candidates_email_hash ON candidates(email_hash);  -- 去重查询使用email_hash索引替代原email明文索引
CREATE INDEX idx_candidates_status   ON candidates(status);
CREATE INDEX idx_candidates_tenant   ON candidates(tenant_id);
COMMENT ON TABLE candidates IS '人才画像——组织对候选人的多维能力模型，匹配决策唯一依据';
COMMENT ON COLUMN candidates.email IS 'AES-256加密存储（密文），与phone字段同模式；去重查询使用email_hash字段（SHA256），不在此列建立UNIQUE约束';
COMMENT ON COLUMN candidates.email_hash IS '邮箱SHA256哈希，用于去重查询和UNIQUE组合约束（与phone_hash组合），原邮箱明文不参与去重';
```

**实体定义**（§7.2.3）：

| 维度 | 说明 |
|------|------|
| **定义** | 组织的累积认知，唯一匹配决策实体 |
| **创作者** | 组织（多源数据融合） |
| **基数** | 一个人 → 一个画像（UNIQUE by phone_hash + email_hash 组合约束） |
| **数据源** | 简历 + 面试反馈 + 技能评估 + HR手动标注 |
| **时效性** | 持续演进（入职后继续更新绩效/晋升数据） |
| **冷启动** | 首次投递无画像时，用简历向量做初始筛选，5-15分钟异步构建画像后切换 |
| **向量策略** | 增量更新（新数据）+ 全量重建（模型升级/季度修复）。统一触发条件：①Embedding模型版本变更 ②季度向量质量审计发现漂移 ③管理员手动触发。全量重建通过ARQ异步任务执行（§8.1c） |

**字段级定义**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 主键 |
| `email` | VARCHAR(255) | AES-256加密存储（与phone同模式），去重使用email_hash字段 |
| `phone` | VARCHAR(255) | AES-256加密存储，解密需权限 |
| `name_encrypted` | VARCHAR(512) | 候选人姓名AES-256加密存储（L3敏感数据，§11.2），展示时解密name_encrypted |
| `profile` | JSONB | 画像核心数据，7类子结构：`basic_info`（基本信息）、`education`（教育背景）、`work_experience`（工作经历）、`skills`（技能列表）、`certifications`（证书）、`projects`（项目经历）、`preferences`（求职偏好） |
| `source_refs` | JSONB | 全局溯源索引，schema：`{field_path: STRING, sources: [{type: ENUM("resume"|"interview"|"assessment"|"hr_manual"), id: UUID, page: INT, para: INT, confidence: FLOAT, updated_at: TIMESTAMP}]}` |
| `credibility_score` | FLOAT | 画像可信度评分（0-100），基于数据源数量、交叉验证率、时效性综合计算 |
| `credibility_grade` | ENUM | 可信度等级：`A`（≥80）、`B`（≥60）、`C`（≥40）、`D`（<40） |
| `inference_data` | JSONB | AI推理结果，schema：`{inferred_skills: [{skill, confidence, evidence}], potential_fields: [{field, reasoning}], risk_factors: [{factor, level, description}]}` |
| `embedding_id` | VARCHAR(255) | pgvector中的向量行ID，关联画像向量 |
| `tenant_id` | UUID FK | 租户ID（多租户隔离） |
| `status` | ENUM | 候选人状态：`active`/`inactive`/`blacklisted`/`onboarded` |

> **P2-16级联约束**：`credibility_grade`随`credibility_score`自动更新，由应用层触发（非DB触发器）。规则：score≥80→grade='A'，score≥60→grade='B'，score≥40→grade='C'，score<40→grade='D'。DDL的CHECK约束仅作数据完整性兜底。

**credibility_score 算法**：

```
基础分 base = 100

数据源加权（source_weight × source_completeness）：
  简历数据     weight=1.0  completeness=已填充字段数/总字段数
  面试反馈     weight=0.8  completeness=已评维度数/总维度数
  背调数据     weight=1.2  completeness=已验证项数/待验证项数
  AI推理数据   weight=0.3  completeness=推理结果数/潜在推理项数

惩罚项（penalties）：
  数据冲突     每处 -5分（来自conflict_resolutions表未裁决记录）
  过期数据     >6月未更新 -10分（基于updated_at计算）
  单源数据     仅有简历无其他数据源 -15分

公式：
  score = min(100, base + Σ(source_weight × source_completeness × 100) - penalties)

分级（与DDL CHECK约束一致）：
  A级（≥90）   高可信：多源交叉验证，数据完整且新鲜
  B级（≥70）   良好：至少2个数据源，少量冲突或过期
  C级（≥50）   一般：数据源单一或存在多处冲突
  D级（<50）   低可信：严重冲突或数据严重过期，需重点验证
  
  注：边界值属于高级别（如70.0归入B级）
```

---

### matches — 匹配记录

```sql
-- 来源：§7.2.5
CREATE TABLE matches (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id           UUID NOT NULL REFERENCES positions(id),
    candidate_id          UUID NOT NULL REFERENCES candidates(id),
    status                VARCHAR(20) NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','screening','shortlisted','interview_scheduled',
                                           'interviewed','offered','hired','rejected','withdrawn')),
    overall_score         FLOAT CHECK(overall_score BETWEEN 0 AND 100),
    skill_score           FLOAT,                                  -- 技能匹配分
    experience_score      FLOAT,                                  -- 经验匹配分
    education_score       FLOAT,                                  -- 教育匹配分
    inference_score       FLOAT,                                  -- AI推理增量分
    score_breakdown       JSONB DEFAULT '{}',                     -- 分项评分详情
    match_details         JSONB DEFAULT '{}',                     -- 匹配分析详情（优势/差距/建议）
    candidate_feedback    JSONB DEFAULT '{}',                     -- 候选人反馈（如拒Offer原因）
    salary_score          DECIMAL(5,4),                           -- 薪资匹配分
    initiated_by          VARCHAR(20) DEFAULT 'system'
                          CHECK(initiated_by IN ('system','candidate','hr')),
    vector_similarity     FLOAT,                                  -- 向量余弦相似度
    matched_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_match UNIQUE (position_id, candidate_id)
);
CREATE INDEX idx_matches_position  ON matches(position_id);
CREATE INDEX idx_matches_candidate ON matches(candidate_id);
CREATE INDEX idx_matches_status    ON matches(status);
CREATE INDEX idx_matches_score     ON matches(overall_score DESC);
COMMENT ON TABLE matches IS '核心关系——岗位vs候选人的匹配评估，支持双向匹配';
```

**实体定义**（§7.2.5）：

| 维度 | 说明 |
|------|------|
| **定义** | 对称关系，一次匹配=一行记录 |
| **对称设计** | `UNIQUE(position_id, candidate_id)` |
| **发起方向** | `initiated_by`枚举（`system`/`candidate`/`hr`，以DDL CHECK为准） |
| **分维评分** | `skill_score` + `experience_score` + `salary_score` + `overall_score` + `inference_score`（推理增强评分） |
| **推理增强评分** | `score_breakdown` JSONB中额外存储：`inferred_overall`（推理增强总分）、`inference_contributions[]`（各推理贡献项）、`inference_delta`（推理增强分差） |
| **生命周期** | 非线性有向图：`pending→shortlisted⇄interviewing→offered⇄counter_offered→hired→onboarded`；`shortlisted/interviewing/offered`均可→`rejected`；所有状态均可→`withdrawn`；任意非终态→`cancelled` |

---

### interviews — 面试记录

```sql
-- 来源：§7.2.4
CREATE TABLE interviews (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id           UUID NOT NULL REFERENCES positions(id),
    candidate_id          UUID NOT NULL REFERENCES candidates(id),
    match_id              UUID REFERENCES matches(id),
    round                 INT NOT NULL DEFAULT 1,                 -- 面试轮次
    interview_type        VARCHAR(20) DEFAULT 'onsite'
                          CHECK(interview_type IN ('phone','video','onsite','group','panel')),
    status                VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                          CHECK(status IN ('scheduled','in_progress','completed','cancelled','no_show')),
    scheduled_at          TIMESTAMPTZ NOT NULL,                   -- 面试时间
    duration_minutes      INT DEFAULT 60,
    location              TEXT,                                   -- 地点/会议链接
    interviewer_ids       UUID[] DEFAULT '{}',                    -- 面试官ID列表
    feedback_tokens       JSONB DEFAULT '[]',                    -- 多面试官反馈Token数组，每项含{interviewer_id, token, expires_at}，JWT格式，24h有效
    transcript_text       TEXT,                                   -- 录音转写文本（faster-whisper生成）
    transcript_status     VARCHAR(20) DEFAULT 'none'
                          CHECK(transcript_status IN ('none','processing','completed','failed')),
    analysis_result       JSONB,                                  -- LLM多维分析结果（原始输出）
    decision              VARCHAR(20)
                          CHECK(decision IN ('advance','reject','hold','offer')),
    decision_reason       TEXT,                                   -- 决策理由
    stage                 VARCHAR(20) NOT NULL DEFAULT 'screening'
                          CHECK(stage IN ('screening','technical','behavioral','final','offer')),
    briefing_data         JSONB,                                  -- AI结构化考察清单（必考/验证/确认/探测四类）
    recording_url         VARCHAR(500),                           -- 面试录音/视频文件路径（MinIO存储）
    ai_analysis           JSONB,                                  -- AI面试分析报告 {strengths[], concerns[], recommendations[], score:float}
    overall_rating        FLOAT CHECK(overall_rating BETWEEN 0 AND 5),
    notes                 TEXT,                                   -- HR备注
    version               INTEGER NOT NULL DEFAULT 1,             -- 乐观锁版本号（V3.5并发控制）
    created_by            UUID NOT NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_interviews_position   ON interviews(position_id);
CREATE INDEX idx_interviews_candidate  ON interviews(candidate_id);
CREATE INDEX idx_interviews_status     ON interviews(status);
CREATE INDEX idx_interviews_scheduled  ON interviews(scheduled_at);
CREATE INDEX idx_interviews_decision   ON interviews(decision) WHERE decision IS NOT NULL;
CREATE INDEX idx_interviews_stage      ON interviews(stage);
COMMENT ON TABLE interviews IS '面试记录——覆盖scheduled→completed全流程，含决策/阶段/考察清单/录音转写和LLM分析';
```

**实体定义**（§7.2.4）：

| 维度 | 说明 |
|------|------|
| **定义** | 双向数据生成器，同时验证岗位定义和人才画像 |
| **双FK** | 必须同时关联`position_id`和`candidate_id` |
| **多轮次** | `round`(INT) + `stage`(VARCHAR+CHECK: screening→technical→behavioral→final→offer) |
| **双向更新** | 方向1：反馈→画像更新；方向2：连续失败信号→岗位修正 |
| **决策字段** | `decision`(VARCHAR+CHECK: advance/reject/hold/offer) + `decision_reason`(TEXT) |
| **AI考察清单** | `briefing_data` JSONB — AI生成的结构化考察清单（必考/验证/确认/探测四类） |
| **转写文本** | `transcript_text` TEXT — faster-whisper生成 |
| **录音文件** | `recording_url` VARCHAR(500) — MinIO存储 |
| **LLM原始分析** | `analysis_result` JSONB — LLM多维分析原始输出 |
| **AI分析报告** | `ai_analysis` JSONB — `{strengths: [], concerns: [], recommendations: [], score: float}` |

---

### resumes — 简历文件

```sql
-- 来源：§7.2.2
CREATE TABLE resumes (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id          UUID REFERENCES candidates(id),          -- 解析后关联候选人
    position_id           UUID REFERENCES positions(id),           -- 投递岗位
    file_url              VARCHAR(500) NOT NULL,                   -- MinIO文件路径
    file_name             VARCHAR(255) NOT NULL,
    file_type             VARCHAR(10) CHECK(file_type IN ('pdf','docx','doc','png','jpg','jpeg')),
    file_size             INT,                                     -- 文件大小(bytes)
    source                VARCHAR(20) DEFAULT 'upload'
                          CHECK(source IN ('upload','email','boss','referral','headhunter')),
    parse_status          VARCHAR(20) DEFAULT 'pending'
                          CHECK(parse_status IN ('pending','processing','completed','failed')),
    parsed_data           JSONB,                                   -- 解析结果（immutable，不可覆盖）
    source_refs           JSONB DEFAULT '[]',                      -- 字段溯源标注
    credibility           JSONB,                                   -- 可信度检测结果
    uploaded_by           UUID REFERENCES users(id),
    tenant_id             UUID,
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chk_resumes_candidate_after_parse CHECK(NOT (parse_status = 'completed' AND candidate_id IS NULL))
);
CREATE INDEX idx_resumes_candidate  ON resumes(candidate_id);
CREATE INDEX idx_resumes_position   ON resumes(position_id);
CREATE INDEX idx_resumes_parse      ON resumes(parse_status);
CREATE INDEX idx_resumes_tenant     ON resumes(tenant_id);
COMMENT ON TABLE resumes IS '简历文件——人才画像的数据源，parsed_data不可变审计追踪';
```

**实体定义**（§7.2.2）：

| 维度 | 说明 |
|------|------|
| **定义** | 人才画像的数据源，不是匹配决策的依据 |
| **创作者** | 候选人（自我报告，可能有水分） |
| **基数** | 一个人 → 多份简历（不同时间、不同平台） |
| **不可变性** | `parsed_data` JSONB字段永不覆盖（immutable audit trail） |
| **冲突处理** | 不同简历信息冲突时进入`profile_updates`表待人工审核 |
| **退居时机** | Offer阶段简历无决策价值，完全基于人才画像 |

---

## 扩展实体（§7.7a）

### tenants — 租户

```sql
-- 来源：§7.7a（P2-03补充）
-- Phase 1单租户运行，仅一条默认记录。Phase 2启用多租户隔离。
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,               -- 租户名称，如"智联科技有限公司"
    plan        VARCHAR(20) NOT NULL DEFAULT 'free' CHECK(plan IN ('free','pro','enterprise')),
    status      VARCHAR(20) NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended','cancelled')),
    created_at  TIMESTAMPTZ DEFAULT now()
);
COMMENT ON TABLE tenants IS 'D2-租户，多租户隔离边界，Phase 1单行数据';
-- Phase 1初始化数据：
-- INSERT INTO tenants (id, name, plan, status) VALUES (gen_random_uuid(), '默认租户', 'pro', 'active');
```

---

### users — 系统用户表

```sql
-- 来源：§7.7a
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    email           VARCHAR(255) NOT NULL,
    name_encrypted  TEXT NOT NULL,          -- L3加密：AES-256-GCM
    role            VARCHAR(20) NOT NULL CHECK (role IN ('hr_admin', 'hr_recruiter')),
    avatar_url      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
COMMENT ON TABLE users IS 'S0-系统用户表，HR Admin和HR Recruiter账号，全文FK引用基表';
```

---

### departments — 部门/团队

```sql
-- 来源：§7.7a
CREATE TABLE departments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,               -- 部门名称
    parent_id     UUID REFERENCES departments(id),     -- 上级部门（NULL=顶级）
    tree_path     LTREE,                               -- 物化路径，如 'tech.backend.group1'
    manager_name  VARCHAR(100),                         -- 部门负责人
    sort_order    INT DEFAULT 0,                        -- 同级排序
    status        VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active','inactive','frozen')),
    tenant_id     UUID NOT NULL REFERENCES tenants(id),
    created_at    TIMESTAMPTZ DEFAULT now()
);
COMMENT ON TABLE departments IS 'D1-部门/团队，组织架构树基础，positions归属';
```

---

### evaluation_templates — 面试评估模板

```sql
-- 来源：§7.7a
CREATE TABLE evaluation_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(200) NOT NULL,               -- 模板名称，如"技术终面评估表"
    type          VARCHAR(20) NOT NULL CHECK(type IN ('interview','offer')),  -- 模板类型
    criteria      JSONB NOT NULL DEFAULT '[]',         -- 评估维度定义：[{dimension, weight, scoring_guide}]
    tenant_id     UUID NOT NULL REFERENCES tenants(id),
    created_at    TIMESTAMPTZ DEFAULT now()
);
COMMENT ON TABLE evaluation_templates IS 'B4-面试评估模板，规范interviews和offers的评估维度';
```

---

### channels — 招聘渠道

```sql
-- 来源：§7.7a
CREATE TABLE channels (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,               -- 渠道名称，如"Boss直聘"
    type          VARCHAR(20) NOT NULL CHECK(type IN ('boss','lagou','51job','internal','referral','headhunter')),
    config        JSONB DEFAULT '{}',                  -- 渠道配置：API密钥/账号/同步规则等
    is_active     BOOLEAN DEFAULT true,
    tenant_id     UUID NOT NULL REFERENCES tenants(id)
);
COMMENT ON TABLE channels IS 'C3-招聘渠道，渠道ROI分析基础';
```

---

### profile_updates — 候选人画像更新溯源记录

```sql
-- 来源：§7.7a
CREATE TABLE profile_updates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id  UUID NOT NULL REFERENCES candidates(id),
    source_type   VARCHAR(20) NOT NULL CHECK(source_type IN ('resume_upload','hr_manual','ai_inference','merge_resolution')),
    source_id     UUID,                  -- 来源记录ID（resume_id / inference_id）
    field_path    VARCHAR(100) NOT NULL,  -- 更新字段路径，如 'skills[0]'
    old_value     JSONB,                 -- 旧值
    new_value     JSONB,                 -- 新值
    created_by    UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ DEFAULT now()
);
COMMENT ON TABLE profile_updates IS '候选人画像更新溯源记录，支持论文式引用追踪';
```

---

### conflict_resolutions — 数据冲突处理

```sql
-- 来源：§7.2.2
CREATE TABLE conflict_resolutions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    field_path      VARCHAR(500) NOT NULL,           -- 冲突字段路径（如"work_experience[2].company"）
    old_value       JSONB NOT NULL,                   -- 当前存储值
    new_value       JSONB NOT NULL,                   -- 新数据值
    old_source      JSONB NOT NULL,                   -- 当前值来源 {type, id, confidence}
    new_source      JSONB NOT NULL,                   -- 新值来源 {type, id, confidence}
    resolution      VARCHAR(20) DEFAULT 'manual'
                    CHECK(resolution IN ('keep_old','keep_new','merge','manual')),
    resolved_by     UUID REFERENCES users(id),        -- 处理人
    resolved_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_conflict_pending UNIQUE (candidate_id, field_path, resolved_at)
);

CREATE INDEX idx_conflict_candidate ON conflict_resolutions(candidate_id);
CREATE INDEX idx_conflict_unresolved ON conflict_resolutions(candidate_id) WHERE resolved_at IS NULL;
```

---

### offers — Offer记录

```sql
-- 来源：§7.7a
CREATE TABLE offers (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id           UUID NOT NULL REFERENCES positions(id),
    candidate_id          UUID NOT NULL REFERENCES candidates(id),
    match_id              UUID REFERENCES matches(id),           -- 关联匹配记录
    salary_encrypted       VARCHAR(512),                           -- 【P0-01修复】提议薪资AES-256密文（L4机密数据）
    salary_hash            VARCHAR(64),                            -- 【P0-01修复】薪资SHA-256哈希，用于等值查询/去重，不可逆
    salary_currency        VARCHAR(3) DEFAULT 'CNY',              -- 币种（CNY/USD等）
    benefits_summary       TEXT,                                  -- 福利摘要
    status                 VARCHAR(20) NOT NULL DEFAULT 'draft'
                          CHECK(status IN ('draft','pending_approval','approved','offered',
                                           'accepted','rejected','counter_offered',
                                           'withdrawn','hired','onboarded','cancelled')),
    onboarding_status      VARCHAR(20)
                          CHECK(onboarding_status IS NULL
                                OR onboarding_status IN ('pending','materials_submitted','contract_signed',
                                                         'onboarded','probation','completed','failed')),
    onboarded_at           TIMESTAMPTZ,                           -- 入职确认时间
    reject_reason          TEXT,                                  -- 拒绝原因
    counter_offer_details  JSONB DEFAULT '{}',                    -- 还价详情：{salary, benefits, note}
    created_by             UUID NOT NULL REFERENCES users(id),    -- 创建人（HR）
    approved_by            UUID REFERENCES users(id),             -- 审批人
    approved_at            TIMESTAMPTZ,                           -- 审批时间
    version                INTEGER NOT NULL DEFAULT 1,            -- 乐观锁版本号（V3.5并发控制）
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_offers_position  ON offers(position_id);
CREATE INDEX idx_offers_candidate ON offers(candidate_id);
CREATE INDEX idx_offers_status    ON offers(status);
COMMENT ON TABLE offers IS 'A4-Offer记录，覆盖draft→onboarded全生命周期';
```

---

### onboarding_tasks — 入职任务清单

```sql
-- 来源：§7.7a（P0-09修复，简化版Checklist模式）
CREATE TABLE onboarding_tasks (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id              UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    task_type             VARCHAR(30) NOT NULL
                          CHECK(task_type IN ('material_upload','contract_sign','checkin_7d',
                                              'checkin_30d','checkin_60d','probation_review',
                                              'account_setup','equipment','mentor_assign')),
    title                 VARCHAR(200) NOT NULL,               -- 任务标题，如"上传劳动合同"
    status                VARCHAR(20) NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending','in_progress','completed','skipped','overdue')),
    due_date              TIMESTAMPTZ,                          -- 截止日期
    completed_at          TIMESTAMPTZ,                          -- 完成时间
    assignee_id           UUID REFERENCES users(id),           -- 负责人（HR或用人经理）
    checklist_data        JSONB DEFAULT '{}',                   -- 任务详情：{file_url, notes, rating...}
    created_at            TIMESTAMPTZ DEFAULT now(),
    updated_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_onboarding_tasks_offer ON onboarding_tasks(offer_id);
CREATE INDEX idx_onboarding_tasks_status ON onboarding_tasks(status);
CREATE INDEX idx_onboarding_tasks_due ON onboarding_tasks(due_date);
COMMENT ON TABLE onboarding_tasks IS 'P0-09-入职任务清单，Checklist模式跟踪入职全流程';
```

---

### match_feedback — 匹配反馈表

```sql
-- 来源：§7.7a
CREATE TABLE match_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'neutral')),
    reason TEXT,
    ai_accuracy_score SMALLINT CHECK (ai_accuracy_score BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_match_feedback_match ON match_feedback(match_id);
CREATE INDEX idx_match_feedback_tenant ON match_feedback(tenant_id);
```

---

### share_links — 共享链接表

```sql
-- 来源：§7.7a
CREATE TABLE share_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('candidate', 'position', 'report')),
    resource_id UUID NOT NULL,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_by UUID NOT NULL REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    access_count INT NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_share_links_token ON share_links(token);
CREATE INDEX idx_share_links_resource ON share_links(resource_type, resource_id);
```

---

### ai_decisions — AI决策记录表

```sql
-- 来源：§7.8a（P2修复）
-- 用途：所有AI决策的审计追踪，支撑可解释性和合规要求
CREATE TABLE ai_decisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID,                                   -- 关联Agent会话（sessions表），可为NULL
    decision_type   VARCHAR(50) NOT NULL,                   -- 决策类型枚举：match/score/recommend/parse/generate_jd/briefing/analyze_recording/infer/benchmark
    input_summary   JSONB,                                  -- 输入参数摘要（脱敏后）
    output_summary  JSONB,                                  -- 输出结果摘要（脱敏后）
    model           VARCHAR(50) NOT NULL,                   -- 使用的LLM模型，如 gpt-4.1/gpt-4.1-mini
    prompt_version  VARCHAR(32) NOT NULL,                   -- Prompt版本标识，格式：{ability}_v{N}，如 generate_jd_v2
    token_usage     JSONB,                                  -- Token用量：{prompt: int, completion: int, total: int}
    latency_ms      INTEGER,                                -- 推理耗时（毫秒）
    tenant_id       UUID NOT NULL,                          -- 租户ID（多租户隔离）
    created_at      TIMESTAMPTZ DEFAULT now()               -- 决策时间
);
-- 索引：(tenant_id, decision_type, created_at) 联合索引 + (session_id) 索引
-- 数据永久保留，支持审计导出
```

---

### consent_records — 候选人知情同意记录

```sql
-- 来源：§3.8（P2-31修复）
-- 用途：记录候选人数据处理的知情同意（个保法第13条"告知-同意"规则）
CREATE TABLE consent_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL,
  candidate_id    UUID NOT NULL REFERENCES candidates(id),
  consent_type    VARCHAR(50) NOT NULL,  -- 'data_collection'/'ai_matching'/'recording'/'data_retention'
  consent_source  VARCHAR(30) NOT NULL,  -- 'email_link'/'sms_link'/'im_link'/'web_form'
  consent_version VARCHAR(20) NOT NULL,  -- 知情同意书版本号（如'v1.0'）
  granted_at      TIMESTAMP,
  revoked_at      TIMESTAMP,             -- 撤回时间
  token           VARCHAR(100) UNIQUE,   -- 一次性确认Token
  ip_address      VARCHAR(45),
  created_at      TIMESTAMP DEFAULT NOW(),
  CONSTRAINT uq_consent_unique UNIQUE (candidate_id, consent_type, consent_version)
);
```

---

## 边界Case处理规范（§7.9）

| Case | 处理方式 |
|------|---------|
| 同一人投递多岗位 | candidates唯一，matches多条，Offer一个后其他withdrawn但保留 |
| 简历信息冲突 | `profile_updates`表冲突检测→pending_review→HR人工审核 |
| 岗位关闭时有进行中候选人 | 通知候选人+反向匹配找其他合适岗位+matches.withdrawn |
| 面试No-Show | 不更新画像，HR决定再约或放弃 |
| Offer被拒 | 拒绝原因存入`matches.candidate_feedback`，不自动更新画像 |

---

## 争议裁决记录（§7.10）

| # | 争议 | 裁决 | 置信度 |
|---|------|------|--------|
| 1 | 面试FK到岗位还是人才 | 双FK | ⭐⭐⭐⭐⭐ |
| 2 | 匹配是否两条记录 | 一条记录，对称设计，`initiated_by`区分方向 | ⭐⭐⭐⭐⭐ |
| 3 | 匹配用简历向量还是画像向量 | 画像优先，简历仅冷启动降级 | ⭐⭐⭐⭐☆ |
| 4 | 简历冲突处理 | `parsed_data`不可变+`profile_updates`人工审核 | ⭐⭐⭐⭐⭐ |
| 5 | Offer决策看简历还是画像 | 画像100% | ⭐⭐⭐⭐⭐ |
| 6 | 岗位定义是否先查人才库 | Phase 1不做，Phase 2支持 | ⭐⭐⭐⭐ |
| 8 | 部门架构优先级 | D1部门管理为P0（M1创建岗位依赖department_id必填） | ⭐⭐⭐⭐⭐ |
| 9 | 岗位必须归属部门 | positions.department_id为必填FK | ⭐⭐⭐⭐⭐ |
| 10 | 编制管理纳入岗位 | positions增加headcount_planned+headcount_filled | ⭐⭐⭐⭐⭐ |
| 36 | 匹配状态机改为非线性有向图 | 支持回退、还价循环、多节点reject | ⭐⭐⭐⭐⭐ |

---

## 并发控制规范（§11.1a）

### 乐观锁策略

所有核心实体表增加version字段：
- DDL: `version INTEGER NOT NULL DEFAULT 1`
- 更新时: `UPDATE ... SET version=version+1 WHERE id=:id AND version=:expected_version`
- 影响行数=0 → 抛ConcurrentModificationError(50003)

**适用范围**：positions, candidates, offers, interviews

### 幂等性保证

- 文件上传：客户端生成 `idempotency_key`（UUID），服务端基于 `file_hash + idempotency_key` 去重，24小时内相同key返回已上传文件ID
- 审批操作：状态机天然幂等（已批准→再批准=idempotent，重复审批请求返回当前状态）
- 反馈提交：`feedback_token` 一次性使用，提交后标记为used，重复提交返回409
- 异步任务：`task_events` 表基于 `task_id + task_type` 去重

### 解析+匹配并行竞态保护（V3.6架构修复C-05）

简历解析进行中时（status=parsing），禁止触发该简历的匹配刷新。匹配刷新的 on_complete 回调中检查简历解析状态，若 status≠completed 则跳过本次刷新（记录日志），等待解析完成后的触发链再次刷新。

### 行级锁场景

| 场景 | 锁策略 | 超时 |
|------|--------|------|
| 简历解析中 | SELECT FOR UPDATE SKIP LOCKED | 无需等待 |
| Offer审批 | 乐观锁(version) | — |
| 岗位编辑 | 乐观锁(version) | — |
| 候选人状态流转 | 乐观锁(version) | — |
