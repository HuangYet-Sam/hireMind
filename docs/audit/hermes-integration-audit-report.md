# 🤖 Hermes Agent 集成专家审计报告

> 审计角色：Hermes Agent集成专家  
> 审计对象：HireMind PRD V3.6 与 Hermes Agent 生态的集成方案  
> 审计日期：2026-05-12  
> 参考来源：PRD V3.6 §5/§8/§9.6，Hermes Agent SKILL.md（v2.1.0），hermes-agent源码结构

---

## 一、总体评估

| 维度 | 结论 | 说明 |
|------|------|------|
| **集成可行性** | ✅ **高度可行** | PRD深度理解Hermes架构，22项能力复用清单完整 |
| **架构契合度** | ⚠️ **需微调** | 3处设计需修正（见下文） |
| **当前代码** | ❌ **零实现** | 当前目录无任何Hermes相关代码 |

---

## 二、逐项审计

### 2.1 HR Tools注册路径（12个）

**结论：✅ 可行，命名规范正确**

PRD定义的12个HR Tools完全符合Hermes `tools/*.py` + `registry.register()` 约定：

```
hermes-agent/tools/
├── hr_resume.py      → registry.register(name="hr_resume", toolset="hr", ...)
├── hr_profile.py     → registry.register(name="hr_profile", toolset="hr", ...)
├── hr_matching.py    → registry.register(name="hr_matching", toolset="hr", ...)
├── hr_position.py    → registry.register(name="hr_position", toolset="hr", ...)
├── hr_interview.py   → registry.register(name="hr_interview", toolset="hr", ...)
├── hr_talent_pool.py → registry.register(name="hr_talent_pool", toolset="hr", ...)
├── hr_vector.py      → registry.register(name="hr_vector", toolset="hr", ...)
├── hr_storage.py     → registry.register(name="hr_storage", toolset="hr", ...)
├── hr_auth.py        → registry.register(name="hr_auth", toolset="hr", ...)
├── hr_analytics.py   → registry.register(name="hr_analytics", toolset="hr", ...)
├── hr_db.py          → registry.register(name="hr_db", toolset="hr", ...)
└── hr_offer.py       → registry.register(name="hr_offer", toolset="hr", ...)
```

**验证要点**：
- ✅ 命名使用 `hr_` 前缀，与Hermes现有tools（70+）不冲突
- ✅ 独立 `toolset="hr"`，可通过 `hermes tools enable hr` 控制
- ✅ 每个Tool需实现 `check_requirements()` 函数
- ⚠️ **需补充**：每个Tool的 `requires_env` 列表（如 `DATABASE_URL`、`MINIO_ENDPOINT`）

**PRD定义的最小权限矩阵（P2-34修复）**设计优秀：
- `tenant_id` 首位参数强制注入（不信任调用者传参）
- 白名单查询模式限制 `hr_db` Tool
- 审计日志通过OTel span记录

### 2.2 HR Skills结构（8个）

**结论：✅ 可行，需补充YAML frontmatter**

PRD定义的8个HR Skills路径 `skills/hr/*/SKILL.md` 符合Hermes Skill规范：

```
hermes-agent/skills/
├── hr-daily-briefing/SKILL.md
├── hr-candidate-screen/SKILL.md
├── hr-interview-prep/SKILL.md
├── hr-interview-debrief/SKILL.md
├── hr-offer-strategy/SKILL.md
├── hr-funnel-diagnosis/SKILL.md
├── hr-talent-pool-scan/SKILL.md
└── hr-weekly-review/SKILL.md
```

**⚠️ 需补充的YAML frontmatter示例**：

```yaml
---
name: hr-candidate-screen
description: "候选人深度筛选：技能验证+经验评估+文化匹配"
version: 1.0.0
metadata:
  hr:
    triggers: [candidate_detail_ai_action]
    tools_required: [hr_profile, hr_matching]
    estimated_duration: 30s
    priority: P1
---
```

**PRD的Skill→Tool调用矩阵设计（§5.4 P2-10）**：
- ✅ 每个Skill明确列出依赖的Tool（1-3个）
- ✅ 调用链逻辑清晰
- ✅ 支持自定义Skill（HR对话创建→Curator自进化）

### 2.3 MCP Server集成（4个）

**结论：⚠️ 有风险，PRD定义与实际有偏差**

PRD定义的4个MCP Server：

| MCP Server | PRD定义 | 实际性质 | 结论 |
|------------|---------|---------|------|
| `hr-crud-api` | FastAPI的MCP包装 | **自建**，需FastAPI → MCP协议适配 | ⚠️ 工作量大 |
| `neo4j-mcp` | 知识图谱 | **外部服务**，需neo4j部署 | ❌ Phase 1不需要 |
| `calendar-mcp` | 日历集成 | §9.6已改为 `feishu-calendar-mcp` | ⚠️ 名称不一致 |
| `ats-mcp` | ATS对接 | §9.6已改为 `boss-zhipin-mcp` | ⚠️ 名称不一致 |

**关键发现**：
1. PRD §9.6（第十三轮研讨）更新了MCP Server列表为 `boss-zhipin-mcp` + `feishu-calendar-mcp`
2. 架构图（§8）仍引用旧名称 `hr-crud-api / neo4j-mcp / calendar-mcp / ats-mcp`
3. **需统一**：架构图与§9.6存在不一致

**建议**：
- Phase 1 仅实现 `boss-zhipin-mcp`（Boss直聘）+ `feishu-calendar-mcp`（飞书日历）
- `hr-crud-api` 改为 FastAPI 直接被 Tool 调用（不需要MCP包装层，增加不必要的复杂度）
- `neo4j-mcp` 推迟到 Phase 3（当前架构无知识图谱需求）

### 2.4 @AiCapability装饰器机制

**结论：✅ 可行，设计精巧但需实现**

PRD §5.1定义：
> 每项能力通过@AiCapability装饰器声明，由代码生成器自动产生FastAPI端点和Agent Tool注册。

**实现方案**：

```python
# backend/app/decorators.py
def AiCapability(
    name: str,
    endpoint: str,       # FastAPI路由，如 "/api/v1/resumes/:id/parse"
    method: str = "POST", # HTTP方法
    tools: list = None,   # 依赖的Tool列表
    model: str = "gpt-4.1",
    timeout: int = 30,
    degradation: str = None,  # 降级方案
):
    """
    装饰器 → 同时生成：
    1. FastAPI路由端点
    2. Hermes Tool注册（schema自动生成）
    """
    def decorator(func):
        # 注册为FastAPI路由
        register_fastapi_endpoint(func, endpoint, method)
        # 生成Tool schema并注册
        register_hermes_tool(func, name, tools)
        return func
    return decorator
```

**⚠️ 风险点**：
- 装饰器需要同时理解 FastAPI 的路由注册和 Hermes 的 `registry.register()` 协议
- 代码生成器的调试成本较高，建议Phase 1先手动注册，Phase 2再引入代码生成器
- Service方法的参数签名（Pydantic model）需要能自动转换为Hermes Tool的JSON Schema

### 2.5 Webhook消费链

**结论：✅ 可行，三种方案清晰**

PRD §5.6定义了3种触发方式：

| 方式 | 场景 | 技术实现 | 结论 |
|------|------|---------|------|
| **Cron** | 定时扫描（日报/周报/超期预警） | `hermes cron create` → Agent → Service → send_message | ✅ 直接复用Hermes Cron |
| **Webhook** | 外部事件（简历上传/Boss直聘回调） | `POST /webhooks/:name` → Agent → Service | ✅ 直接复用Hermes Webhook |
| **回调** | 内部事件（匹配完成>90%推送） | Service层回调 → `hermes webhook test` → Agent | ⚠️ 需实现回调机制 |

**回调方案详解**（PRD §5.6场景6）：
```
匹配完成 → matching_service.run() 返回结果
         → 检测 match_score > 0.9
         → POST /webhooks/high-match-alert (Hermes Webhook)
         → Agent调用 hr_candidate_screen Skill
         → send_message 到微信/Web
```

这个设计利用了Hermes自身的Webhook消费能力，不需要额外的消息队列，✅ 设计合理。

### 2.6 数据流完整性验证

**结论：✅ 通顺，但BFF职责需明确**

完整链路：
```
用户操作（Web前端）
  → Vue组件 → Pinia Store → api/hr/*.ts
  → Koa BFF（:8648）转发 OR 直接调FastAPI（:8000）
  → FastAPI路由 → 中间件(JWT+RBAC+限流+审计)
  → Service层（确定性CRUD + AI推理方法）
  → LLM调用（通过LiteLLM）
  → 结果返回前端（SSE流式 OR JSON）

Agent路径：
  HR微信/飞书 → Hermes Gateway(:8642) → Agent Loop
  → Tool调用(hr_*) → Service层（同一套业务逻辑）
  → send_message推送结果
```

**⚠️ 前端审计报告指出**：招聘业务建议不走Koa BFF，直接调FastAPI。这与本审计一致——BFF仅服务Hermes管理后台（15页复用），招聘业务API直连FastAPI更简洁。

### 2.7 调用上下文（caller_type机制）

**结论：✅ 设计精良**

PRD §8（P1-16修复）定义的 `caller_type: Literal["tool", "api"]` 机制：
- Tool路径：Agent上下文注入 `tenant_id/user_id`
- API路径：JWT Token解析 `tenant_id/user_id`
- Service层通过 `_authorize()` 装饰器统一处理，不感知调用来源

这个设计确保了 Service 层的纯粹性，✅ 无需修改。

---

## 三、关键发现汇总

| # | 发现 | 严重度 | 状态 |
|---|------|--------|------|
| 1 | MCP Server名称不一致（§8 vs §9.6） | 🟡 Medium | PRD需修复 |
| 2 | hr-crud-api MCP不必要（增加复杂度） | 🟡 Medium | 建议Tool直连FastAPI |
| 3 | @AiCapability代码生成器Phase 1建议手动 | 🟢 Low | 开发策略 |
| 4 | Tool的requires_env列表PRD未完整定义 | 🟢 Low | 开发时补充 |
| 5 | neo4j-mcp Phase 1不需要 | 🟢 Low | 已在OPC路线图中推迟 |

---

## 四、优化建议

### 4.1 MCP Server方案简化

```
Phase 1（M0-M8）:
  ✅ FastAPI Tool直连（12个hr_* Tools直接调FastAPI Service）
  ✅ boss-zhipin-mcp（Boss直聘集成）
  ✅ feishu-calendar-mcp（飞书日历集成）

Phase 2（M9-M10）:
  📋 考虑引入 hr-crud-api MCP（如果第三方系统需要通过MCP访问FastAPI）
  📋 钉钉审批MCP、邮件模板MCP

Phase 3:
  📋 neo4j-mcp（知识图谱，视需求而定）
```

### 4.2 Tool注册最佳实践

```python
# tools/hr_position.py — 推荐实现模板
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("FASTAPI_BASE_URL"))

def hr_position_list(
    tenant_id: str,        # 首位参数，Agent上下文注入
    status: str = None,    # 可选筛选
    page: int = 1,
    page_size: int = 20,
    task_id: str = None
) -> str:
    """列出当前租户的岗位"""
    from services.position_service import PositionService
    svc = PositionService()
    result = svc.list_positions(
        tenant_id=tenant_id, status=status,
        page=page, page_size=page_size,
        caller_type="tool"
    )
    return json.dumps(result, ensure_ascii=False)

registry.register(
    name="hr_position_list",
    toolset="hr",
    schema={
        "name": "hr_position_list",
        "description": "列出当前租户的招聘岗位，支持按状态筛选",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["draft","active","paused","closed"], "description": "岗位状态筛选"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 20}
            },
            "required": []
        }
    },
    handler=lambda args, **kw: hr_position_list(
        tenant_id=kw.get("tenant_id", ""),
        status=args.get("status"),
        page=args.get("page", 1),
        page_size=args.get("page_size", 20),
        task_id=kw.get("task_id")
    ),
    check_fn=check_requirements,
    requires_env=["FASTAPI_BASE_URL"],
)
```

### 4.3 前端→Agent双入口架构

```
┌──────────────┐     ┌──────────────┐
│  Web前端     │     │  微信/飞书    │
│  (Vue 3)     │     │  (IM)        │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  FastAPI     │     │  Hermes      │
│  (:8000)     │     │  Agent       │
│              │     │  (:8642)     │
│  直接HTTP    │     │  对话式      │
│  CRUD+AI     │     │  Tool→Service│
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
       ┌──────────────┐
       │  Service层   │  ← 唯一业务逻辑
       │  (Python)    │
       └──────────────┘
```

---

## 五、结论

HireMind与Hermes Agent的集成方案**高度可行**。PRD作者深度理解Hermes架构，22项能力复用清单、Tool→Service调用关系、Skill→Tool矩阵设计精良。

**3处需微调**：
1. MCP Server列表统一（§8架构图 vs §9.6定义）
2. hr-crud-api MCP简化为Tool直连FastAPI
3. @AiCapability代码生成器推迟到Phase 2

**总体评分：8.5/10** — 集成设计优秀，仅需小幅修正。
