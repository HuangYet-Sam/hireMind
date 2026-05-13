# RAG架构与复用扩展 (RAG Pipeline)

> **PRD来源**：§5.10 RAG复用扩展计划（L3282-L3336）、§12 技术选型-RAG架构（L6388-L6472）、§12.0a LLM选型-Embedding维度决策（L6527-L6557）
> **更新日期**：2026-05-12

---

## 1. RAG复用扩展计划（§5.10）

> **新增于**：P1-10 AI架构修复 | **用途**：将RAG架构从仅匹配检索扩展至JD生成、面试题生成等高频AI能力

### 1.1 现状问题

当前RAG架构（§12 混合检索+LLM Rerank）仅用于人岗智能匹配（AI能力#4），JD生成（#1）、面试问题生成（#6）、Offer方案建议（#9）等6项高频AI能力均为纯LLM生成，未复用历史数据，Token消耗高且输出一致性不足。

### 1.2 `retrieve_rerank()`通用方法

> **P1-20修复**：原`retrieve_rerank()`参数签名不完整，缺少跨表检索对齐方案。

```python
async def retrieve_rerank(
    query: str,
    tenant_id: UUID,
    entity_types: list[str],     # 检索实体类型（如["positions", "candidates", "interviews"]）
    similarity_threshold: float = 0.7,  # 向量相似度过滤阈值
    rerank_model: str = "gpt-4.1-mini", # Rerank使用的LLM模型
    top_k: int = 10,                     # 最终返回结果数
    # 向下兼容旧参数
    source_tables: list[str] | None = None,  # 兼容旧调用方式，内部映射到entity_types
    rerank: bool = True,
) -> list[dict]:
    """通用检索+重排方法，供多AI能力复用
    
    跨表检索对齐方案：
    1. 统一embedding维度(1536)：所有表使用text-embedding-3-small生成1536维向量
    2. 各表独立pgvector索引：每张表维护独立HNSW索引（ef_construction=128, m=24）
    3. 合并检索：对各entity_type分别执行pgvector ANN检索，取各表Top-K结果
    4. RRF融合：对多表结果执行Reciprocal Rank Fusion（k=60），合并为统一排序
    5. LLM Rerank：将RRF融合后的Top-K送入LLM进行语义精排，返回最终结果
    
    流程：query → embedding(1536d) → 各表ANN检索 → RRF融合 → LLM Rerank → top_k结果
    """
    # 1. 向量检索: pgvector HNSW + tsvector RRF融合
    # 2. 可选LLM Rerank
    # 3. 返回top_k结果
```

### 1.3 RAG复用路线图

| 里程碑 | 交付内容 | 复用AI能力 | 预期收益 |
|--------|---------|-----------|---------|
| **M2** | `retrieve_rerank()`通用Service方法上线 | 匹配检索（已接入） | 方法抽象化，统一检索入口 |
| **M3** | JD生成复用RAG | JD智能生成(#1) | Few-shot RAG：检索历史相似岗位JD作为参考，Token消耗降50%，JD质量更一致 |
| **M3** | 面试题生成复用RAG | 面试问题生成(#6) | Context RAG：检索历史面试题+反馈数据，题目针对性提升 |
| **M4** | Offer薪资建议复用RAG | Offer方案建议(#9) | 参考RAG：检索历史相似候选人Offer，薪资建议更合理 |

### 1.4 预期效果

- Token消耗降低50%（RAG提供上下文替代长Prompt）
- JD/面试题输出一致性提升（基于历史优质样本）
- `retrieve_rerank()`一处实现，多处复用，维护成本低

---

## 2. RAG架构技术选型（§12）

### 2.1 混合检索RRF架构

**两阶段检索架构**（P0-04）：

| 阶段 | 方案 | 说明 |
|------|------|------|
| 第一阶段（向量召回） | pgvector HNSW+SQ8向量检索 + PG tsvector全文检索 | RRF(Reciprocal Rank Fusion)融合两路结果 |
| 第二阶段（LLM精排） | gpt-4.1对Top-30候选重排序 | 输出Top-10+匹配解释 |

**预期效果**：
- Top-10命中率从纯向量60%→75%+
- 中文技能名称检索准确率显著提升
- Phase 1先用pgvector+基础tsvector，Phase 2引入zhparser中文分词优化

### 2.2 向量数据库选型

| 组件 | 版本 | 用途 | 选型理由 |
|------|------|------|---------|
| **pgvector** | 0.8+ | 向量索引+相似检索 | HNSW索引+SQ8量化，召回率>99%，内存降75% |
| **pgvectorscale** | latest | 大规模向量检索 | StreamingDiskANN索引，Phase 2百万级扩展路径 |

---

## 3. Embedding维度决策（§12.0a）

> 原方案3072维(text-embedding-3-large)对中小企业场景过度设计。

### 3.1 维度对比

| 维度 | Phase 1（默认） | Phase 2（升级路径） |
|------|----------------|-------------------|
| 模型 | text-embedding-3-small | text-embedding-3-large |
| 维度 | **1536维** | 3072维 |
| 内存预估 | 10万×1536维×4bytes ≈ **800MB**（单机可承受） | 10万×3072维×4bytes ≈ 1.6GB |
| 检索质量 | Top-10命中率≥70% | Top-10命中率≥75%（+5%） |
| 升级方式 | — | `ALTER TABLE` + 重建HNSW索引，无需改代码 |

### 3.2 Phase 1采用1536维的理由

1. 中小企业候选人库<10万，1536维区分度足够
2. 800MB内存单机部署无压力，降低硬件门槛
3. text-embedding-3-small API成本更低
4. 预留3072维无损升级路径（text-embedding-3-large原生支持维度截断）

### 3.3 中文Embedding质量验证计划（P1-22修复）

> ⚠️ text-embedding-3-small主要针对英文优化，中文适用性未论证。招聘场景核心数据均为中文，需验证中文场景下Embedding质量。

**M0基建增加中文Embedding质量基准测试**：

| 测试项 | 内容 | 通过标准 | 失败处置 |
|--------|------|---------|---------|
| **100对中文技能相似度标注基准** | 人工标注100对中文技能描述的语义相似度(0-5分)，涵盖：同义词("Java开发"/"Java工程师")、上下位("微服务"/"Spring Cloud")、无关对("前端"/"财务") | Top-10检索准确率≥65% | **切换BGE-M3**（BAAI开源中文Embedding模型，1536维对齐，MTEB中文榜单Top3） |
| **中文简历片段检索** | 50段真实中文简历摘要作为查询，验证同类经验描述的召回率 | Top-5召回率≥80% | 同上 |
| **中文JD-简历跨域匹配** | 30条中文JD需求 vs 100份中文简历摘要，验证岗位需求→候选人检索质量 | MRR@10≥0.6 | 同上 |

**切换路径**：若基准测试未通过 → `embedding_service.py` 将`text-embedding-3-small`替换为`BGE-M3`（通过LiteLLM的`embedding`模块统一调用，仅改配置不改代码）→ 重新执行pgvector全量重建 → 预计迁移耗时2小时（10万向量）。

---

## 4. LLM选型与RAG架构关联（§12.0a）

### 4.1 LiteLLM Router按任务类型动态选模型

| 任务类型 | 首选模型 | 降级链 | 说明 |
|---------|---------|--------|------|
| 匹配精排/推理增强 | gpt-4.1 | → Gemini 2.5 Pro → Qwen3-72B | 需要最强推理能力 |
| 常规生成/解析 | gpt-4.1-mini | → Gemini 2.5 Flash → Qwen3-72B | 成本优先 |
| 国内合规场景 | Qwen3-72B | Qwen3不可用→直接进入Rule级兜底 | 金融/政企客户，不反向降级到境外模型 |
| 面试录音转写后分析 | gpt-4.1 | → Gemini 2.5 Pro | 长上下文理解 |

### 4.2 四模型对比（RAG相关维度）

| 维度 | gpt-4.1 | Claude Sonnet 4 | Gemini 2.5 Pro | Qwen3-72B（自部署） |
|------|---------|-----------------|----------------|---------------------|
| **中文理解** | F1≈0.88 / BLEU≈0.72 | F1≈0.90 / BLEU≈0.75 | F1≈0.86 / BLEU≈0.70 | F1≈0.91 / BLEU≈0.78 |
| **成本（$/1M tokens）** | $2.00/$8.00 | $3.00/$15.00 | $1.25/$10.00 | ¥0（自部署，GPU成本¥3-5/h） |
| **延迟（P95）** | ~8s | ~10s | ~6s | ~15s（自部署） |
| **结构化输出** | 99.9%可靠 | 99.5%可靠 | 99%可靠 | 98%可靠 |
| **综合评分** | **88分** | 85分 | 83分 | 80分 |
