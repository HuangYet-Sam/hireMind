# Prompt版本管理规范

> **PRD来源**：§5.9 Prompt版本管理规范（L3211-L3282）、§5.3 核心AI能力Prompt策略（L2853-L2869）
> **更新日期**：2026-05-12

---

## 1. Prompt文件组织规范（§5.9）

### 1.1 目录结构

```
prompts/
├── position/              # 岗位Service
│   └── generate_jd_v1.yaml    # #1 JD智能生成Prompt
├── matching/              # 人岗匹配Service
│   ├── rerank_v1.yaml     # LLM精排Prompt
│   ├── explain_v1.yaml    # 匹配解释Prompt
│   └── enhance_match_v1.yaml  # #18 匹配推理增强Prompt
├── resume/                # 简历解析Service
│   ├── parse_v1.yaml      # 结构化抽取Prompt
│   └── verify_credibility_v1.yaml
├── interview/             # 面试Service
│   ├── generate_questions_v1.yaml
│   ├── evaluate_v1.yaml
│   ├── generate_briefing_v1.yaml
│   ├── analyze_recording_v1.yaml
│   └── generate_report_v1.yaml   # #21 面试分析报告Prompt
├── offer/                 # Offer Service
│   ├── generate_v1.yaml
│   └── benchmark_v1.yaml
├── analytics/             # 分析Service
│   └── generate_insights_v1.yaml  # #10 数据洞察Prompt
├── notification/          # 主动通知Service
│   └── proactive_notify_v1.yaml   # #13 主动通知推送Prompt
└── profile/               # 画像Service
    ├── build_profile_v1.yaml
    ├── recommend_v1.yaml
    └── infer_potential_v1.yaml
```

### 1.2 命名规则

```
prompts/{service}/{ability}_v{N}.yaml
```

### 1.3 YAML结构

```yaml
version: "v1"
ability: "rerank"
service: "matching"
model_target: "gpt-4.1"
system_prompt: "..."
user_prompt_template: "..."
output_schema: { }  # JSON Schema约束
few_shots: [ ]       # Few-shot示例
metadata:
  author: "team"
  created_at: "2026-05-10"
  changelog: "初始版本"
```

---

## 2. Golden Dataset回归门禁

| 规则 | 要求 |
|------|------|
| 标注样本量 | 每项AI能力至少20条标注样本（含输入+期望输出） |
| 存储位置 | `tests/golden_datasets/{ability}/` 目录 |
| CI门禁 | PR合并前自动运行Golden Dataset回归测试 |
| 通过标准 | 输出与期望结果的语义相似度≥0.85（embedding余弦相似度） |
| 回归检测 | Prompt变更导致任意样本评分下降>5%时阻断合并 |

---

## 3. 版本追踪链

```
Prompt YAML (v1) → ai_decisions.prompt_version = "rerank_v1" → 审计可追溯
Prompt变更(v2) → Golden Dataset回归 → CI通过 → 合并 → 新决策记录"rerank_v2"
```

每条AI决策记录（`ai_decisions`表）自动关联使用的Prompt版本，支持：
- 按Prompt版本筛选决策历史
- Prompt变更前后AI质量对比
- 合规审计时追溯决策依据

---

## 4. 各能力Prompt策略总览（§5.3扩展）

| # | AI能力 | Prompt策略核心 | 目标模型 |
|---|--------|--------------|---------|
| 1 | JD智能生成 | 结构化JD模板+行业Few-shot+JSON Schema输出 | gpt-4.1-mini |
| 2 | 简历AI解析 | JSON Schema约束输出+字段溯源标记+Few-shot示例 | gpt-4.1-mini |
| 3 | 人才画像构建 | 多源融合Prompt（简历+面试+评估→结构化画像） | gpt-4.1-mini |
| 4 | 人岗智能匹配 | 向量Top50召回→LLM精排（JSON Schema+评分标准+溯源） | gpt-4.1 |
| 5 | 匹配解释生成 | 分维度差距分析Prompt+因果推理 | gpt-4.1-mini |
| 6 | 面试问题生成 | 岗位-候选人差距→针对性出题Prompt | gpt-4.1-mini |
| 7 | 面试评分结构化 | 结构化提取Prompt（评分+关键观察+推荐决策） | gpt-4.1-mini |
| 8 | 候选人推荐评语 | 综合画像+岗位+团队风格→推荐理由生成 | gpt-4.1-mini |
| 9 | Offer方案建议 | 市场数据Prompt+候选人画像+内部薪酬结构 | gpt-4.1 |
| 10 | 招聘数据洞察 | 趋势分析+行动建议Prompt | gpt-4.1-mini |
| 14 | 简历可信度检测 | 三层验证Prompt（内部一致性+跨简历一致性+外部合理性） | gpt-4.1 |
| 15 | 薪资对标分析 | 分位计算+内部公平性检验Prompt | gpt-4.1-mini |
| 16 | 漏斗瓶颈诊断 | 通过率趋势+失败维度聚合+根因分析CoT Prompt | gpt-4.1 |
| 17 | 候选人隐性推理 | CoT推理链Prompt：已知→推断→依据→置信度 | gpt-4.1 |
| 18 | 岗位匹配推理增强 | 明面匹配+推理匹配双轨评分Prompt | gpt-4.1 |
| 19 | 面试考察清单生成 | 差距分析Prompt+结构化考察要点+面试题+追问策略 | gpt-4.1 |
| 20 | 面试录音分析 | faster-whisper转写→LLM多维分析Prompt | gpt-4.1 |
| 21 | 面试分析报告 | 综合评估Prompt→多维度分析→录用建议 | gpt-4.1 |

---

## 5. Prompt安全规范（关联§5.7）

所有LLM调用采用严格的三段式Prompt结构：

```
[System Prompt] — 不可被用户输入覆盖的角色定义、安全规则、输出格式约束
<user_input>
[经净化的用户输入内容，被明确分隔符包裹]
</user_input>
[System Prompt Tail] — 安全兜底指令
```

- `<user_input>...</user_input>` 分隔符在System Prompt中声明语义边界
- 用户输入中的分隔符标签在净化阶段被转义
- 新Prompt版本上线前必须通过注入防御回归测试
