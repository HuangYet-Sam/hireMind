# 索引策略与pgvector向量方案

> PRD来源：§7.2.1（岗位画像向量重建）、§7.2.3（候选人向量策略）、§5.10（RAG架构）、§11.4（可扩展性）、§12（技术选型）、§12.1（架构优化规范）
> 最后更新：2026-05-12

---

## 一、向量数据库选型

| 维度 | 选型 |
|------|------|
| **向量数据库** | pgvector 0.8+ |
| **索引类型** | HNSW索引 + SQ8量化 |
| **召回率** | >99% |
| **内存优化** | SQ8量化内存降75% |
| **Phase 2扩展** | pgvectorscale StreamingDiskANN，百万级扩展路径 |
| **存储引擎** | PostgreSQL 17+（内置pgvector扩展） |

**选型理由**：pgvector作为PG扩展，零额外运维，与业务数据同库查询避免网络开销。HNSW+SQ8量化在10万向量规模下性能卓越。

---

## 二、Embedding方案

| 维度 | 规格 |
|------|------|
| **Embedding模型** | text-embedding-3-small |
| **向量维度** | 1536维（Phase 1默认） |
| **Phase 2升级** | 3072维（text-embedding-3-large） |
| **内存预估** | 10万向量 × 1536维 ≈ 800MB（单机可承受） |

### 跨表检索对齐方案

1. **统一embedding维度(1536)**：所有表使用text-embedding-3-small生成1536维向量
2. **各表独立pgvector索引**：每张表维护独立HNSW索引（ef_construction=128, m=24）
3. **合并检索**：对各entity_type分别执行pgvector ANN检索，取各表Top-K结果
4. **RRF融合**：对多表结果执行Reciprocal Rank Fusion（k=60），合并为统一排序
5. **LLM Rerank**：将RRF融合后的Top-K送入LLM进行语义精排，返回最终结果

```
流程：query → embedding(1536d) → 各表ANN检索 → RRF融合 → LLM Rerank → top_k结果
```

---

## 三、岗位画像向量策略（§7.2.1）

### 增量更新

- **触发条件**：JD字段（title, required_skills, profile_summary, profile_keywords, jd_text）修改时
- **执行方式**：实时异步更新向量

### 全量重建

- **触发条件**：
  1. Embedding模型版本变更
  2. 季度向量质量审计发现漂移
  3. 管理员手动触发
  4. 岗位需求大幅调整
- **执行方式**：通过 `POST /api/v1/positions/rebuild-vectors` 批量触发，ARQ异步任务执行（§8.1c）
- **岗位向量生命周期**：岗位发布时生成向量进入pgvector匹配池

---

## 四、候选人向量策略（§7.2.3）

### 增量更新

- **触发条件**：新数据写入画像时（简历解析、面试反馈、HR手动标注等）
- **执行方式**：异步更新画像向量

### 全量重建

- **触发条件**（统一触发条件）：
  1. Embedding模型版本变更
  2. 季度向量质量审计发现漂移
  3. 管理员手动触发
- **执行方式**：ARQ异步任务执行（§8.1c）

### 冷启动策略

首次投递无画像时，用简历向量做初始筛选，5-15分钟异步构建画像后切换到画像向量。

---

## 五、混合检索架构（RAG + LLM Rerank）

### 两阶段检索流程

**第一阶段（向量召回）**：
- pgvector HNSW + SQ8 向量检索
- PG tsvector 全文检索
- RRF (Reciprocal Rank Fusion) 融合两路结果

**第二阶段（LLM精排）**：
- gpt-4.1 对 Top-30 候选重排序
- 输出 Top-10 + 匹配解释

**预期效果**：Top-10命中率从纯向量60% → 75%+，中文技能名称检索准确率显著提升

### Phase规划

- **Phase 1**：pgvector + 基础tsvector
- **Phase 2**：引入zhparser中文分词优化

---

## 六、HNSW索引配置

### 索引参数

| 参数 | 值 | 说明 |
|------|-----|------|
| ef_construction | 128 | 构建时搜索宽度（越大越精确，构建越慢） |
| m | 24 | 每个节点的连接数（越大越精确，内存越多） |

### 各表HNSW索引

每张需要向量检索的表维护独立的HNSW索引：

- **positions**（岗位画像向量）— `embedding_id` 关联
- **candidates**（人才画像向量）— `embedding_id` 关联

索引创建示例：

```sql
-- 岗位向量索引（Phase 1，embedding维度1536）
CREATE INDEX idx_positions_embedding ON positions
  USING hnsw (embedding vector_cosine_ops)
  WITH (ef_construction = 128, m = 24);

-- 候选人向量索引（Phase 1，embedding维度1536）
CREATE INDEX idx_candidates_embedding ON candidates
  USING hnsw (embedding vector_cosine_ops)
  WITH (ef_construction = 128, m = 24);
```

> 注：PRD中向量存储使用 `embedding_id VARCHAR(255)` 关联pgvector行ID，实际向量数据存储在pgvector扩展的向量列中。

---

## 七、匹配性能目标分解（Top20 < 15s）

| 步骤 | 目标 | 依据 |
|------|------|------|
| pgvector HNSW检索Top50 | < 3s | 10万向量×1536维，HNSW ef=200基准 |
| tsvector全文检索 | < 1s | PG原生GIN索引 |
| RRF融合+重排 | < 1s | 内存计算 |
| LLM Rerank Top20 | < 8s | gpt-4.1-mini批量评分 |
| 结果写入+缓存 | < 2s | DB写入+Redis缓存 |
| **合计** | **< 15s** | — |

---

## 八、业务索引策略

### positions 表索引

```sql
CREATE INDEX idx_positions_department ON positions(department_id);
CREATE INDEX idx_positions_status     ON positions(status);
CREATE INDEX idx_positions_tenant     ON positions(tenant_id);
```

### candidates 表索引

```sql
CREATE INDEX idx_candidates_email_hash ON candidates(email_hash);  -- 去重查询
CREATE INDEX idx_candidates_status     ON candidates(status);
CREATE INDEX idx_candidates_tenant     ON candidates(tenant_id);
-- UNIQUE (phone_hash, email_hash) -- 去重组合唯一约束
```

### matches 表索引

```sql
CREATE INDEX idx_matches_position  ON matches(position_id);
CREATE INDEX idx_matches_candidate ON matches(candidate_id);
CREATE INDEX idx_matches_status    ON matches(status);
CREATE INDEX idx_matches_score     ON matches(overall_score DESC);  -- 排序查询
-- UNIQUE (position_id, candidate_id) -- 对称唯一约束
```

### interviews 表索引

```sql
CREATE INDEX idx_interviews_position   ON interviews(position_id);
CREATE INDEX idx_interviews_candidate  ON interviews(candidate_id);
CREATE INDEX idx_interviews_status     ON interviews(status);
CREATE INDEX idx_interviews_scheduled  ON interviews(scheduled_at);
CREATE INDEX idx_interviews_decision   ON interviews(decision) WHERE decision IS NOT NULL;  -- 部分索引
CREATE INDEX idx_interviews_stage      ON interviews(stage);
```

### resumes 表索引

```sql
CREATE INDEX idx_resumes_candidate  ON resumes(candidate_id);
CREATE INDEX idx_resumes_position   ON resumes(position_id);
CREATE INDEX idx_resumes_parse      ON resumes(parse_status);
CREATE INDEX idx_resumes_tenant     ON resumes(tenant_id);
```

### offers 表索引

```sql
CREATE INDEX idx_offers_position  ON offers(position_id);
CREATE INDEX idx_offers_candidate ON offers(candidate_id);
CREATE INDEX idx_offers_status    ON offers(status);
```

### conflict_resolutions 表索引

```sql
CREATE INDEX idx_conflict_candidate ON conflict_resolutions(candidate_id);
CREATE INDEX idx_conflict_unresolved ON conflict_resolutions(candidate_id) WHERE resolved_at IS NULL;  -- 部分索引，仅查未解决
```

### ai_decisions 表索引

```sql
-- (tenant_id, decision_type, created_at) 联合索引
-- (session_id) 索引
```

### onboarding_tasks 表索引

```sql
CREATE INDEX idx_onboarding_tasks_offer ON onboarding_tasks(offer_id);
CREATE INDEX idx_onboarding_tasks_status ON onboarding_tasks(status);
CREATE INDEX idx_onboarding_tasks_due ON onboarding_tasks(due_date);
```

### 其他表索引

```sql
-- match_feedback
CREATE INDEX idx_match_feedback_match ON match_feedback(match_id);
CREATE INDEX idx_match_feedback_tenant ON match_feedback(tenant_id);

-- share_links
CREATE INDEX idx_share_links_token ON share_links(token);
CREATE INDEX idx_share_links_resource ON share_links(resource_type, resource_id);

-- users
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

---

## 九、向量空间多租户隔离

- 向量空间按 `tenant_id` 分片（pgvector条件索引）
- Phase 2 启用 PostgreSQL RLS Policy 强制隔离：

```sql
-- Phase 2 RLS实现
CREATE POLICY tenant_isolation ON positions
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

---

## 十、候选人数据删除级联（pgvector级联）

| 阶段 | 操作 | 时间 |
|------|------|------|
| 软删除 | 标记 `candidates.deleted_at`，前端不可见 | 收到请求后立即 |
| 保留期 | 进行中的面试/Offer不可删除，先完成或取消 | 7天内完成 |
| 硬删除 | 物理清除所有关联数据（resumes/matches/interviews/offers/**pgvector向量**/MinIO文件） | 软删除后7天内 |
| pgvector级联 | 删除候选人对应的embedding向量行（`DELETE FROM candidate_embeddings WHERE candidate_id = :id`），确保向量数据不可恢复 | 与硬删除同步执行 |
| AI记忆 | 标记Memory引用为"数据已删除"，不清除Memory | 软删除后7天内 |
| 已入职 | 仅可删除简历原文，保留脱敏画像数据 | — |
