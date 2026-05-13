# 术语表

> 源自 PRD V3.6 附录F（L7719-L7751）
> PRD原文：`prd/HireMind-PRD-V3.6.md`

| 术语 | 全称 | 定义 |
|------|------|------|
| Agent | AI Agent | 具备自主规划+多步执行能力的AI实体（本系统中基于Hermes Agent） |
| ATS | Applicant Tracking System | 招聘管理系统（传统范式：表单驱动） |
| BFF | Backend For Frontend | 服务于前端的中间层（本系统中为Koa 2） |
| Context Bar | AI Context Bar | 详情页顶部AI洞察栏（随Tab动态刷新） |
| Cron | Cron Job | 定时任务调度器（Hermes内置） |
| delegate_task | — | Hermes子Agent委派能力（创建独立子Agent并行执行任务） |
| JD | Job Description | 岗位描述/职位描述 |
| LLM | Large Language Model | 大语言模型（本系统使用OpenAI gpt-4.1/gpt-4.1-mini） |
| MCP | Model Context Protocol | AI外部系统连接协议（本系统用于Boss直聘/飞书集成） |
| pgvector | — | PostgreSQL向量扩展（HNSW+SQ8量化，候选人/岗位向量检索核心引擎） |
| PII | Personally Identifiable Information | 个人身份信息（姓名/手机/邮箱/身份证等） |
| PIPL | Personal Information Protection Law | 中华人民共和国个人信息保护法 |
| RPO | Recovery Point Objective | 恢复点目标（数据丢失容忍度） |
| RTO | Recovery Time Objective | 恢复时间目标（系统恢复容忍时间） |
| Sidecar | Agent Sidecar | 详情页右侧Agent对话面板（上下文感知） |
| Skill | — | Hermes可复用任务流程（文件驱动的AI工作流） |
| SSE | Server-Sent Events | 服务器推送事件（用于Agent流式输出） |
| Tool | — | Hermes注册的可调用工具函数（如parse_resume） |
| Webhook | — | 外部事件回调通知机制（如Boss直聘新简历通知） |
| 360°视图 | 360° Detail View | 详情页聚合视图（候选人/岗位/面试/Offer的全息信息展示） |
| ARQ | — | 基于Redis的async-first任务队列框架（异步任务执行层） |
| Caddy | — | 零配置HTTPS反向代理服务器（替代Nginx） |
| DeepEval | — | AI能力评估框架，pytest原生集成，LLM-as-Judge |
| LiteLLM | — | LLM多Provider路由库（库模式），支持降级链和成本追踪 |
| pgvectorscale | — | PostgreSQL向量扩展（StreamingDiskANN索引，百万级向量检索） |
| RRF | Reciprocal Rank Fusion | 倒数排名融合（向量检索+全文检索结果融合算法） |
| Scalar | — | 现代API文档UI工具（替代Swagger UI） |
| structlog | — | Python结构化日志库（JSON+OTLP输出） |
