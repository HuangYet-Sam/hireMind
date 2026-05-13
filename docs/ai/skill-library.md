# 招聘Skill库 (Skill Library)

> **PRD来源**：§5.4 招聘Skill库（L2870-L2903）、附录B Cron任务配置（L7650-L7665）、附录D Skill清单（L7684-L7698）
> **更新日期**：2026-05-12

---

## 1. Skill库概述（§5.4）

> **新增于**：第十三轮研讨 | **裁决#31** | **优先级**：⭐⭐⭐⭐

Hermes Skill是活的AI流程（非死规则模板），描述"做什么+怎么思考"。预置8个核心招聘Skill，且支持HR通过对话创建自定义Skill。

---

## 2. 预置Skill清单

| Skill名称 | 功能 | 触发场景 | 对应Tool |
|-----------|------|---------|----------|
| `hr-daily-briefing` | 每日招聘简报（待办+关键指标+AI洞察） | Cron定时 | hr_analytics |
| `hr-candidate-screen` | 候选人深度筛选（技能验证+经验评估+文化匹配） | 候选人详情→AI操作 | hr_profile + hr_matching |
| `hr-interview-prep` | 面试准备（考察清单+模拟问答+风险评估） | 面试前触发 | hr_interview |
| `hr-interview-debrief` | 面试复盘（3维度分析+决策建议+画像更新） | 面试后触发 | hr_interview + hr_profile |
| `hr-offer-strategy` | Offer策略（薪资建议+谈判要点+风险预案） | 发起Offer时 | hr_offer |
| `hr-funnel-diagnosis` | 招聘漏斗诊断（瓶颈定位+根因分析+改进方案） | 分析页→AI操作 | hr_analytics + hr_db |
| `hr-talent-pool-scan` | 人才库扫描（沉睡候选人激活+匹配新岗位） | Cron定时/手动 | hr_talent_pool + hr_matching |
| `hr-weekly-review` | 招聘周报（完成情况+下周计划+趋势分析） | Cron定时 | hr_analytics |

---

## 3. Skill→Tool调用矩阵（P2-10）

| Skill | Tool 1 | Tool 2 | Tool 3 | 调用链说明 |
|-------|--------|--------|--------|-----------|
| `hr-daily-briefing` | hr_analytics | — | — | 查询待办+指标→生成简报 |
| `hr-candidate-screen` | hr_profile | hr_matching | — | 获取画像→执行匹配→综合评估 |
| `hr-interview-prep` | hr_interview | hr_profile | hr_matching | 获取面试信息→查画像→匹配分析→生成考察清单 |
| `hr-interview-debrief` | hr_interview | hr_profile | — | 获取反馈→更新画像→生成分析报告 |
| `hr-offer-strategy` | hr_offer | hr_analytics | hr_profile | 获取岗位+候选人→薪资对标→生成策略 |
| `hr-funnel-diagnosis` | hr_analytics | hr_db | — | 查询漏斗数据→瓶颈定位→生成改进方案 |
| `hr-talent-pool-scan` | hr_talent_pool | hr_matching | — | 扫描沉睡候选人→匹配新岗位→生成激活列表 |
| `hr-weekly-review` | hr_analytics | — | — | 汇总周数据→生成周报 |

---

## 4. 自定义Skill

HR可对话创建自定义Skill，如"每次有新简历进来，帮我用技术部的标准先筛选一遍，通过的自动推给我"→Agent编码为Skill并激活。

Skill通过Hermes Curator机制自进化——执行效果不佳时自动优化Prompt。

---

## 5. Cron任务配置（附录B）

> **P1-21对齐说明**：以下Cron任务与§5.6主动式AI引擎9类场景一一对应。场景1（新简历自动筛选）和场景6（高匹配候选人推荐）为Webhook/回调触发，不配置Cron。

| 任务名 | Cron表达式 | Skill | 对应§5.6场景 | 说明 |
|--------|-----------|-------|-------------|------|
| 面试前准备包推送 | `0 */2 * * *` | hr-interview-prep | 场景2：面试前准备包推送 | 每2h扫描未来2h面试，推送考察清单给面试官 |
| 岗位超期预警 | `0 8 * * *` | hr-daily-briefing | 场景3：岗位超期预警 | 每日8:00扫描超期岗位，推送预警 |
| Offer跟进提醒 | `0 9 * * *` | hr-daily-briefing | 场景4：Offer跟进提醒 | 每日9:00扫描待跟进Offer，推送提醒 |
| 招聘周报 | `0 17 * * 5` | hr-daily-briefing | 场景5：招聘周报 | 每周五17:00生成本周招聘漏斗统计 |
| 漏斗异常预警 | `0 22 * * *` | hr-funnel-diagnosis | 场景7：漏斗异常预警 | 每日22:00分析漏斗转化率异常 |
| 沉睡候选人激活 | `0 9 * * 1` | hr-talent-pool-scan | 场景8：沉睡候选人激活 | 每周一9:00扫描沉睡候选人，匹配新岗位 |
| 岗位匹配刷新 | `0 8 * * *` | hr-candidate-screen | 场景3补充：每日匹配新简历到开放岗位 | 每日匹配新简历到开放岗位 |
| 面试提醒 | `0 8,14 * * *` | hr-interview-prep | 场景2补充：面试当日提醒 | 面试前1小时提醒HR |
| 入职前关怀提醒 | `0 9 * * *` | hr-daily-briefing | 场景9：入职前关怀提醒 | 每日9:00扫描入职前1天/Day7/30/60候选人，推送关怀提醒 |

---

## 6. Skill文件清单（附录D）

> 与§5.4招聘Skill库（权威清单）对齐，统一命名规范为 `hr-{capability}` 格式。

| Skill名 | 文件位置 | 触发条件 | 流程摘要 |
|---------|---------|---------|---------|
| hr-daily-briefing | `skills/hr/hr-daily-briefing/SKILL.md` | Cron定时（每日8:00） | 汇总待办→关键指标→AI洞察→推送简报 |
| hr-candidate-screen | `skills/hr/hr-candidate-screen/SKILL.md` | 候选人详情→AI操作 | 技能验证→经验评估→文化匹配→筛选报告 |
| hr-interview-prep | `skills/hr/hr-interview-prep/SKILL.md` | 面试前触发（Cron面试前2h） | 确认岗位→生成考察清单→模拟问答→风险评估 |
| hr-interview-debrief | `skills/hr/hr-interview-debrief/SKILL.md` | 面试后触发 | 3维度分析→决策建议→画像更新→看板流转 |
| hr-offer-strategy | `skills/hr/hr-offer-strategy/SKILL.md` | 发起Offer时 | 薪资建议→谈判要点→风险预案→对标分析 |
| hr-funnel-diagnosis | `skills/hr/hr-funnel-diagnosis/SKILL.md` | 分析页→AI操作 | 瓶颈定位→根因分析→改进方案→历史对比 |
| hr-talent-pool-scan | `skills/hr/hr-talent-pool-scan/SKILL.md` | Cron定时/手动 | 统计→识别沉睡→匹配新岗位→推送建议 |
| hr-weekly-review | `skills/hr/hr-weekly-review/SKILL.md` | Cron定时（每周五17:00） | 完成情况→下周计划→趋势分析→数据看板 |
