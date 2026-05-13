# AI能力端点（调Service+LLM，1-30s）

> **PRD来源**：§9.1 AI能力端点、§8.1a 双路径优化方案（@AiCapability装饰器规格）、§9.1 Agent独占端点

---

## 1. AI能力端点清单

| 方法 | 端点 | 描述 | Service方法 | 装饰器name | Tool注册名 |
|------|------|------|------------|------------|------------|
| POST | `/api/v1/positions/:id/generate-jd` | AI生成JD | `position_service.generate_jd()` | `generate_jd` | `generate_jd` |
| POST | `/api/v1/positions/:id/vectorize` | 岗位向量化 | `position_service.vectorize()` | `vectorize` | `vectorize` |
| POST | `/api/v1/resumes/:id/parse` | AI解析简历 | `resume_service.parse()` | `parse_resume` | `parse_resume` |
| POST | `/api/v1/candidates/:id/recommend` | AI推荐评语 | `candidate_service.recommend()` | `recommend_candidate` | `recommend_candidate` |
| POST | `/api/v1/candidates/:id/build-profile` | 构建人才画像 | `candidate_service.build_profile()` | `build_profile` | `build_profile` |
| POST | `/api/v1/matching/run` | 执行智能匹配 | `matching_service.run()` | `run_matching` | `run_matching` |
| GET | `/api/v1/matches/:id/explain` | 匹配解释 | `matching_service.explain()` | `explain_match` | `explain_match` |
| POST | `/api/v1/matching/reverse` | 反向匹配（人→岗位） | `matching_service.reverse()` | `reverse_matching` | `reverse_matching` |
| POST | `/api/v1/interviews/:id/generate-questions` | AI生成面试题 | `interview_service.generate_questions()` | `generate_questions` | `generate_questions` |
| POST | `/api/v1/interviews/:id/evaluate` | AI面试分析报告（含评分+发现+风险+录用建议） | `interview_service.generate_report()` | `evaluate_interview` | `evaluate_interview` |
| POST | `/api/v1/interviews/:id/structure-score` | 面试评分结构化 | `interview_service.structure_score()` | `structure_score` | `structure_score` |
| POST | `/api/v1/interviews/:id/briefing` | AI面试考察清单（面试前自动生成） | `interview_service.generate_briefing()` | `generate_briefing` | `generate_briefing` |
| GET | `/api/v1/interviews/:id/verification-checklist` | AI待验证清单（简历可信度+冲突项） | `interview_service.get_verification_checklist()` | `verification_checklist` | `verification_checklist` |
| POST | `/api/v1/interviews/:id/recording/upload` | 面试录音/视频上传 | `interview_service.upload_recording()` | `upload_recording` | `upload_recording` |
| POST | `/api/v1/interviews/:id/analyze` | AI录音分析（faster-whisper转写+LLM多维分析） | `interview_service.analyze_recording()` | `analyze_recording` | `analyze_recording` |
| GET | `/api/v1/interviews/:id/transcript` | 获取面试录音转写文本 | `interview_service.get_transcript()` | `get_transcript` | `get_transcript` |
| POST | `/api/v1/interviews/batch` | 批量排期 | `interview_service.batch_create()` | `batch_interview` | `batch_interview` |
| POST | `/api/v1/resumes/:id/verify` | AI简历可信度检测 | `resume_service.verify_credibility()` | `verify_resume` | `verify_resume` |
| POST | `/api/v1/resumes/batch-parse` | 批量简历解析 | `resume_service.batch_parse()` | `batch_parse` | `batch_parse` |
| POST | `/api/v1/candidates/:id/infer` | AI候选人隐性推理 | `candidate_service.infer_potential()` | `infer_potential` | `infer_potential` |
| GET | `/api/v1/candidates/:id/inferences` | 获取推理结果 | `candidate_service.get_inferences()` | `get_inferences` | `get_inferences` |
| POST | `/api/v1/candidates/:id/resolve-conflict` | HR裁决数据冲突 | `candidate_service.resolve_conflict()` | `resolve_conflict` | `resolve_conflict` |
| GET | `/api/v1/candidates/:id/conflicts` | 获取未裁决冲突列表 | `candidate_service.get_conflicts()` | `get_conflicts` | `get_conflicts` |
| POST | `/api/v1/candidates/:id/inferences/merge` | 将推理结果合并到画像 | `candidate_service.merge_inferences()` | `merge_inferences` | `merge_inferences` |
| GET | `/api/v1/analytics/dashboard` | 全局分析仪表盘 | `analytics_service.get_dashboard()` | `analytics_dashboard` | `analytics_dashboard` |
| GET | `/api/v1/analytics/position-health` | 岗位健康度分析 | `analytics_service.position_health()` | `position_health` | `position_health` |
| GET | `/api/v1/offers/:id/compensation-benchmark` | Offer薪资对标 | `offer_service.benchmark()` | `benchmark_offer` | `benchmark_offer` |
| POST | `/api/v1/offers/generate` | AI生成Offer方案 | `offer_service.generate()` | `generate_offer` | `generate_offer` |
| POST | `/api/v1/offers/:id/negotiation-advice` | AI谈判策略 | `offer_service.negotiate()` | `generate_negotiation_advice` | `hr_offer_negotiate` |
| POST | `/api/v1/analytics/insights` | AI数据洞察 | `analytics_service.generate_insights()` | `generate_insights` | `generate_insights` |
| POST | `/api/v1/analytics/funnel-diagnosis` | 漏斗瓶颈诊断 | `analytics_service.diagnose_funnel()` | `diagnose_funnel` | `diagnose_funnel` |
| POST | `/api/v1/matching/:id/explain` | 匹配推理增强 | `matching_service.infer_match()` | `enhance_match` | `hr_matching` |
| POST | `/api/v1/matches/:id/feedback` | 匹配反馈收集 | `match_feedback_service.submit()` | `submit_match_feedback` | `hr_match_feedback` |
| GET | `/api/v1/matches/feedback-stats` | 匹配反馈统计 | `match_feedback_service.get_stats()` | `get_match_feedback_stats` | `hr_match_feedback_stats` |
| POST | `/api/v1/analytics/org-health` | **AI组织架构用人分析** | `analytics_service.org_health_analysis()` | `org_health_analysis` | `org_health_analysis` |
| POST | `/api/v1/analytics/org-health/:dept_id` | **AI单部门用人分析** | `analytics_service.dept_health_analysis()` | `dept_health_analysis` | `dept_health_analysis` |
| GET | `/api/v1/insights` | Context Bar上下文洞察（**P1-02修复：走FastAPI直出，不走Koa BFF**） | `analytics_service.get_context_insights()` | `get_context_insights` | `get_context_insights` |

---

## 2. Agent独占端点（allowed_callers=["tool"]，无Web入口）

> ⚠️ **C-03修复**：以下4项Agent独占能力无Web端点，仅在Agent Loop内部通过Tool直接调用Service方法。`allowed_callers=["tool"]`确保无法通过HTTP直接访问。

| 方法 | 路径 | AI能力 | Service方法 | 装饰器name |
|------|------|--------|-------------|-----------|
| internal | agent/nl-search | #11自然语言搜索 | `agent_service.nl_search()` | nl_search |
| internal | agent/orchestrate | #12多步编排 | `agent_service.orchestrate()` | orchestrate |
| POST | /api/v1/notifications/proactive | #13主动通知 | `notification_service.proactive_push()` | proactive_push |
| internal | agent/partial-reason | #17部分推理 | `agent_service.partial_reason()` | partial_reason |

---

## 3. @AiCapability装饰器规格

> **PRD来源**：§8.1a.2 @AiCapability装饰器设计

### 3.1 装饰器示例

```python
@AiCapability(
    name="generate_jd",               # 唯一标识（FastAPI路由名+Tool注册名）
    endpoint="/api/v1/positions/:id/generate-jd",  # FastAPI端点路径
    method="POST",                     # HTTP方法
    tool_name="hr_position",           # 所属Tool模块
    permissions=["position:write"],    # 所需权限
    timeout=30,                        # 超时(秒)
    llm_model="gpt-4.1",              # 默认LLM模型
    fallback_model="gpt-4.1-mini",    # 降级模型
    prompt_version="jd-gen-v1.2",     # Prompt版本号
    allowed_callers=["api", "tool"],   # 允许的调用路径
    requires_tenant_isolation=True,    # 需要租户隔离
    ai_capability_id=1,               # §5.3 AI能力矩阵编号
    description="AI生成岗位JD",        # 人类可读描述
)
async def generate_jd(self, tenant_id: UUID, user_id: UUID, 
                      position_id: UUID, caller_type: Literal["tool", "api"] = "api") -> JDResult:
    ...
```

### 3.2 装饰器21字段完整定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| name | str | ✅ | 唯一标识，同时作为FastAPI路由函数名和Tool方法名 |
| endpoint | str | ✅ | FastAPI端点路径（含/api/v1前缀） |
| method | str | ✅ | HTTP方法（POST/GET） |
| tool_name | str | ✅ | 所属Tool模块名 |
| permissions | list[str] | ✅ | 所需权限列表 |
| timeout | int | ✅ | 超时秒数 |
| llm_model | str | ✅ | 默认LLM模型 |
| fallback_model | str | ❌ | 降级模型（None=无降级） |
| prompt_version | str | ❌ | Prompt版本号 |
| allowed_callers | list[str] | ✅ | 允许的调用路径["api","tool"]或仅["tool"] |
| requires_tenant_isolation | bool | ✅ | 是否需要租户隔离 |
| ai_capability_id | int | ✅ | §5.3 AI能力矩阵编号 |
| description | str | ✅ | 人类可读描述 |
| request_model | str | ❌ | Pydantic请求模型类名 |
| response_model | str | ❌ | Pydantic响应模型类名 |
| cache_ttl | int | ❌ | 缓存TTL秒数（0=不缓存） |
| rate_limit | str | ❌ | 速率限制（如"10/min"） |
| data_classification | str | ❌ | 数据分级（L1-L4） |
| audit_level | str | ❌ | 审计级别（full/summary/none） |
| tags | list[str] | ❌ | 标签（用于分组和过滤） |

### 3.3 Service签名规范

> **PRD来源**：§8.1a.3 Service签名规范

所有AI能力Service方法遵循统一签名：

```python
async def method_name(
    self,
    tenant_id: UUID,           # 首位：租户ID（装饰器自动注入）
    user_id: UUID,             # 首位：用户ID（装饰器自动注入）
    *,                         # 关键字参数分隔
    # 业务参数（与request_model一一对应）
    ...
    caller_type: Literal["tool", "api"] = "api",  # 末位：调用来源（生成器硬编码）
) -> ResponseModel:
```

### 3.4 代码生成器

> **PRD来源**：§8.1a.4 代码生成器

- **生成策略**：静态代码生成（Jinja2模板），非运行时反射
- **命令**：`python -m hiremind.codegen generate`
- **产物**：`generated/routes/`（FastAPI路由）+ `generated/tools/`（Tool注册）
- **CI门禁**：`make generate && git diff --exit-code generated/`
- **漂移检测**：生成代码文件头含`# ⚠️ AUTO-GENERATED — DO NOT EDIT`警告标记
- **安全校验**：SecurityValidationHook在生成后自动校验权限字段完整性

### 3.5 一致性保障（四层防线）

> **PRD来源**：§8.1a.5 一致性保障

| 层级 | 机制 | 阶段 | 说明 |
|------|------|------|------|
| L1设计时 | @AiCapability装饰器 = SSOT | 编码 | 接口定义只写一次 |
| L2编译时 | Pydantic类型约束 + CI diff检查 | CI/CD | 生成代码与Service签名不匹配时CI失败 |
| L3测试时 | 双路径一致性测试套件（参数化33端点） | 测试 | 同一Service方法走两条路径结果一致 |
| L4运行时 | OTel双路径指标 + 告警 | 生产 | 路径差异率>1%触发告警 |

### 3.6 21项AI能力路径归属

> **PRD来源**：§8.1a.6 21项AI能力路径归属

| 归属 | 能力数 | 说明 |
|------|:------:|------|
| 共享（allowed_callers=["api","tool"]） | 17 | JD生成/简历解析/匹配/面试分析/画像推理等 |
| Agent独占（allowed_callers=["tool"]） | 4 | 自然语言搜索(#11)/多步编排(#12)/主动通知(#13)/Skill流程编排 |

---

## 4. Context Bar端点完整Schema（P1-02修复）

> Context Bar洞察端点由FastAPI直出（`/api/v1/insights`），内部调用Hermes API Server获取Agent洞察结果。**不走Koa BFF**，消除架构歧义。

```yaml
# 请求参数
GET /api/v1/insights?entity_type=candidate&entity_id=123&tab=profile&force_refresh=false

# 请求参数Schema
params:
  entity_type:   # required, enum: [candidate, position, interview, offer]
  entity_id:     # required, UUID
  tab:           # required, string - 当前激活Tab名
  force_refresh: # optional, boolean, default false - 强制刷新绕过缓存

# 响应Schema (200 OK)
response:
  entity_type: "candidate"
  entity_id: "uuid-xxx"
  tab: "profile"
  insights:
    - id: "insight-uuid-1"
      type: "summary"           # enum: summary | recommendation | warning
      priority: "high"          # enum: high | medium | low
      content: "张三Java匹配架构师92%，但项目管理仅1年Lead"
      confidence: 0.92
      actions:
        - label: "为什么92%?"
          trigger: "sidecar"    # 点击展开Sidecar
          prompt: "为什么张三匹配度是92%？详细分析差距"
        - label: "详细分析"
          trigger: "sidecar"
          prompt: "展开张三的完整匹配分析"
  cache:
    hit: true                   # 是否缓存命中
    expires_at: "2026-05-10T05:30:00Z"  # 缓存过期时间(5min)
    ai_call_weight: 0.5         # P1-03: AI调用降权计为0.5次

# 响应Schema (404 - 实体不存在)
error_response:
  code: "ENTITY_NOT_FOUND"
  message: "候选人不存在"

# 响应Schema (422 - 参数校验失败)
error_response:
  code: "INVALID_PARAMS"
  message: "entity_type必须是candidate|position|interview|offer"
```

> **内部调用链**：FastAPI `GET /api/v1/insights` → Redis缓存查询 → (缓存未命中时) Hermes API Server `POST /v1/chat/completions`(Agent Session) → Agent调用insight Skill → 返回结构化洞察 → 写入Redis(5min TTL) → 返回前端
