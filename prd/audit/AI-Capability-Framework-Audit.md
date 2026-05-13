# AI能力框架维度审计报告

> **审计对象**：HireMind-PRD-V3.6.md  
> **审计时间**：2026-05-12  
> **审计人**：AI工程审计专家  

---

## CRITICAL

| ID | 方面 | 问题 | 影响 | 修复建议 |
|----|------|------|------|---------|
| C-01 | A. AI能力矩阵 | **AI能力#16 漏斗瓶颈诊断（`analytics_service.diagnose_funnel()`）无独立端点**。§9.1 AI能力端点表中没有 `diagnose_funnel` 专用端点。§5.3 TOP10表将其映射到 `POST /api/v1/analytics/insights`，但§9.1中该端点的Service方法为 `analytics_service.generate_insights()`（#10数据洞察），两个不同AI能力共用一个端点 | 无法独立触发漏斗诊断；调用时无法区分"数据洞察"和"漏斗诊断"；装饰器name冲突 | 新增独立端点 `POST /api/v1/analytics/funnel-diagnosis`，Service方法 `analytics_service.diagnose_funnel()`，装饰器name=`diagnose_funnel`，Tool注册名=`diagnose_funnel` |
| C-02 | A. AI能力矩阵 | **AI能力#7 面试评分结构化（`interview_service.evaluate()`）Service方法在§9.1端点表中不存在**。§9.1的面试评分端点是 `POST /api/v1/interviews/:id/evaluate`，但映射的Service方法为 `interview_service.generate_report()`（#21面试分析报告），两个AI能力共用一个端点+Service方法。§5矩阵中#7和#21是不同的能力（#7=评分结构化，#21=分析报告） | #7面试评分结构化作为独立AI能力无法独立调用；§5矩阵定义的21项能力实际只有20个实现入口 | 方案A：拆分为两个独立端点——`POST /api/v1/interviews/:id/structure-score`（#7评分结构化）和 `POST /api/v1/interviews/:id/report`（#21分析报告）；方案B：明确说明#7是#21的子步骤，从21项中移除#7作为独立能力 |
| C-03 | A. AI能力矩阵 | **4项Agent独占能力（#11自然语言搜索/#12多步编排/#13主动通知/#17部分推理）在§9.1 AI能力端点表中无端点映射**。§8.1a.6声明4项为Agent独占（allowed_callers=["tool"]），但§9.1仅列出Web可达端点。§5.3 TOP10表中#9多步编排明确标注"Agent内部编排，无直接端点"，#10主动推送映射到 `GET /api/v1/dashboard/ai-insights`（但该端点是GET查询已有洞察，不是触发推送） | §5矩阵声明21项AI能力，但4项无FastAPI端点；@AiCapability装饰器无法声明端点；CI漂移检测会报错 | 对Agent独占能力做统一处理：(1) §9.1新增"Agent独占端点"分区，即使无Web入口也需声明装饰器元数据；(2) #13主动通知增加 `POST /api/v1/notifications/proactive` 作为内部触发端点；(3) 在§5.3中为每项标注"端点路径：Agent内部（无需端点）"或提供内部端点 |
| C-04 | A. AI能力矩阵 | **§8.2 Tool注册权限表仅列出11个Tool，但§9.1 AI能力端点表有33个AI端点**。缺少的Tool注册包括：`explain_match`/`reverse_matching`/`generate_briefing`/`verification_checklist`/`upload_recording`/`analyze_recording`/`get_transcript`/`batch_interview`/`batch_parse`/`infer_potential`/`get_inferences`/`resolve_conflict`/`get_conflicts`/`merge_inferences`/`analytics_dashboard`/`position_health`/`benchmark_offer`/`generate_negotiation_advice`/`enhance_match`/`submit_match_feedback`/`get_match_feedback_stats`/`org_health_analysis`/`dept_health_analysis`/`vectorize`/`get_context_insights` | §8.2作为安全审计权威清单，缺失22个Tool的权限声明，安全隐患——未声明权限的Tool可能绕过RBAC检查 | §8.2 Tool注册权限表补充全部33个AI端点对应的Tool注册名、Service方法、所需权限级别 |
| C-05 | B. Skill库一致性 | **§13里程碑表引用4个不存在的Skill名称**：`resume-parser`（M1）、`job-matching`（M2）、`interview-coord`（M3）、`jd-generator`（M3）。§5.4权威Skill清单仅定义8个Skill（hr-daily-briefing/hr-candidate-screen/hr-interview-prep/hr-interview-debrief/hr-offer-strategy/hr-funnel-diagnosis/hr-talent-pool-scan/hr-weekly-review），附录D也只列出这8个 | 开发团队按里程碑交付时会创建与§5.4命名不一致的Skill文件，导致Cron配置和Skill调用链断裂 | 将§13里程碑表中的伪造Skill名替换为§5.4权威清单中的对应名称：`resume-parser`→`hr-candidate-screen`、`job-matching`→`hr-candidate-screen`+`hr-talent-pool-scan`、`interview-coord`→`hr-interview-prep`、`jd-generator`→无对应Skill（JD生成为直接Tool调用，不经过Skill编排） |
| C-06 | D. 降级链一致性 | **§5.8降级链增加了一个§5.11和§12.0a中不存在的降级步骤**：§5.8第四条"Qwen3-72B也不可用 → 降级到gpt-4.1-mini（仅限已脱敏的常规任务）"，而§5.11三级链（Full→Light→Rule）和§12.0a降级链均不包含此"Qwen3→gpt-4.1-mini反向降级"步骤 | 三处定义不一致，开发团队不知道以哪个为准；实际实现可能产生循环降级（gpt-4.1→Gemini→Qwen3→gpt-4.1-mini→Gemini Flash→...） | 在§5.8中标注"本节为权威降级链定义，§5.11/§12.0a引用本节"。删除Qwen3→gpt-4.1-mini反向降级步骤（违反国内合规场景降级逻辑），改为：Qwen3不可用→直接进入Rule级兜底 |
| C-07 | D. 降级链一致性 | **§5.8超时阈值表与§5.11 LiteLLM Router配置的超时阈值冲突**。§5.8定义"简单任务10s/复杂任务30s/长任务300s"，§5.11 LiteLLM配置定义"对话类30s/长任务按§8.1c/批量自定义"，§5.8降级触发规则中又有"对话类单次超时>30s"。三处超时数字不一致（10s vs 30s，哪个触发降级？） | 开发团队无法确定超时阈值应以哪节为准；可能导致简单任务10s超时后不触发降级（因为Router配置30s才降级） | 统一超时定义，指定§5.8为权威来源。简单任务（JD润色/评语/摘要）10s超时→返回模板；复杂任务（匹配/画像/报告）30s超时→降级重试；长任务300s→ARQ管理。§5.11引用§5.8的超时表 |

## WARNING

| ID | 方面 | 问题 | 修复建议 |
|----|------|------|---------|
| W-01 | A. AI能力矩阵 | §9.1端点表中 `POST /api/v1/matching/:id/explain` 的装饰器name=`enhance_match`，Tool注册名=`hr_matching`，与 `GET /api/v1/matches/:id/explain`（装饰器name=`explain_match`，Tool注册名=`explain_match`）路径相似但功能不同（一个是匹配推理增强#18，一个是匹配解释#5），容易混淆 | 统一命名：`/matching/:id/explain`改为`/matching/:id/enhance`以明确区分；或Tool注册名从`hr_matching`改为`enhance_match`以与装饰器name一致 |
| W-02 | A. AI能力矩阵 | §9.1中 `POST /api/v1/offers/:id/negotiation-advice` 的Tool注册名=`hr_offer_negotiate`，与§8.2 Tool注册权限表中`hr_offer`模块名不一致（附录中无`hr_offer_negotiate`这个Tool） | 在§8.2中补充`hr_offer_negotiate` Tool的权限声明，或在§9.1中统一Tool注册名为`generate_negotiation_advice` |
| W-03 | A. AI能力矩阵 | §9.1 AI能力端点表中部分端点不属于21项AI能力但列在AI能力分区下：`vectorize`（岗位向量化）、`upload_recording`（录音上传）、`batch_interview`（批量排期）、`batch_parse`（批量解析）、`verification_checklist`（待验证清单）、`get_transcript`/`get_inferences`/`get_conflicts`/`resolve_conflict`/`merge_inferences`/`analytics_dashboard`/`position_health`/`get_context_insights`等。这些是辅助端点，不直接对应§5矩阵的21项AI能力 | 将这些辅助端点从"AI能力端点"分区移至单独的"AI辅助端点"分区，或在§5矩阵中补充对应的AI能力编号映射 |
| W-04 | B. Skill库一致性 | §5.4 Skill清单中 `hr-candidate-screen` 的触发场景描述为"候选人详情→AI操作"，但附录B Cron表中将其用于"岗位匹配刷新"（`0 8 * * *`）的Cron触发。触发方式不一致（手动 vs Cron） | 在§5.4 `hr-candidate-screen` 触发场景中补充"Cron定时（每日8:00匹配刷新）"，或为岗位匹配刷新创建独立Skill |
| W-05 | B. Skill库一致性 | §5.4 Skill清单中 `hr-talent-pool-scan` 引用的Tool为 `hr_talent_pool`，但§9.1端点表中无 `hr_talent_pool` 相关端点。该Tool在§8.3 Hermes源码复用清单中也无定义 | 在§8.2 Tool注册权限表中补充 `hr_talent_pool` 的定义和权限；或在§9.1中补充人才库扫描相关端点 |
| W-06 | C. Prompt系统 | §5.9 Prompt文件目录共18个YAML文件，但§5矩阵有21项AI能力。缺失的Prompt文件对应：(1) #5匹配解释生成——`matching/explain_v1.yaml`存在但未在矩阵TOP10中独立列出；(2) #8候选人推荐评语——`profile/recommend_v1.yaml`存在；(3) #7面试评分结构化——无独立Prompt文件（被合并入evaluate_v1.yaml或generate_report_v1.yaml）；(4) #16漏斗瓶颈诊断——无独立Prompt文件（共用generate_insights_v1.yaml）；(5) #17候选人隐性推理——`profile/infer_potential_v1.yaml`存在；(6) #18匹配推理增强——`matching/enhance_match_v1.yaml`存在；(7) #11自然语言搜索/#12多步编排——Agent内部，可能不需要独立Prompt | 为#7面试评分结构化和#16漏斗瓶颈诊断补充独立Prompt文件；或在§5.9中明确说明哪些AI能力共用Prompt、哪些使用Agent内部推理不需要独立Prompt |
| W-07 | C. Prompt系统 | §5.9 YAML结构定义了 `output_schema` 和 `few_shots` 字段，但未定义 `input_schema`（输入参数Schema）。§5矩阵中每项AI能力的输入格式各异（文件/ID/文本），缺少统一的输入约束定义 | 在YAML结构中增加 `input_schema` 字段，与@AiCapability装饰器的 `request_model` 字段对齐 |
| W-08 | C. Prompt系统 | §5.9中Prompt文件的 `model_target` 字段仅声明单一模型，未包含降级链信息。§5.8/§5.11定义了三级降级链，但Prompt YAML中无法看到降级后的模型切换策略 | 在Prompt YAML结构中增加 `fallback_model` 字段（与@AiCapability装饰器对齐），或引用§5.8统一降级链配置 |
| W-09 | E. 主动式AI引擎 | §5.6主动式AI引擎定义9类场景，但标题和§5.2分层架构图中仍写"8类场景"（L2794："基于Hermes Cron + Webhook构建9类主动式AI场景"，但L2837："主动式AI引擎（Cron+Webhook触发8类场景）"）。场景9"入职前关怀提醒"为V3.2.4新增但分层架构图未更新 | 统一§5.2分层架构图中的数字为"9类场景" |
| W-10 | E. 主动式AI引擎 | 附录B中场景9"入职前关怀提醒"使用的Skill为 `hr-daily-briefing`，该Skill原始定义为"每日招聘简报"，被复用于3个Cron任务（岗位超期预警/Offer跟进/招聘周报/入职前关怀）。一个Skill承载4个不同业务场景，逻辑复杂度过高 | 考虑将 `hr-daily-briefing` 拆分为更细粒度的Skill，或在Skill内部用场景参数区分执行路径 |
| W-11 | E. 主动式AI引擎 | §5.6 P2-24修复定义了去重窗口（30天），但附录B中7个Cron任务均未在配置中声明 `dedup_window` 和 `dedup_key_pattern`。Cron配置缺少去重参数列 | 附录B Cron表增加"去重配置"列，声明每个任务的 `dedup_key` 和 `dedup_ttl`。P0场景（1/2/3）标注"无去重" |
| W-12 | E. 主动式AI引擎 | §5.6 P2-24定义"单次Cron执行最大AI调用次数限制：20次/Cron Job"，但附录B中无任何Cron任务声明AI调用次数预算。成本控制策略未在Cron配置中落地 | 附录B Cron表增加"AI调用预算"列，结合场景优先级和§5.6成本控制策略设置每任务上限 |
| W-13 | E. 主动式AI引擎 | 场景1"新简历自动筛选推送"为Webhook触发，附录B正确未配置Cron。但§9.1"主动式AI引擎端点"分区（L5156-5163）缺少"新简历筛选"场景的Webhook注册端点。§9.1仅列出4个主动式AI管理端点（trigger/status/config），无Webhook注册端点 | §9.1新增 `POST /api/v1/webhooks/register`（Webhook注册端点）或在主动式AI端点分区补充场景1的触发配置端点 |

---

## 审计总结

### A. AI能力矩阵完整性 — 4 CRITICAL

21项AI能力中存在**3项端点映射缺失/冲突**：
- #16 漏斗瓶颈诊断：无独立端点
- #7 面试评分结构化：与#21共用端点
- #11/#12/#13/#17 Agent独占能力：无FastAPI端点声明

§8.2 Tool注册权限表仅覆盖11/33个Tool，**缺失率67%**。

### B. Skill库一致性 — 1 CRITICAL

§13里程碑表引用4个不存在的Skill名称（`resume-parser`/`job-matching`/`interview-coord`/`jd-generator`），与§5.4+附录D的8个权威Skill不一致。

### C. Prompt系统 — 0 CRITICAL, 4 WARNING

18个Prompt文件覆盖了21项AI能力中的大部分，但#7评分结构化和#16漏斗瓶颈诊断缺少独立Prompt。输入Schema和降级模型未在Prompt YAML中声明。

### D. 降级链一致性 — 2 CRITICAL

三处降级链定义（§5.8/§5.11/§12.0a）存在**超时阈值冲突**和**降级步骤不一致**，无统一权威来源标注。

### E. 主动式AI引擎 — 0 CRITICAL, 5 WARNING

9类场景均有对应Cron/Webhook配置，但：
- §5.2架构图仍写"8类"
- hr-daily-briefing复用过度
- 去重/成本控制参数未落地到Cron配置表

### 统计

| 级别 | 数量 | 分布 |
|------|:----:|------|
| CRITICAL | 7 | A×4, B×1, D×2 |
| WARNING | 13 | A×3, B×2, C×4, E×5 |
