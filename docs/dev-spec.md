# HireMind 开发规范

> 版本: v1.0-draft  
> 维护者: CTO  
> 更新日期: 2026-05-12
>
> ⚠️ **本文档基于 Next.js + React + Prisma 架构编写，技术栈已变更为 Vue 3 + FastAPI + SQLAlchemy。** 文档中的业务设计、数据模型、API接口定义仍然有效，但所有技术实现细节（代码示例、组件引用、配置方式）需要按新架构重新理解。具体技术差异参见 `docs/architecture/tech-stack.md`。

---

## 1. 代码规范

### 1.1 TypeScript

- 严格模式：`strict: true`
- 禁止 `any`，必须提供类型定义
- 优先使用 `interface` 定义对象类型，`type` 用于联合类型和工具类型
- 枚举使用 Prisma 生成的枚举类型，不重复定义

### 1.2 命名约定

| 类型 | 风格 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `candidate-service.ts` |
| 组件文件 | PascalCase | `CandidateCard.tsx` |
| 变量/函数 | camelCase | `getCandidateById` |
| 常量 | SCREAMING_SNAKE_CASE | `MAX_FILE_SIZE` |
| 类型/接口 | PascalCase | `CandidateDetail` |
| Prisma Model | PascalCase | `Candidate` |
| API 路由 | kebab-case | `/api/candidates` |
| 数据库表名 | snake_case | `candidates`（通过 @@map） |

### 1.3 ESLint + Prettier

```json
{
  "extends": ["next/core-web-vitals", "prettier"],
  "rules": {
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

### 1.4 Import 顺序

```typescript
// 1. React / Next.js
import { useState } from 'react';
import { useRouter } from 'next/navigation';

// 2. 第三方库
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

// 3. 内部模块
import { prisma } from '@/lib/prisma';
import { candidateService } from '@/services/candidate.service';

// 4. 类型
import type { Candidate } from '@/types/candidate';

// 5. 组件
import { Button } from '@/components/ui/button';
import { CandidateCard } from '@/components/candidates/candidate-card';
```

---

## 2. Git 规范

### 2.1 分支策略

```
main          — 生产分支，只通过 PR 合入
├── develop   — 开发主线
├── feat/xxx  — 功能分支
├── fix/xxx   — 修复分支
└── chore/xxx — 杂项（依赖更新等）
```

### 2.2 Commit Message

遵循 Conventional Commits：

```
feat(candidates): add candidate list with pagination
fix(ai): handle OpenAI API timeout gracefully
docs(tad): update data model for MVP scope
refactor(services): extract shared pagination logic
chore(deps): update prisma to v6.x
```

---

## 3. API 开发规范

### 3.1 Route Handler 模板

```typescript
// app/api/candidates/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { candidateService } from '@/services/candidate.service';

// 参数校验 Schema
const listSchema = z.object({
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
  search: z.string().optional(),
  status: z.enum(['ACTIVE', 'INACTIVE']).optional(),
});

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const params = listSchema.parse(Object.fromEntries(searchParams));
    const result = await candidateService.list(params);
    
    return NextResponse.json({
      success: true,
      data: result.data,
      meta: result.meta,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { success: false, error: { code: 'VALIDATION_ERROR', message: error.message } },
        { status: 400 }
      );
    }
    return NextResponse.json(
      { success: false, error: { code: 'INTERNAL_ERROR', message: 'Internal server error' } },
      { status: 500 }
    );
  }
}
```

### 3.2 Service 模板

```typescript
// services/candidate.service.ts
import { prisma } from '@/lib/prisma';

export const candidateService = {
  async list(params: { page: number; limit: number; search?: string }) {
    const where = params.search
      ? { name: { contains: params.search, mode: 'insensitive' as const } }
      : {};

    const [data, total] = await Promise.all([
      prisma.candidate.findMany({
        where,
        skip: (params.page - 1) * params.limit,
        take: params.limit,
        orderBy: { createdAt: 'desc' },
        include: { tags: true },
      }),
      prisma.candidate.count({ where }),
    ]);

    return {
      data,
      meta: {
        page: params.page,
        limit: params.limit,
        total,
        totalPages: Math.ceil(total / params.limit),
      },
    };
  },
};
```

---

## 4. 测试规范

### 4.1 测试分层

| 层级 | 工具 | 覆盖范围 |
|------|------|---------|
| 单元测试 | Vitest | Service 层业务逻辑 |
| API 测试 | Vitest + MSW | API Route 请求响应 |
| E2E 测试 | Playwright | 核心用户流程 |

### 4.2 命名约定

```
测试文件：[module].test.ts
测试描述：should [预期行为] when [条件]
```

### 4.3 覆盖率目标

- Service 层：80%+
- API Route：70%+
- 核心 E2E 流程：100%（候选人 CRUD、职位 CRUD、AI 画像生成）

---

## 5. 目录结构约定

- 一个模块的代码放在对应目录下（components/candidates/, services/candidate.service.ts）
- 共享组件放在 components/shared/
- 工具函数放在 lib/
- 类型定义集中管理在 types/
- Prompt 模板放在 services/ai/prompts/

---

> 此文档随项目推进持续更新。如有疑问 @CTO。
