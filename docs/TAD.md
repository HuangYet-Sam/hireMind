# HireMind 技术架构文档 (TAD)

> 版本: v1.2 | 最后更新: 2026-05-12 | 作者: CTO
>
> ⚠️ **本文档基于 Next.js + React + Prisma 架构编写，技术栈已变更为 Vue 3 + FastAPI + SQLAlchemy。** 文档中的业务设计、数据模型、API接口定义仍然有效，但所有技术实现细节（代码示例、组件引用、配置方式）需要按新架构重新理解。具体技术差异参见 `docs/architecture/tech-stack.md`。

---

## 1. 概述

### 1.1 文档目的

本技术架构文档（TAD）定义 HireMind 的系统架构、技术选型、数据模型、API 规范和工程标准。所有开发人员必须以此为基准进行开发，任何偏离需要经过 CTO 评审。

### 1.2 系统定位

HireMind 是 AI 原生 HR 招聘管理系统，核心差异在于"论文式 AI 画像"——通过 AI 分析简历和候选人数据，生成带引用溯源的结构化画像，帮助 HR 快速理解候选人。

### 1.3 约束条件

- 一人公司规模，架构必须一个人能维护
- MVP 阶段，功能优先于性能
- 零运维目标，尽量使用托管服务
- AI 功能作为增强层，不影响核心 CRUD 可用性

---

## 2. 技术选型

### 2.1 选型总览

| 层级 | 技术 | 版本 |
|------|------|------|
| 框架 | Next.js (App Router) | 16.x |
| 语言 | TypeScript | 5.x (strict) |
| 样式 | Tailwind CSS | 4.x |
| UI 组件 | shadcn/ui | 最新 |
| ORM | Prisma | 6.x |
| 数据库 | PostgreSQL | 16.x |
| AI | OpenAI API | gpt-4o / text-embedding-3-small |
| 部署 | Vercel + Supabase | - |
| 包管理 | pnpm | 10.x |

### 2.2 选型决策记录

#### 2.2.1 Next.js 16 (App Router)

**选择理由：**
- 全栈统一：前后端一个项目，一人维护不用切换上下文
- App Router：Server Components 默认减少客户端 JS，性能好
- Server Actions：CRUD 操作的最佳实践，替代传统 API Routes
- Vercel 原生支持：部署零配置，预览环境自动生成
- 最新稳定版（16.2.6）：无历史包袱，直接使用最新 API

**Breaking Changes（vs 15.x）：**
- params 在页面和布局中变为 Promise，需要 await
- cookies() / headers() 变为 Promise，需要 await
- 路由缓存从 session 级改为 30 秒临时缓存
- fetch 默认不再缓存（no-store），需显式声明缓存策略

**排除方案：**
- Next.js 15.x：已进入维护模式，不会有新特性
- Remix：社区更小，一人公司风险高
- 单独 React + Express：两个项目维护成本翻倍
- Nuxt：TypeScript 生态不如 React

#### 2.2.2 Prisma + PostgreSQL

**选择理由：**
- Schema 即文档：数据模型定义在 schema.prisma，类型自动生成
- 类型安全：查询结果完全类型化，减少运行时错误
- 迁移管理：prisma migrate 自动处理数据库变更
- PostgreSQL：JSON 支持好（AI 推理结果存储）、全文搜索能力

**排除方案：**
- Drizzle：更轻量但社区更小，文档不够成熟
- TypeORM：装饰器风格，TypeScript 集成不如 Prisma
- MongoDB：关系型数据更适合 HR 场景，候选人-职位多对多关系

#### 2.2.3 OpenAI API

**选择理由：**
- 不训练模型，API 调用最省力
- Embedding + Chat 覆盖画像和匹配两个核心场景
- 生态成熟，文档完善，一人能搞定

**排除方案：**
- 自部署 LLM：运维成本高，一人搞不定
- Anthropic Claude：国内访问不稳定
- 百度/阿里大模型：作为备选，架构上预留切换能力

**抽象设计：**
AI 服务层通过接口抽象，不直接依赖 OpenAI SDK，方便后续切换模型提供商。

#### 2.2.4 shadcn/ui

**选择理由：**
- 不是 npm 包，是代码拷贝：完全可定制、不黑盒
- 基于 Radix UI：无障碍性好
- Tailwind CSS 原生：与项目样式方案一致
- 一人维护能掌控每一行组件代码

**排除方案：**
- Ant Design：样式覆盖困难，设计自由度低
- Material UI：包体积大，定制成本高
- Headless UI：组件数量少，不够用

#### 2.2.5 Vercel + Supabase

**选择理由：**
- Vercel：Next.js 原生部署，零配置 CI/CD，预览环境自动生成
- Supabase：托管 PostgreSQL，免费额度够 MVP，自带 Auth 和 Storage
- 零运维：不需要管理服务器、SSL、域名解析

**排除方案：**
- AWS：运维复杂度高，一人搞不定
- Railway：功能类似但生态不如 Vercel
- 自部署：运维成本与一人公司定位矛盾

### 2.3 前端技术栈补充

| 技术 | 用途 |
|------|------|
| React Hook Form + Zod | 表单验证 |
| TanStack Query | 服务端状态管理 |
| Zustand | 客户端状态管理（仅必要时） |
| Lucide React | 图标库 |
| date-fns | 日期处理 |
| react-pdf | 简历 PDF 预览 |

---

## 3. 系统架构

### 3.1 分层架构

```
┌─────────────────────────────────────────────┐
│                   客户端                      │
│   React Components (Server + Client)         │
│   UI 层：shadcn/ui + Tailwind CSS            │
├─────────────────────────────────────────────┤
│                 Next.js App Router            │
│   Pages / Layouts / Loading / Error          │
├─────────────────────────────────────────────┤
│                 API 层 (Route Handlers)       │
│   RESTful API Endpoints                      │
│   请求验证 → 业务逻辑 → 响应格式化              │
├─────────────────────────────────────────────┤
│                 服务层 (Services)             │
│   业务服务：Candidate / Job / Tag             │
│   AI 服务：Profile / Match / Embedding        │
│   基础服务：Storage / Notification            │
├─────────────────────────────────────────────┤
│                 数据层                        │
│   Prisma ORM → PostgreSQL                    │
│   OpenAI API → Embedding + Chat              │
│   Supabase Storage → 文件存储                 │
└─────────────────────────────────────────────┘
```

### 3.2 模块划分与依赖方向

```
模块依赖关系（箭头表示依赖方向）：

  core（基础设施、类型定义、工具函数）
    ↑
  services（业务逻辑层）
    ├── candidate-service（候选人管理）
    ├── job-service（职位管理，含匹配）
    ├── ai-service（AI 画像 + 匹配分析）
    ├── resume-service（简历解析与存储）
    └── tag-service（标签管理）
    ↑
  api（API 路由层，调用 services）
    ↑
  app（页面层，调用 API 或直接用 Server Components）
```

**依赖规则：**
- 上层可以依赖下层，下层不能依赖上层
- services 层内部模块可以互相引用，但禁止循环依赖
- ai-service 不能被业务服务直接依赖，必须通过接口层调用

### 3.3 AI 服务层架构（零侵入原则）

```
                    ┌──────────────┐
                    │  AI Gateway  │  ← 统一入口
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌─────▼──────┐ ┌──▼─────────┐
     │ Profile AI │ │  Match AI  │ │ Embedding  │
     │ 画像生成    │ │  匹配分析   │ │  向量化     │
     └────────────┘ └────────────┘ └────────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │ AI Provider  │  ← 可插拔（OpenAI / 其他）
                    └──────────────┘
```

**零侵入实现方式：**
1. AI Gateway 是唯一对外接口，业务层只调用 Gateway
2. AI Provider 通过配置切换，不改业务代码
3. AI 调用失败时降级：核心 CRUD 不受影响，AI 功能显示"暂不可用"
4. AI 推理结果独立存储在 `AiInference` 表，与事实数据字段分离

### 3.4 目录结构

```
src/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # 认证相关页面（路由组）
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/              # 主业务页面（路由组）
│   │   ├── layout.tsx            # 侧边栏 + 顶栏布局
│   │   ├── candidates/           # 候选人管理
│   │   │   ├── page.tsx          # 列表页
│   │   │   ├── [id]/page.tsx     # 详情页（含 AI 画像）
│   │   │   └── new/page.tsx      # 新建页
│   │   ├── jobs/                 # 职位管理
│   │   │   ├── page.tsx          # 列表页
│   │   │   ├── [id]/page.tsx     # 详情页（含匹配列表）
│   │   │   └── new/page.tsx      # 新建页
│   │   ├── settings/             # 设置
│   │   └── page.tsx              # 仪表盘首页
│   ├── api/                      # API Route Handlers
│   │   ├── candidates/
│   │   ├── jobs/
│   │   ├── ai/
│   │   │   ├── profile/          # AI 画像生成
│   │   │   └── match/            # AI 匹配分析
│   │   ├── tags/
│   │   └── upload/               # 文件上传
│   ├── layout.tsx                # 根布局
│   └── globals.css
├── components/                   # 可复用组件
│   ├── ui/                       # shadcn/ui 基础组件
│   ├── candidates/               # 候选人相关组件
│   ├── jobs/                     # 职位相关组件
│   ├── ai/                       # AI 功能组件
│   │   ├── profile-card.tsx      # AI 画像卡片
│   │   ├── inference-badge.tsx   # AI 推理标注
│   │   ├── source-link.tsx       # 引用溯源链接
│   │   └── ai-provider.tsx       # AI 上下文 Provider
│   └── shared/                   # 通用业务组件
├── lib/                          # 核心库
│   ├── db.ts                     # Prisma 客户端实例
│   ├── ai/                       # AI 服务
│   │   ├── gateway.ts            # AI Gateway
│   │   ├── providers/            # AI 提供商实现
│   │   │   └── openai.ts
│   │   ├── profile.ts            # 画像生成逻辑
│   │   ├── match.ts              # 匹配分析逻辑
│   │   └── embedding.ts          # 向量化逻辑
│   ├── services/                 # 业务服务
│   │   ├── candidate.service.ts
│   │   ├── job.service.ts
│   │   ├── resume.service.ts
│   │   └── tag.service.ts
│   ├── validators/               # Zod Schema 验证
│   │   ├── candidate.ts
│   │   └── job.ts
│   └── utils/                    # 工具函数
│       ├── api-response.ts       # 统一响应格式化
│       ├── error.ts              # 错误处理
│       └── pagination.ts         # 分页工具
├── types/                        # TypeScript 类型定义
│   ├── api.ts                    # API 类型
│   ├── candidate.ts
│   ├── job.ts
│   └── ai.ts
└── hooks/                        # 自定义 React Hooks
    ├── use-candidates.ts
    ├── use-jobs.ts
    └── use-ai-profile.ts
```

---

## 4. 数据模型

> 注意：以下为初版设计，等 PRD V3.5 最终确认后调整字段细节。

### 4.1 核心实体关系

```
User ──< Company >── Job ──< Application >── Candidate
              │                                      │
              │                                      ├──< Resume
              │                                      │
              │                                      ├──< CandidateTag >── Tag
              │                                      │
              └──────────────────────────────────────┘
                                   │
                            AiProfile（独立存储）
                                   │
                            AiInference（引用链）
```

### 4.2 Prisma Schema（初版）

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ============ 用户与组织 ============

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String
  avatarUrl String?
  role      UserRole @default(MEMBER)
  companyId String
  company   Company  @relation(fields: [companyId], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("users")
}

enum UserRole {
  OWNER
  ADMIN
  MEMBER
}

model Company {
  id        String     @id @default(cuid())
  name      String
  industry  String?
  size      CompanySize?
  users     User[]
  jobs      Job[]
  tags      Tag[]
  createdAt DateTime   @default(now())
  updatedAt DateTime   @updatedAt

  @@map("companies")
}

enum CompanySize {
  STARTUP     // 1-20
  SMALL       // 20-100
  MEDIUM      // 100-500
  LARGE       // 500+
}

// ============ 职位管理 ============

model Job {
  id          String       @id @default(cuid())
  title       String
  department  String?
  location    String?
  type        JobType?
  salaryMin   Int?
  salaryMax   Int?
  description String       // Markdown 格式
  requirements String      // Markdown 格式
  status      JobStatus    @default(DRAFT)
  companyId   String
  company     Company      @relation(fields: [companyId], references: [id])
  applications Application[]
  embeddings  JobEmbedding?
  createdAt   DateTime     @default(now())
  updatedAt   DateTime     @updatedAt

  @@map("jobs")
}

enum JobType {
  FULL_TIME
  PART_TIME
  CONTRACT
  INTERNSHIP
}

enum JobStatus {
  DRAFT
  OPEN
  PAUSED
  CLOSED
  ARCHIVED
}

// ============ 候选人管理 ============

model Candidate {
  id          String          @id @default(cuid())
  name        String
  email       String?
  phone       String?
  source      String?         // 来源渠道
  headline    String?         // 一句话简介
  summary     String?         // 人工摘要
  companyId   String
  // company relation 通过 Application 间接关联
  resumes     Resume[]
  tags        CandidateTag[]
  aiProfile   AiProfile?
  applications Application[]
  createdAt   DateTime        @default(now())
  updatedAt   DateTime        @updatedAt

  @@unique([email, companyId])
  @@map("candidates")
}

model Resume {
  id           String   @id @default(cuid())
  filename     String
  fileUrl      String   // Supabase Storage URL
  fileType     String   // pdf / docx
  fileSize     Int
  parsedText   String?  // 解析后的纯文本
  parseStatus  ParseStatus @default(PENDING)
  candidateId  String
  candidate    Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)
  uploadedAt   DateTime @default(now())

  @@map("resumes")
}

enum ParseStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
}

// ============ 标签系统 ============

model Tag {
  id        String         @id @default(cuid())
  name      String
  color     String         // hex color
  type      TagType        @default(CUSTOM)
  companyId String
  company   Company        @relation(fields: [companyId], references: [id])
  candidates CandidateTag[]

  @@unique([name, companyId])
  @@map("tags")
}

enum TagType {
  SKILL       // 技能标签
  EXPERIENCE  // 经验标签
  EDUCATION   // 学历标签
  CUSTOM      // 自定义标签
}

model CandidateTag {
  candidateId String
  tagId       String
  candidate   Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)
  tag         Tag       @relation(fields: [tagId], references: [id], onDelete: Cascade)
  createdAt   DateTime  @default(now())

  @@id([candidateId, tagId])
  @@map("candidate_tags")
}

// ============ 申请/投递 ============

model Application {
  id          String            @id @default(cuid())
  status      ApplicationStatus @default(APPLIED)
  matchScore  Float?            // AI 匹配分数 0-1
  matchReason String?           // AI 匹配分析（Markdown）
  candidateId String
  candidate   Candidate         @relation(fields: [candidateId], references: [id])
  jobId       String
  job         Job               @relation(fields: [jobId], references: [id])
  createdAt   DateTime          @default(now())
  updatedAt   DateTime          @updatedAt

  @@unique([candidateId, jobId])
  @@map("applications")
}

enum ApplicationStatus {
  APPLIED
  SCREENING
  INTERVIEW
  OFFER
  REJECTED
  HIRED
  WITHDRAWN
}

// ============ AI 画像（零侵入独立存储） ============

model AiProfile {
  id          String   @id @default(cuid())
  candidateId String   @unique
  candidate   Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)
  summary     String   // AI 生成的候选人摘要
  strengths   Json     // AI 分析的优势列表
  concerns    Json     // AI 分析的风险点
  experience  Json     // AI 结构化的工作经历
  education   Json     // AI 结构化的教育经历
  skills      Json     // AI 提取的技能列表
  version     Int      @default(1)
  generatedAt DateTime @default(now())
  updatedAt   DateTime @updatedAt

  inferences  AiInference[]

  @@map("ai_profiles")
}

model AiInference {
  id              String            @id @default(cuid())
  profileId       String
  profile         AiProfile         @relation(fields: [profileId], references: [id], onDelete: Cascade)
  type            InferenceNature   // 推理性质：FACT（事实提取）或 REASONING（隐性推理）
  category        InferenceCategory // 业务语义：技能、经历、文化等
  content         String            // 推理结论
  confidence      Float             // 置信度 0-1
  reasoningChain  String?           // 推理过程（REASONING 类型必须填写）
  sourceType      SourceType        // 数据来源类型
  sourceId        String?           // 来源记录 ID（resumeId 等）
  sourceText      String?           // 原文摘录
  createdAt       DateTime          @default(now())

  @@map("ai_inferences")
}

// 推理性质 — 决定前端视觉模式和验收标准
// FACT: 实色背景 + 引用标记，准确率 >= 95%，引用覆盖率 100%
// REASONING: 渐变背景 + Sparkles + 置信度，幻觉 <= 10%，必须有 reasoningChain
enum InferenceNature {
  FACT       // 事实提取 — 从简历中直接提取的结构化数据
  REASONING  // 隐性推理 — AI 基于数据推断的结论
}

// 业务语义 — 决定前端颜色系和展示分类
enum InferenceCategory {
  SKILL_TAG            // 技能标签
  EXPERIENCE_SUMMARY   // 经历摘要
  CULTURE_FIT          // 文化契合度
  MATCH_SCORE          // 匹配评分
  SALARY_PREDICTION    // 薪资预测
}

enum SourceType {
  RESUME       // 来自简历
  INTERVIEW    // 来自面试记录
  ASSESSMENT   // 来自测评
  AI_REASONING // AI 推理（明确标注非事实）
}

// ============ 向量嵌入（匹配用） ============

model JobEmbedding {
  id        String   @id @default(cuid())
  jobId     String   @unique
  job       Job      @relation(fields: [jobId], references: [id], onDelete: Cascade)
  embedding Vector   // pgvector 扩展，存储职位要求的向量
  createdAt DateTime @default(now())

  @@map("job_embeddings")
}

model CandidateEmbedding {
  id          String   @id @default(cuid())
  candidateId String
  candidate   Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)
  resumeId    String?   // 关联的简历
  embedding   Vector    // pgvector，存储候选人简历的向量
  createdAt   DateTime  @default(now())

  @@unique([candidateId, resumeId])
  @@map("candidate_embeddings")
}
```

### 4.3 数据模型设计要点

1. **Company 隔离**：所有业务数据通过 companyId 实现多租户隔离
2. **AI 数据独立存储**：AiProfile 和 AiInference 独立于 Candidate 表，删除 AI 数据不影响候选人基本信息
3. **引用链设计**：AiInference.sourceId + sourceType 实现数据溯源，UI 可跳转到原始简历
4. **推理双维度分类**：AiInference 使用 type（InferenceNature: FACT/REASONING）+ category（InferenceCategory: 5 种业务语义）双字段设计。同一业务语义（如 SKILL_TAG）可以同时存在事实提取和隐性推理。前端直接按 type 决定视觉模式，按 category 决定颜色系，无需映射函数。FACT 类型准确率 >= 95%、引用覆盖率 100%；REASONING 类型幻觉 <= 10%，必须有 reasoningChain
5. **向量匹配**：JobEmbedding + CandidateEmbedding 支持语义相似度匹配
6. **Application 桥接**：候选人-职位多对多关系通过 Application 表实现，同时承载匹配结果

---

## 5. API 设计规范

### 5.1 URL 规范

```
基础路径: /api/v1

资源命名: 小写复数名词
GET    /api/v1/candidates          # 列表
GET    /api/v1/candidates/:id      # 详情
POST   /api/v1/candidates          # 创建
PATCH  /api/v1/candidates/:id      # 更新
DELETE /api/v1/candidates/:id      # 删除

嵌套资源:
GET    /api/v1/candidates/:id/resumes      # 候选人的简历列表
POST   /api/v1/candidates/:id/resumes      # 上传简历
GET    /api/v1/candidates/:id/ai-profile   # 候选人的 AI 画像
POST   /api/v1/candidates/:id/ai-profile   # 触发 AI 画像生成

GET    /api/v1/jobs/:id/applications       # 职位的候选人列表
POST   /api/v1/jobs/:id/match              # 触发 AI 匹配分析
```

### 5.2 统一响应格式

**成功响应：**

```typescript
// 单条记录
interface ApiResponse<T> {
  success: true;
  data: T;
}

// 列表（带分页）
interface ApiListResponse<T> {
  success: true;
  data: T[];
  pagination: {
    page: number;       // 当前页，从 1 开始
    pageSize: number;   // 每页条数
    total: number;      // 总条数
    totalPages: number; // 总页数
  };
}
```

**错误响应：**

```typescript
interface ApiErrorResponse {
  success: false;
  error: {
    code: string;       // 错误码，如 "CANDIDATE_NOT_FOUND"
    message: string;    // 人类可读的错误信息
    details?: unknown;  // 可选的详细信息（验证错误等）
  };
}
```

### 5.3 错误码体系

```
通用错误:
  INVALID_REQUEST     400  请求参数验证失败
  UNAUTHORIZED        401  未认证
  FORBIDDEN           403  无权限
  NOT_FOUND           404  资源不存在
  CONFLICT            409  资源冲突（如重复创建）
  RATE_LIMITED        429  请求频率超限
  INTERNAL_ERROR      500  服务端内部错误

业务错误:
  CANDIDATE_NOT_FOUND
  JOB_NOT_FOUND
  RESUME_PARSE_FAILED
  AI_SERVICE_UNAVAILABLE  # AI 服务降级
  AI_PROFILE_GENERATING   # 画像正在生成中
  DUPLICATE_APPLICATION   # 重复投递

验证错误:
  VALIDATION_ERROR     # 通用验证失败
  INVALID_EMAIL
  INVALID_PHONE
```

### 5.4 API 端点清单（MVP）

#### 候选人管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /candidates | 候选人列表（分页、搜索、标签筛选） |
| GET | /candidates/:id | 候选人详情（含标签、简历列表） |
| POST | /candidates | 创建候选人 |
| PATCH | /candidates/:id | 更新候选人 |
| DELETE | /candidates/:id | 删除候选人 |
| POST | /candidates/:id/resumes | 上传简历 |
| GET | /candidates/:id/resumes | 简历列表 |
| DELETE | /candidates/:id/resumes/:rid | 删除简历 |
| POST | /candidates/:id/tags | 添加标签 |
| DELETE | /candidates/:id/tags/:tid | 移除标签 |

#### AI 画像

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /candidates/:id/ai-profile | 获取 AI 画像 |
| POST | /candidates/:id/ai-profile | 触发画像生成（异步） |
| GET | /candidates/:id/ai-profile/inferences | 获取推理列表 |

#### 职位管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /jobs | 职位列表 |
| GET | /jobs/:id | 职位详情 |
| POST | /jobs | 创建职位 |
| PATCH | /jobs/:id | 更新职位 |
| DELETE | /jobs/:id | 删除职位 |
| PATCH | /jobs/:id/status | 更新职位状态 |

#### 匹配（职位子功能）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /jobs/:id/applications | 职位的候选人列表（含匹配分） |
| POST | /jobs/:id/applications | 添加候选人到职位 |
| POST | /jobs/:id/match | 触发 AI 匹配分析 |
| PATCH | /applications/:id/status | 更新申请状态 |

#### 标签

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /tags | 标签列表 |
| POST | /tags | 创建标签 |
| PATCH | /tags/:id | 更新标签 |
| DELETE | /tags/:id | 删除标签 |

### 5.5 请求/示例

**创建候选人：**

```
POST /api/v1/candidates
Content-Type: application/json

{
  "name": "张三",
  "email": "zhangsan@example.com",
  "phone": "13800138000",
  "source": "BOSS直聘"
}

Response 201:
{
  "success": true,
  "data": {
    "id": "clxxx...",
    "name": "张三",
    "email": "zhangsan@example.com",
    "phone": "13800138000",
    "source": "BOSS直聘",
    "createdAt": "2026-05-12T10:00:00Z"
  }
}
```

**候选人列表（分页）：**

```
GET /api/v1/candidates?page=1&pageSize=20&search=张&tagId=clxxx

Response 200:
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

---

## 6. 工程规范

### 6.1 代码规范

```json
// tsconfig.json 关键配置
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

**规则：**
- 禁止 any，用 unknown 代替
- 禁止 @ts-ignore，用 @ts-expect-error 并注释原因
- 函数参数和返回值必须有类型注解
- API 响应数据必须经过 Zod Schema 验证

### 6.2 文件命名

- 组件：kebab-case（candidate-card.tsx）
- 工具函数：kebab-case（format-date.ts）
- 类型文件：kebab-case（candidate.ts）
- 页面：Next.js 约定（page.tsx, layout.tsx, loading.tsx, error.tsx）
- API 路由：route.ts（Next.js App Router 约定）

### 6.3 Git 规范

```
分支策略:
main            # 生产分支，保护分支
  └── dev       # 开发主线
       └── feat/candidate-crud    # 功能分支
       └── fix/resume-parse       # 修复分支
       └── refactor/ai-service    # 重构分支

Commit 格式 (Conventional Commits):
feat: 新功能
fix: 修复
refactor: 重构（不改变功能）
docs: 文档
style: 格式调整
test: 测试
chore: 构建/工具

示例:
feat(candidates): add candidate list with pagination
fix(resume): handle PDF parse timeout gracefully
refactor(ai): extract provider interface for zero-coupling
```

### 6.4 环境变量

```env
# .env.local（本地开发）
DATABASE_URL=postgresql://...
NEXT_PUBLIC_APP_URL=http://localhost:3000

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# AI 服务开关（零侵入降级）
AI_SERVICE_ENABLED=true
```

---

## 7. 部署方案

### 7.1 环境规划

| 环境 | 用途 | 部署方式 |
|------|------|----------|
| Local | 本地开发 | next dev + Supabase Docker |
| Preview | PR 预览 | Vercel 自动部署 |
| Staging | 测试验收 | Vercel staging branch |
| Production | 生产环境 | Vercel main branch |

### 7.2 CI/CD 流程

```
Push to feat/* → 自动部署 Preview 环境
PR to dev → 自动部署 + 类型检查 + Lint
Merge to dev → 自动部署 Staging
PR to main → 自动部署 + 完整测试
Merge to main → 自动部署 Production
```

### 7.3 数据库迁移

```
开发环境: prisma migrate dev（自动应用 + 生成客户端）
生产环境: prisma migrate deploy（仅应用迁移，在 CI 中执行）
```

---

## 8. 安全考虑

1. **认证**：Supabase Auth（JWT），API 中间件统一校验
2. **多租户隔离**：所有查询强制 companyId 过滤
3. **输入验证**：所有 API 输入经过 Zod Schema 验证
4. **文件上传**：限制文件类型（pdf/docx）和大小（10MB）
5. **AI 降级**：AI 服务故障时，系统自动降级，核心功能不受影响
6. **敏感数据**：简历文件通过 Supabase Storage 的签名 URL 访问

---

## 9. 待 PRD 确认后补充的内容

- [ ] Prisma Schema 字段微调（根据 PRD 最终需求）
- [ ] AI 画像生成的具体 Prompt 策略
- [ ] 简历解析的技术方案选型（自建 vs 第三方 API）
- [ ] 完整的 API 请求/响应示例
- [ ] 性能指标和优化目标
- [ ] 监控和日志方案

---

> 本文档随项目推进持续更新。修改记录请查看 Git 提交历史。
