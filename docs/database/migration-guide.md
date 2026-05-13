# 数据库迁移策略

> PRD来源：§11.7a
> 最后更新：2026-05-12

---

## 迁移规范总表

| 维度 | 规范 |
|------|------|
| **迁移工具** | Alembic（SQLAlchemy官方迁移工具） |
| **分支策略** | 每个Feature分支创建独立迁移脚本，合并时按时间戳自动排序 |
| **生产规则** | 迁移脚本仅允许 `upgrade`，禁止手写 `downgrade`（生产不可逆） |
| **DDL审查** | 新增DDL必须包含 `COMMENT ON TABLE/COLUMN`、索引、外键约束 |
| **回滚方案** | 生产回滚通过 `pg_dump` 快照恢复，不依赖Alembic downgrade |
| **CI集成** | `alembic upgrade head` 作为CI必经步骤，迁移失败阻断构建 |

---

## 详细说明

### 1. 迁移工具：Alembic

- 使用SQLAlchemy官方迁移工具Alembic管理数据库schema版本
- 与SQLAlchemy ORM深度集成，完整支持JSONB/pgvector/CTE等PG特性
- 自动生成迁移脚本（`alembic revision --autogenerate`），减少手写错误

### 2. 分支策略

```
main (生产)
  ├── feature/position-encryption  → 迁移脚本 001_add_position_fields.py
  ├── feature/offer-table          → 迁移脚本 002_create_offers.py
  └── feature/ai-decisions         → 迁移脚本 003_create_ai_decisions.py
```

- 每个Feature分支创建独立迁移脚本
- 合并到main时，Alembic按时间戳自动排序（`revision`链式依赖）
- 冲突时需手动调整 `down_revision` 引用

### 3. 生产规则

- **仅允许 upgrade**：生产环境只执行 `alembic upgrade head`
- **禁止 downgrade**：不在生产环境执行回滚迁移脚本
- **原因**：生产数据不可逆，回滚通过 `pg_dump` 快照恢复

### 4. DDL审查清单

新增DDL必须包含：

| 审查项 | 示例 |
|--------|------|
| 表注释 | `COMMENT ON TABLE xxx IS '...'` |
| 列注释 | `COMMENT ON COLUMN xxx.yyy IS '...'` |
| 索引 | 根据查询模式创建合适索引（B-tree/部分索引/GIN） |
| 外键约束 | `REFERENCES` + `ON DELETE CASCADE`（如适用） |
| CHECK约束 | 状态枚举、数值范围等 |
| UNIQUE约束 | 业务唯一键 |

### 5. 回滚方案

```
正常流程：
  pg_dump → 部署新版本 → alembic upgrade head → 验证

回滚流程：
  停止应用 → pg_restore 恢复快照 → 部署旧版本 → 启动验证
```

- **快照时机**：每次部署前自动执行 `pg_dump`
- **快照保留**：最近5次部署快照
- **恢复时间目标**：< 15分钟

### 6. CI集成

```yaml
# GitHub Actions CI步骤
- name: Run Database Migrations
  run: |
    alembic upgrade head
  env:
    DATABASE_URL: postgresql://test:test@localhost:5432/hiremind_test
```

- `alembic upgrade head` 作为CI必经步骤
- 迁移失败 → 阻断构建 → 开发者修复后重新提交
- 测试数据库使用独立测试实例，不污染开发/生产数据

---

## 初始化迁移顺序建议

基于§7.2-§7.10的DDL依赖关系，建议的初始化迁移顺序：

```
001_create_tenants          -- 基表，无依赖
002_create_users            -- 依赖 tenants
003_create_departments      -- 依赖 tenants
004_create_positions        -- 依赖 departments, users
005_create_candidates       -- 依赖 tenants
006_create_resumes          -- 依赖 candidates, positions, users
007_create_matches          -- 依赖 positions, candidates
008_create_interviews       -- 依赖 positions, candidates, matches, users
009_create_profile_updates  -- 依赖 candidates, users
010_create_conflict_resolutions -- 依赖 candidates, users
011_create_evaluation_templates -- 依赖 tenants
012_create_channels         -- 依赖 tenants
013_create_offers           -- 依赖 positions, candidates, matches, users
014_create_onboarding_tasks -- 依赖 offers, users
015_create_match_feedback   -- 依赖 tenants, matches, users
016_create_share_links      -- 依赖 tenants, users
017_create_ai_decisions     -- 独立表
018_create_consent_records  -- 依赖 candidates
```

---

## ORM技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| SQLAlchemy | 2.x | 数据库操作，完整支持JSONB/pgvector/CTE |
| Alembic | latest | 迁移管理（SQLAlchemy官方工具） |
| Pydantic | 2.x | API参数校验（FastAPI内置） |

---

## 数据安全相关迁移注意事项

### 加密字段迁移

涉及AES-256加密存储的字段（L3/L4级别数据）：

| 表 | 字段 | 级别 | 加密方式 |
|-----|------|------|---------|
| candidates | email | L3 | AES-256加密密文 |
| candidates | phone | L3 | AES-256加密密文 |
| candidates | name_encrypted | L3 | AES-256-GCM |
| users | name_encrypted | L3 | AES-256-GCM |
| offers | salary_encrypted | L4 | AES-256密文+独立密钥 |

### 哈希字段迁移

用于去重/查询的SHA256哈希字段：

| 表 | 字段 | 用途 |
|-----|------|------|
| candidates | phone_hash | 手机号去重 |
| candidates | email_hash | 邮箱去重 |
| candidates | name_hash | 姓名模糊匹配去重 |
| offers | salary_hash | 薪资等值查询 |

### 向量相关迁移

- pgvector扩展需在初始化迁移中启用：`CREATE EXTENSION IF NOT EXISTS vector;`
- LTREE扩展需为departments表启用：`CREATE EXTENSION IF NOT EXISTS ltree;`
- HNSW索引创建属于耗时操作，建议在大数据量迁移时单独执行
