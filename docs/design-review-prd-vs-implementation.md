# HireMind PRD V3.6 vs 实际代码实现 — 全面设计审查报告

> 审查人：资深产品架构师 + 技术负责人
> 审查日期：2026-05-18
> PRD 版本：V3.6（7754行，含13轮研讨成果）
> 代码基准：28 commits，157 files changed

---

## 一、PRD 核心设计规格量化提取

### §4 功能需求规格

**功能全景**：
- 10个自研业务页面 + 15个hermes-web-ui复用管理页面
- 21项AI能力（通过Service层LLM方法实现）
- 7大核心功能模块：F1组织架构、F2简历库、F3候选人管理、F4智能匹配、F5面试管理、F6 Offer管理、F7招聘分析

**核心页面清单（15个）**：
- 工作台 /hr/dashboard（系统首页，P0）
- AI任务中心 /hr/tasks（P0）
- 岗位管理 /hr/positions + 岗位360°视图 /hr/positions/:id
- 简历库 /hr/resumes + 简历详情 /hr/resumes/:id
- 候选人管理 /hr/candidates + 候选人360° /hr/candidates/:id
- 智能匹配 /hr/matching
- 面试管理 /hr/interviews + 面试详情 /hr/interviews/:id
- Offer管理 /hr/offers + Offer详情 /hr/offers/:id
- 招聘分析 /hr/analytics
- 组织架构 /hr/org-chart

**状态机清单（3个核心）**：
- 岗位：draft → open → paused → closed → filled
- 匹配：pending → screening → shortlisted → interview_scheduled → interviewed → offered → hired → rejected → withdrawn（非线性有向图）
- Offer：draft → pending_approval → approved → offered → accepted/rejected/counter_offered → hired → onboarded

### §7 数据模型规格

**PRD定义的表清单（13+张）**：
- 5大核心表：positions, candidates, matches, interviews, resumes
- 3个基础表：departments, users, tenants
- 5+扩展表：offers, onboarding_tasks, profile_updates, conflict_resolutions, match_feedback, share_links, audit_logs, ai_decisions, consent_records, im_user_bindings, evaluation_templates, channels
- 特殊要求：candidates表email/phone/name_encrypted字段AES-256加密、offers表salary_encrypted加密

### §8 系统架构规格

**关键设计要素**：
- 双路径架构：FastAPI端点 + Agent Tool → 共享Service层
- @AiCapability装饰器：21字段元数据声明（PRD V3.5新增SSOT机制）
- 代码生成器：Jinja2静态生成FastAPI路由 + Tool注册
- 12个HR Tools：hr_resume, hr_profile, hr_matching等
- 8个招聘Skills：hr-daily-briefing, hr-candidate-screen等
- 异步任务架构：ARQ任务队列 + SSE进度通知
- Master-Worker Agent编排模式

### §9 API 设计规格

**PRD定义端点总数（约90+个）**：
- 确定性CRUD端点（§9.1）：约40个
- Dashboard端点：4个
- AI任务中心端点：8个
- AI能力端点：约35个
- Agent独占端点：4个
- 主动式AI端点：4个
- Koa BFF代理端点：7类

### §10 前端设计规格

- 15个招聘业务页面（10一级+5详情子页）
- AI三模式交互：Context Bar + Sidecar + 全屏Chat
- 全局搜索 CommandBar（Cmd+K）
- AI操作菜单（每个页面右上角）
- 双模创建入口（AI引导+手动表单）
- 新用户引导三步流程
- 6种页面状态规范（空/加载/错误/部分/无权限/离线）

### §13 里程碑规划

- M0基建（W0-W2）→ M1组织+岗位（W3-W5）→ M2简历（W6-W8）→ M3候选人（W9-W12）→ M4匹配（W13-W16）→ M5面试（W17-W21）→ M6 Offer（W22-W25）→ M7 Dashboard（W26-W28）→ M8分析+AI（W29-W33）→ M9 Skill+Cron（W34-W36）→ M10 Memory+主动AI（W37-W41）
- 总计约52周（12个月），一人公司模式

---

## 二、实际代码实现扫描

### 后端（packages/api/app/）

**数据模型（models/，11个文件）**：
- base.py, tenant.py, user.py, department.py, position.py, candidate.py, resume.py, matching.py（含MatchFeedback）, interview.py（含InterviewFeedback）, offer.py（含OfferApproval）, audit_log.py, ai_task.py
- 共定义13个ORM类

**API路由（routers/，13个.py文件）**：
- auth.py, departments.py, positions.py, resumes.py, candidates.py, matching.py, interviews.py, offers.py, analytics.py, dashboard.py, ai_tasks.py, public.py, __init__.py

**业务服务（services/，10个.py文件）**：
- department_service.py, position_service.py, resume_service.py, candidate_service.py, matching_service.py, interview_service.py, offer_service.py, analytics_service.py, dashboard_service.py, ai_task_service.py, ai_client.py

**中间件（middleware/，3个文件）**：
- auth.py（JWT认证）、rbac.py（角色权限）、audit.py（审计日志）

**装饰器（decorators/，1个文件）**：
- ai_capability.py（@AiCapability装饰器，简化版）

### 前端（packages/client/src/）

**HR页面（views/hr/，15个.vue文件）**：
- DashboardView, TasksView, PositionsView, PositionDetailView, ResumesView, ResumeDetailView, CandidatesView, CandidateDetailView, MatchingView, InterviewsView, InterviewDetailView, OffersView, OfferDetailView, AnalyticsView, OrgChartView

**HR API层（api/hr/，12个.ts文件）**：
- client.ts, index.ts, dashboard.ts, positions.ts, resumes.ts, candidates.ts, matching.ts, interviews.ts, offers.ts, analytics.ts, departments.ts, tasks.ts, public.ts

**状态管理（stores/hr/，7个.ts文件）**：
- index.ts, positions.ts, resumes.ts, candidates.ts, matching.ts, interviews.ts, offers.ts, analytics.ts

---

## 三、逐项差距分析

### A. 数据模型差距

**✅ 已实现且符合PRD**：
- positions表：核心字段齐全（title, department_id, status, required_skills, salary_min/max, headcount, filled_count, embedding_id, version等），DDL与PRD §7.2.1对齐
- candidates表：email/phone加密字段预留、email_hash/phone_hash去重键、profile JSONB、source_refs、credibility_score/grade、inference_data、embedding_id，DDL与PRD §7.2.3对齐
- matches表：分维评分（skill/experience/education/inference/salary_score）、score_breakdown JSONB、match_details、initiated_by、UNIQUE约束，与PRD §7.2.5对齐
- match_feedback表：与PRD §7.7a一致
- departments表：自引用树形结构（parent_id）、manager_name、sort_order，与PRD §4.1.1对齐
- users表：role枚举、tenant_id隔离、email唯一约束
- tenants表：plan/status枚举
- offers表：基础状态机+OfferApproval审批链
- interviews表：双FK（position_id+candidate_id）、round_number、interview_type、status枚举、interviewer_ids JSONB、ai_questions JSONB

**⚠️ 已实现但与PRD有偏差**：

1. **candidates表遗留字段**：Candidate模型保留了position_id, stage, source, source_detail, summary, applied_at, tags等遗留字段（PRD V3.6明确candidates表不应包含简历/投递相关字段，这些应通过matches/resumes关联查询）。建议：标记为deprecated，后续迭代清理。

2. **@AiCapability装饰器大幅简化**：PRD §8.1a定义21字段装饰器（name, endpoint, method, tool_name, permissions, timeout, llm_model, fallback_model, prompt_version, allowed_callers, requires_tenant_isolation, ai_capability_id, description, request_model, response_model, cache_ttl, rate_limit, data_classification, audit_level, tags），实际只实现了5个参数（capability, fallback, timeout, cache_ttl）。建议：按PRD规格补全字段，支撑代码生成器。

3. **interviews表字段缺失**：PRD §7.2.4 DDL定义了match_id FK、feedback_tokens JSONB（多面试官JWT Token）、transcript_text/transcript_status（录音转写）、analysis_result JSONB（LLM原始分析）、decision/decision_reason字段、stage字段（screening/technical/behavioral/final/offer）、briefing_data JSONB（考察清单）、recording_url、ai_analysis JSONB等，实际模型大量缺失。建议：补齐DDL字段。

4. **offers表薪资字段未加密**：PRD §7.7a明确定义salary_encrypted（AES-256密文）+ salary_hash（SHA-256哈希），实际使用base_salary Integer明文存储。建议：Phase 2实现加密，Phase 1至少改字段名并预留。

5. **positions表extra字段**：保留了location, employment_type, description, requirements, benefits等DDL外的字段。这些是早期版本遗留，与PRD §7.2.1 DDL不完全对齐但也不冲突，可保留作为扩展。

6. **tenant_id类型偏差**：PRD DDL定义tenant_id为UUID类型+FK到tenants表，实际多个模型用String(64)存储，无FK约束。建议：统一改为UUID+FK。

**❌ PRD要求但未实现**：

7. **profile_updates表**（P1）：PRD §7.7a定义候选人画像更新溯源记录表，用于简历冲突处理和历史追踪。未创建对应模型。优先级：**P1**（M3候选人模块依赖）。

8. **conflict_resolutions表**（P1）：PRD §7.2.3定义冲突裁决表（候选人数据冲突检测+人工审核），未创建。优先级：**P1**。

9. **onboarding_tasks表**（P1）：PRD §7.4定义入职任务清单表（P0-09修复），Offer→入职闭环依赖。优先级：**P1**（M6 Offer模块）。

10. **ai_decisions表**（P2）：PRD §7.8a定义AI决策审计表（所有AI推理的输入/输出/模型/版本/耗时追踪）。优先级：**P2**（可后期补充）。

11. **consent_records表**（P2）：PRD §3.8定义候选人知情同意记录表。优先级：**P2**。

12. **im_user_bindings表**（P1）：PRD §9.3定义IM发送者身份映射表。优先级：**P1**（IM审批功能依赖）。

13. **share_links表**（P1）：PRD §7.7a定义共享链接表（7天+撤销API）。优先级：**P1**。

14. **evaluation_templates表**（P0）：PRD §7.7a定义面试评估模板。优先级：**P0**（面试评估规范依赖）。

15. **channels表**（P1）：PRD §7.7a定义招聘渠道表。优先级：**P1**。

16. **dead_letter_tasks表**（P1）：PRD §8.1c定义异步任务死信队列表。优先级：**P1**。

### B. API端点差距

**✅ 已实现**：
- 基础CRUD端点：departments, positions, candidates, resumes, interviews, offers, matches
- Dashboard端点：dashboard路由存在
- AI任务端点：ai_tasks路由存在
- 认证端点：auth.py
- 公开端点：public.py（反馈表单等）

**⚠️ 已实现但需验证完整性**：
- 需逐个路由文件核对端点数量与PRD §9.1的对齐度

**❌ PRD要求但未实现（关键缺失）**：

17. **AI能力端点大部分缺失**（P0）：PRD §9.1定义约35个AI能力端点（generate-jd, parse, build-profile, matching/run, generate-questions, generate-report, briefing, analyze-recording, verify, infer, generate-offer, benchmark, insights, funnel-diagnosis等），当前services层多为TODO stub。优先级：**P0**（核心AI功能）。

18. **岗位360°视图支撑端点**（P1）：PRD §4.1.2定义 /positions/:id/funnel + /positions/:id/timeline 端点。优先级：**P1**。

19. **Context Bar洞察端点**（P1）：PRD §9.1定义 GET /api/v1/insights（FastAPI直出，不走Koa BFF）。优先级：**P1**（AI交互核心）。

20. **AI引导式创建端点**（P1）：PRD §9.1定义 POST /positions/ai-interpret + /positions/ai-confirm。优先级：**P1**。

21. **入职相关端点**（P1）：PRD §9.1定义 /offers/:id/onboard, /onboarding/:token 等6个端点。优先级：**P1**。

22. **主动式AI端点**（P2）：PRD §9.1定义4个 /ai/proactive/* 端点。优先级：**P2**。

23. **SSE任务事件流端点**（P1）：PRD §9.1定义 GET /tasks/:id/events。优先级：**P1**。

24. **向量重建端点**（P1）：PRD §9.1定义 POST /positions/rebuild-vectors。优先级：**P1**。

### C. Service层差距

**❌ 核心差距**：

25. **LLM集成未实现**（P0）：PRD §8.1定义Service层 = CRUD方法 + AI推理方法，21项AI能力均有对应Service方法签名（generate_jd, parse, build_profile, run, explain, generate_questions, generate_report, infer_potential, verify_credibility, benchmark, diagnose_funnel等）。当前ai_client.py存在但大部分Service方法是TODO stub。优先级：**P0**。

26. **pgvector向量检索未集成**（P0）：PRD §8.1定义向量检索+LLM精排匹配架构，positions/candidates的embedding_id字段已预留但无实际向量操作代码。优先级：**P0**。

27. **异步任务队列(ARQ)未实现**（P1）：PRD §8.1c定义完整的ARQ任务队列（Worker并发控制、进度通知、死信队列），当前仅ai_task模型存在但无Worker实现。优先级：**P1**。

28. **LiteLLM降级链未实现**（P1）：PRD §5.8定义gpt-4.1→Gemini→Qwen3-72B三级降级链+熔断机制，未实现。优先级：**P1**。

29. **PII数据脱敏Pipeline未实现**（P0）：PRD §5.7定义LLM数据脱敏Pipeline（姓名→[NAME_1]、手机→[PHONE_1]等），这是P0安全要求。优先级：**P0**。

30. **Prompt版本管理未实现**（P1）：PRD §5.9定义prompts/目录+YAML结构+Golden Dataset回归，未创建。优先级：**P1**。

31. **RAG检索增强未实现**（P2）：PRD §5.10定义retrieve_rerank()通用RAG方法。优先级：**P2**。

### D. 前端差距

**✅ 已实现**：
- 15个HR页面全部创建（与PRD §10.1清单完全匹配）
- 10+ API模块文件（覆盖所有核心业务）
- 8个Pinia Store（状态管理）
- HR Layout组件（侧边导航）
- 路由骨架

**⚠️ 已实现但需深化**：

32. **页面内容深度**（P1）：15个页面文件已创建但多数为基础骨架，PRD §10.1定义了非常详细的页面布局（如岗位360°的5Tab结构、候选人360°的画像卡片+经验时间线、Dashboard的4区域布局等），需要大量前端组件开发。优先级：**P1**。

**❌ PRD要求但未实现**：

33. **AI Context Bar组件**（P0）：PRD §10.1b定义所有360°视图详情页顶部AI洞察栏（随Tab切换动态刷新）。这是AI原生交互的核心组件。优先级：**P0**。

34. **Agent Sidecar组件**（P1）：PRD §10.1b定义右侧对话面板（480px固定宽度+300ms ease-out滑入动画+遮罩层）。优先级：**P1**。

35. **全局搜索CommandBar**（P1）：PRD §10.7定义Cmd+K全局搜索（岗位/候选人/简历分组展示+AI搜索按钮）。优先级：**P1**。

36. **双模创建入口**（P1）：PRD §10.1a定义岗位/面试创建的🤖AI引导+📝手动表单切换交互。优先级：**P1**。

37. **AI操作菜单**（P1）：PRD §10.1a定义每个招聘页面右上角的🤖AI操作下拉菜单。优先级：**P1**。

38. **新用户引导流程**（P2）：PRD §10.4定义三步引导+功能卡片推送。优先级：**P2**。

39. **页面状态规范**（P1）：PRD §10.5定义6种页面状态（空/加载/错误/部分/无权限/离线）统一UI组件。优先级：**P1**。

### E. 架构级差距

**❌ PRD要求但未实现**：

40. **代码生成器**（P0）：PRD §8.1a.4定义Jinja2静态代码生成器（从@AiCapability装饰器自动生成FastAPI路由+Tool注册），CI漂移检测。这是双路径一致性的核心机制。优先级：**P0**。

41. **HR Tools（12个）**（P1）：PRD §8.1定义hr_resume, hr_profile, hr_matching, hr_position等12个Agent Tool文件。优先级：**P1**（Agent交互依赖）。

42. **招聘Skills（8个）**（P2）：PRD §5.4定义hr-daily-briefing, hr-candidate-screen等8个SKILL.md文件。优先级：**P2**。

43. **AgentContext安全机制**（P0）：PRD §8.1b定义frozen dataclass + HMAC-SHA256签名 + Tool层验签。优先级：**P0**。

44. **统一认证装饰器_authorize()**（P0）：PRD §8.1b定义Service层所有方法必须经过的认证装饰器（RBAC+审计日志）。优先级：**P0**。

45. **MCP Server集成**（P2）：PRD §9.6定义boss-zhipin-mcp + feishu-calendar-mcp。优先级：**P2**（Phase 2）。

46. **SSE中间件**（P1）：PRD §8.1c/§9.5定义SSE流式响应中间件。优先级：**P1**。

### 🆕 实际实现了但PRD未覆盖

47. **ai_task模型和服务**：PRD仅在§8.1c提到tasks表概念，实际代码创建了完整的AiTask模型+ai_task_service+ai_tasks路由，提供了CRUD+状态管理+统计接口，超出了PRD的细化程度。这是良好实践。

48. **InterviewFeedback独立表**：PRD §7.2.4未单独定义面试反馈表（反馈数据在interviews表内），但实际代码独立创建了InterviewFeedback模型，支持多面试官独立评分。这是更好的数据模型设计。

49. **OfferApproval审批链表**：PRD §7.7a的offers表仅有approved_by单字段，实际代码创建了独立的OfferApproval模型，支持多级审批链（approval_order）。这是更灵活的设计。

50. **public.py路由**：PRD未单独定义public路由文件，实际代码抽取了公开端点（反馈表单、健康检查等），符合关注点分离最佳实践。

---

## 四、最佳实践建议

### 1. 后端架构优化

**A. 分层架构进一步细化**：
- 当前Router→Service→Model三层清晰，但缺少Schema层验证。建议为每个端点创建Pydantic Request/Response Schema（当前schemas目录已预留但内容不足），确保API契约的类型安全。
- 引入Repository层隔离SQLAlchemy查询逻辑，Service层只操作Repository接口，提升可测试性。

**B. 领域事件驱动**：
- PRD §8.1c已定义ARQ异步任务框架，建议进一步引入领域事件模式：简历解析完成→发布ResumeParsedEvent→触发画像构建→触发匹配刷新。用事件解耦Service间依赖，避免Service直接调用Service造成的循环依赖。
- 事件总线实现推荐：Python的blinker或自建轻量EventBus，配合Redis Pub/Sub跨进程传递。

**C. 乐观锁并发控制**：
- positions/candidates的version字段已预留（PRD V3.5新增），但Service层需实现compare-and-swap逻辑。建议封装为BaseService.check_version(model, expected_version)通用方法。

### 2. AI功能优化

**A. Prompt工程标准化**：
- 按PRD §5.9创建prompts/目录结构，每个AI能力一个YAML文件（system_prompt + user_prompt_template + output_schema + few_shots）。
- 引入Prompt版本追踪：ai_decisions表记录每次AI调用的prompt_version，支持A/B测试和回归分析。
- 建立Golden Dataset：每个AI能力至少20条标注样本，CI门禁确保Prompt变更不降低质量。

**B. RAG架构**：
- 当前仅依赖LLM直接推理，建议引入RAG架构：JD生成时检索历史高评分JD作为参考；面试题生成时检索该岗位历史面试高频问题。
- 检索策略：pgvector HNSW索引 + 混合检索（关键词BM25 + 语义向量） + RRF融合排序。

**C. 降级链实现**：
- 按PRD §5.8实现LiteLLM Router：gpt-4.1(精排) → Gemini 2.5 Pro → Qwen3-72B → Rule兜底。
- 熔断器：推荐pybreaker库，5分钟5次失败触发OPEN，10分钟后HALF_OPEN。
- 超时分级：简单10s/复杂30s/长任务300s，异步任务ARQ Worker独立管理。

### 3. 安全性加固

**A. PII数据脱敏Pipeline**（P0安全修复）：
- PRD §5.7已详细定义，需立即实现：
  - 发送前：正则匹配姓名/手机/邮箱/身份证/地址 → 替换为占位符
  - 接收后：占位符反替换还原
  - 映射表仅存内存，请求完成即销毁
  - 脱敏日志写入audit_logs(source='llm_masking')

**B. Prompt注入防护**（P1安全修复）：
- PRD §5.7定义三段式Prompt结构 + 输入净化过滤器 + 输出后处理过滤器。
- 建议引入guardrails-ai库简化实现。

**C. 数据分类分级**：
- L1公开（岗位标题）/ L2内部（JD文本）/ L3敏感（姓名/手机）/ L4机密（薪资）
- 每个API端点标注data_classification，中间件自动执行对应保护策略。

**D. CSRF防护**：
- PRD P2-32要求Double Submit Cookie，建议FastAPI中间件实现。

### 4. 可观测性

**A. 结构化日志**：
- PRD §12指定structlog，建议：每个请求注入trace_id（UUID），贯穿Service→LLM→DB全链路。日志格式JSON，字段包含：timestamp, level, trace_id, tenant_id, user_id, service, method, duration_ms。

**B. OpenTelemetry集成**：
- PRD §12指定OTel，建议：FastAPI自动instrumentation + SQLAlchemy instrumentation + Redis instrumentation + 自定义Span标注AI能力调用。
- 推荐 Jaeger 或 Tempo 作为Trace后端。

**C. 监控大盘**：
- LLM成本：每日Token消耗/模型分布/降级率
- API性能：P50/P95/P99延迟/错误率
- 业务指标：简历解析量/匹配执行量/Offer转化率

### 5. 开发体验优化

**A. 测试策略**：
- 单元测试：每个Service方法至少3个测试（正常/边界/异常）
- 集成测试：pytest + httpx-async，测试Router→Service→DB全链路
- Golden Dataset回归：AI能力Prompt变更自动跑回归
- 建议：M0基建阶段搭建测试基础设施，每个模块交付要求测试覆盖率>80%

**B. CI/CD Pipeline**：
- PR触发：lint(ruff) + type-check(mypy) + test(pytest) + 前端build(vue-tsc + vite build)
- 代码生成器漂移检测：make generate && git diff --exit-code generated/
- 安全扫描：bandit + pip-audit
- 建议GitHub Actions配置完整Pipeline。

**C. 开发环境标准化**：
- Docker Compose一键启动：PostgreSQL 17 + pgvector + Redis + MinIO + FastAPI + Koa
- alembic自动迁移：每个模块交付时提交migration
- 种子数据脚本：开发/测试环境自动填充Mock数据

### 6. 前端架构优化

**A. 组件库标准化**：
- 创建hr/components/通用组件库：CandidateCard, MatchScoreBar, StatusBadge, AiContextBar, SkillTag, TimelineView等
- 所有360°视图共享TabContainer组件（懒加载+缓存）
- 统一空状态/加载态/错误态组件

**B. 状态管理规范**：
- Pinia Store统一结构：{ data, loading, error, pagination }
- API调用统一经过Store action，组件不直接调API
- 乐观更新策略：先更新UI再等API响应（匹配/状态变更等高频操作）

**C. AI交互组件**：
- AiContextBar：独立组件，接收entity_type + entity_id + tab参数，内部管理缓存+刷新
- AgentSidecar：基于NDrawer实现，480px固定宽度，管理Agent Session
- CommandBar：基于NModal + NInput，Debounce 300ms + 搜索API调用

---

## 五、总结与优先级建议

### 当前项目进度评估

根据PRD §13里程碑对照，当前代码实现大致处于 **M0基建完成 + M1部分完成** 阶段：
- M0基建（✅大部分完成）：FastAPI骨架、PostgreSQL+pgvector、中间件、前端目录结构
- M1组织+岗位（🔄进行中）：部门/岗位模型完成、基础CRUD路由存在、但AI能力端点未实现
- M2-M10（❌未开始）：简历解析、候选人管理、匹配、面试、Offer等核心业务逻辑待实现

### 立即行动项（P0）

1. **补全@AiCapability装饰器21字段**（支撑后续所有AI能力开发）
2. **实现PII数据脱敏Pipeline**（安全合规刚需）
3. **实现AgentContext安全机制**（frozen + HMAC验签）
4. **创建AI Context Bar组件**（AI原生交互核心差异化）
5. **实现代码生成器骨架**（双路径一致性保障）

### 短期行动项（P1，M1-M3内）

6. 补全interviews表DDL字段（transcript, recording, briefing_data, decision等）
7. 创建profile_updates, conflict_resolutions表
8. 实现LiteLLM降级链+熔断器
9. 创建prompts/目录+YAML Prompt文件
10. 实现ARQ异步任务队列
11. 开发15个页面的深度交互组件
12. 实现Agent Sidecar组件

### 中期行动项（P2，M4-M6）

13. 创建ai_decisions审计表
14. RAG检索增强
15. MCP Server集成
16. 新用户引导流程
17. 主动式AI引擎9场景
18. Golden Dataset回归测试

---

> **审查结论**：项目骨架搭建完整，核心数据模型与PRD高度对齐（覆盖率约75%），前端15页面骨架齐全。主要差距集中在AI能力实现（21项中大部分为TODO stub）、安全机制（脱敏/验签/加密）和深度交互组件（Context Bar/Sidecar/CommandBar）。建议按M1→M2→M3的里程碑顺序，优先补全P0安全和AI基础设施，再逐步实现各模块业务逻辑。
