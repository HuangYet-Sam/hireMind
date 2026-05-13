# 认证与权限

> **PRD来源**：§9.3 认证与权限、§2.4 用户权限矩阵、§2.5 技术实现要点、§11.2 安全要求

---

## 1. 认证方案

### 1.1 JWT Token认证

```
登录流程：
  POST /api/v1/auth/login { username, password }
  → 验证 → 返回 JWT Token（含tenant_id, user_id, role）
  → 后续请求 Header: Authorization: Bearer <token>

Token结构：
  {
    "user_id": "uuid",
    "tenant_id": "company-a",
    "role": "recruiter",
    "exp": 1715385600
  }
```

### 1.2 JWT签名密钥管理（P1-16安全修复）

4套JWT签名密钥全部存储于HashiCorp Vault，纳入90天轮换周期：

| 密钥路径 | 用途 | 有效期 | 特性 |
|---------|------|--------|------|
| `hiremind/{tenant_id}/jwt/system` | 系统用户登录认证Token | 24h | 常规登录 |
| `hiremind/{tenant_id}/jwt/feedback` | 面试官反馈表单Token | 24h | 一次性使用 |
| `hiremind/{tenant_id}/jwt/share` | 候选人共享页面Token | 7天 | 支持撤销 |
| `hiremind/{tenant_id}/jwt/sse` | SSE连接认证Token | 5分钟 | 一次性使用 |

**密钥轮换策略**：轮换时旧密钥保留30天并行期（验证旧Token有效），新Token使用新密钥签名。密钥访问审计：每次JWT密钥读取/轮换操作写入Vault审计日志。

---

## 2. RBAC权限矩阵

### 2.1 系统用户权限（2种角色）

> **PRD来源**：§2.4 用户权限矩阵

| 功能模块 | HR Admin | HR Recruiter |
|---------|:---:|:---:|
| 岗位管理 | 全部 | 全部 |
| 简历解析 | 全部 | 全部 |
| 人才画像 | 全部 | 查看+标注 |
| 智能匹配 | 全部（含配置） | 执行+查看 |
| 面试管理 | 全部 | 协调+查看 |
| Offer管理 | 全部 | 发起+查看 |
| 数据分析 | 全部 | 查看 |
| 系统设置 | ✅ | ❌ |
| 用户管理 | ✅ | ❌ |
| **薪资字段可见性（L4字段级）** | **查看Offer时可见完整薪资（`salary_encrypted`解密展示）** | **查看Offer时薪资字段自动脱敏为 `***`，仅HR Admin+可见完整薪资** |

> **P1-15修复**：L4级薪资数据实施字段级可见性控制。HR Recruiter查看Offer详情时，`salary_encrypted` 字段在API层返回脱敏值 `***`；仅HR Admin（及更高权限角色）可查看解密后的完整薪资数据。字段级脱敏在Service层 `_authorize()` 装饰器中实现，根据 `request.user.role` 自动决定返回明文或掩码。

### 2.2 端点分类权限

| 端点分类 | HR Admin | HR Recruiter | 说明 |
|---------|:---:|:---:|------|
| 部门CRUD | ✅ | ❌ | 仅Admin可增删改部门，Recruiter可查看部门列表 |
| 岗位CRUD | ✅ | ✅ | — |
| 简历操作 | ✅ | ✅ | — |
| 匹配执行 | ✅ | ✅ | — |
| 面试管理 | ✅ | ✅ | HR创建面试，系统自动发表单给面试官 |
| 面试反馈 | Token URL（无需登录） | — | 面试官通过Token链接提交 |
| Offer管理 | ✅ | 发起+查看 | 审批通过IM，不需要系统端点 |
| 数据分析 | ✅ | ✅ | 含AI洞察 |
| 系统设置 | ✅ | ❌ | 仅Admin |

### 2.3 流程参与者权限

| 角色 | 查看面试列表 | 提交反馈 | 查看Offer详情 | 审批操作 | 查看关联岗位分析 | 其他操作 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Interviewer（面试官） | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approver（审批人） | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Hiring Manager（用人经理） | ❌ | ❌ | ❌ | ❌ | ✅（只读） | ❌ |

> **说明**：Interviewer和Approver通过Token链接（无需登录系统）完成各自操作。Hiring Manager通过HR生成的只读共享链接查看关联岗位分析Dashboard。

### 2.4 流程参与者交互方式

| 参与者 | 交互方式 | 触发场景 | 数据回流 |
|--------|---------|---------|---------|
| 面试官 | 表单链接（Token URL） | 面试前1天收到提醒+面后收到反馈表单 | 评分+反馈文本→面试记录+画像更新 |
| 用人经理 | IM消息 | 候选人推荐、Offer审批 | "同意/拒绝"→审批状态更新 |
| 审批人 | IM消息 | 招聘需求审批、Offer审批 | "同意/拒绝"→审批状态更新 |

---

## 3. 技术实现要点

> **PRD来源**：§2.5 技术实现要点

### 3.1 面试反馈表单（JWT Token安全机制）

```
1. HR创建面试时，系统为每位面试官生成 JWT feedback_tokens（JSONB数组，每项含interview_id+interviewer_id+exp签名校验，有效期24小时）
2. 面试前发送提醒时，附上链接：https://hiremind.xxx/feedback/{token}
3. 面试官点击链接 → 系统验证JWT签名+有效期 → 展示预填信息的反馈表单
4. 提交频率限制：同一Token 5分钟内最多3次提交（Redis计数器）
5. 提交成功后 → Token立即失效（服务端黑名单，Redis SET feedback:used:{token_id}，TTL=token原有效期）
6. 无需登录、无需注册、一次性使用
7. 每次Token验证/提交记录访问日志（IP/UA/时间）
```

### 3.2 IM审批（Agent解析机制 + 身份验证）

```
1. HR发起审批 → Agent通过IM向审批人发送消息（含审批摘要 + 6位一次性验证码）
2. 审批人回复"同意+验证码"或"拒绝+验证码" → Agent验证身份 → 识别意图
   - 验证码绑定审批人ID+审批单ID，30分钟有效期，使用后立即失效
   - 高风险操作（Offer月薪>50K）额外触发SMS二次验证：向审批人手机发送4位确认码
3. Agent验证通过后调用对应API更新审批状态
4. 通知HR审批结果
5. 验证码无效/过期 → Agent提示"验证码无效，请查看最新审批消息中的验证码"
```

### 3.3 AgentContext安全条款

> ⚠️ **安全约束**：Agent→Tool→Service调用链的身份基石，确保不可伪造、不可篡改。

- **不可变性**：AgentContext为frozen dataclass，创建后任何字段修改均抛异常
- **身份来源**：tenant_id/user_id仅从JWT Token解析注入，禁止从对话内容、请求参数、环境变量中提取
- **HMAC签名保护**：创建时计算`HMAC-SHA256(server_secret_key, tenant_id + user_id + session_id)`，签名存于`_signature`字段
- **Tool层强制验签**：每个Tool方法入口必须调用`ctx.verify_integrity()`，签名不匹配立即抛出`SecurityError`，阻断调用链
- **Worker Agent继承约束**：Master Agent派生Worker时，Worker的AgentContext必须原样继承Master的tenant_id/user_id，Worker禁止自定义或覆盖身份字段
- **签名校验失败处理**：SecurityError触发审计告警（写入`audit_logs`，source=`agent_context_violation`），并拒绝当前操作

---

## 4. IM发送者身份验证机制（P0-07安全修复）

> ⚠️ **安全修复**：IM审批需验证发送者身份，防止冒充审批。

### 4.1 IM发送者ID→系统用户映射

| IM平台 | 发送者标识 | 映射方式 | 存储 |
|--------|----------|---------|------|
| 微信 | `FromUserName`（openid） | HR在系统后台绑定审批人微信openid | `im_user_bindings` 表 |
| 飞书 | `user_id` / `open_id` | 飞书企业通讯录自动映射 | `im_user_bindings` 表 |
| 钉钉 | `userid` | 钉钉企业通讯录自动映射 | `im_user_bindings` 表 |

`im_user_bindings` 表结构：

```sql
CREATE TABLE im_user_bindings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),         -- 系统用户（HR/Admin）
    im_platform     VARCHAR(20) NOT NULL CHECK(im_platform IN ('wechat','feishu','dingtalk','wecom')),
    im_user_id      VARCHAR(128) NOT NULL,                       -- IM平台用户标识
    role            VARCHAR(30) NOT NULL,                        -- 参与角色：approver/hiring_manager/interviewer
    display_name    VARCHAR(100),                                -- IM平台显示名
    verified        BOOLEAN DEFAULT FALSE,                       -- 是否已完成身份验证
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, im_platform, im_user_id)
);
```

### 4.2 审批验证码机制

- 6位一次性验证码（数字），存储于 Redis `approval:otp:{approval_id}:{im_user_id}`，TTL 30分钟
- 审批消息模板更新：`📋 Offer审批 #{id}\n...\n验证码：{6位码}\n请回复：同意+验证码 / 拒绝+验证码`
- 验证码校验通过后立即从Redis删除（一次性使用）
- Agent解析回复时先校验验证码，验证码不匹配则拒绝操作

### 4.3 高风险操作二次验证

- 触发条件：Offer月薪 > 50,000 元（阈值可配置）
- 二次验证方式：SMS验证码（4位），发送至审批人绑定的手机号
- 审批流程：IM回复"同意+OTP" → 校验OTP通过 → 触发SMS → 审批人回复"确认+SMS码" → 最终通过

---

## 5. 安全要求总表

> **PRD来源**：§11.2 安全要求

### 5.1 数据分类分级标准（P1-35安全修复，个保法第51条要求）

| 级别 | 分类 | 典型数据 | 存储要求 | 访问控制 | 操作要求 |
|------|------|---------|---------|---------|---------|
| **L1 公开** | 可对外公开的信息 | 岗位描述、公司信息、招聘公告 | 明文存储 | 无特殊限制 | 无特殊要求 |
| **L2 内部** | 组织内部工作信息 | 面试评价、匹配分数、候选人状态、面试安排 | 加密传输（TLS 1.3） | RBAC权限控制（仅授权HR/面试官可见） | 操作需记录审计日志 |
| **L3 敏感** | 个人敏感信息 | 候选人PII（姓名、手机、邮箱、身份证号） | AES-256加密存储，密钥独立管理 | 最小权限+按需解密+脱敏展示 | **必须记录审计日志**（谁在何时访问了谁的PII） |
| **L4 机密** | 高敏感业务数据 | 薪资、Offer详情、绩效评估、合同条款 | AES-256加密存储+独立密钥+MinIO加密桶 | 严格RBAC+字段级权限控制 | **需双人审批**（至少2名授权人员确认后方可查看/导出） |

### 5.2 各级别操作要求细则

- **L3审计日志**：每次加密数据的解密操作、PII字段访问、批量导出均需记录 `{operator_id, target_entity, fields_accessed, timestamp, purpose}`
- **L4双人审批**：薪资/Offer等L4数据的查看、修改、导出操作需发起审批流，至少1名HR+1名Admin同时授权；审批记录写入 `audit_logs`（source=`l4_approval`）
- **级别升级**：当数据关联场景升级（如面试评价关联到具体候选人PII），自动提升为最高涉及级别
- **定期核查**：每季度由合规负责人核查数据分级标签准确性，误分级数据限期修正

### 5.3 分级实现矩阵（P0-01安全修复）

| 级别 | DDL存储层 | API传输层 | 前端展示层 | 典型数据 |
|------|----------|----------|----------|---------|
| **L1 公开** | 明文存储（DDL明文字段） | API明文返回 | 前端明文展示 | 岗位描述、公司信息、招聘公告 |
| **L2 内部** | 明文存储（DDL明文字段） | API脱敏返回（按RBAC） | 前端按权限展示 | 岗位薪资预算、面试安排、候选人状态 |
| **L3 敏感** | AES-256加密存储（DDL VARCHAR密文） | API脱敏返回（手机/邮箱掩码）+按需解密需审计 | 前端按需展示（权限+二次验证） | 候选人PII（姓名、手机、邮箱、身份证号） |
| **L4 机密** | AES-256加密存储（DDL VARCHAR密文+独立密钥） | API双人审批后返回明文 | 前端掩码展示（`***`），HR Admin+审批后可见完整值 | Offer薪资、绩效评估、合同条款 |

### 5.4 安全要求总表

| 类别 | 要求 |
|------|------|
| 认证 | JWT Token，24h过期，Refresh Token 7天 |
| 授权 | RBAC 2种系统用户 + 6种流程参与角色（详见§7.7），API层统一拦截 |
| 数据加密 | 候选人敏感信息（手机/邮箱/身份证）AES-256加密存储 |
| 传输加密 | 全站HTTPS/TLS 1.3 |
| 密钥管理 | HashiCorp Vault（推荐）或MinIO KES（轻量部署）。密钥按tenant_id隔离，轮换周期90天。FastAPI启动时通过Vault API获取密钥，缓存至内存（TTL=1h），密钥不落盘、不写入日志 |
| 文件安全 | 简历文件存储在MinIO（私有化），签名URL访问 |
| 脱敏 | Agent输出自动脱敏（Hermes内置redact机制） |
| 审计 | 所有写操作记录审计日志（谁/何时/做了什么/结果） |
| SQL注入 | SQLAlchemy ORM + Pydantic参数校验 |
| XSS | Vue自动转义 + CSP策略 |
| CSRF | **Double Submit Cookie模式**：FastAPI中间件校验CSRF Token。GET/OPTIONS/HEAD请求豁免。SSE端点通过Header认证 |
| 多租户 | 所有查询强制带tenant_id，数据库行级隔离 |

### 5.5 双路径安全保障（V3.5新增）

1. **AgentContext签名验证**：Tool层入口强制调用`ctx.verify_integrity()`，HMAC-SHA256签名校验tenant_id/user_id完整性
2. **代码生成器安全校验**：SecurityValidationHook在生成后自动校验每个@AiCapability的permissions字段非空
3. **路径守卫**：`allowed_callers`字段限制每个AI能力只允许指定路径调用
4. **统一速率限制**：FastAPI中间件和Agent节流器共享Redis计数器
5. **生成代码完整性校验**：启动时计算generated/目录SHA256哈希，与CI产出哈希比对

### 5.6 审计增强

- audit_logs表新增`agent_intent`字段（TEXT，Agent操作的原始意图描述）
- audit_logs表新增`data_classification`字段（VARCHAR(4)，操作涉及的数据分级L1-L4）
