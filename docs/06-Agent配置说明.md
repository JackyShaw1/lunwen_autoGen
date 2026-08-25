# Agent 配置说明

> **文档版本**：v2.1
> **关联文档**：`02-产品需求文档PRD.md` F06、`04-技术实现文档.md` 第 2 章  
> **读者**：产品经理、教研管理员、开发实施人员

---

## 1. 「Agent 配置」在本系统里指什么？

在本项目中，**Agent 配置**不是泛指「所有 AI 设置」，而是一套可版本化、可热更新的**多智能体运行参数集合**，决定：

1. **每个 Agent 扮演什么角色**（Prompt、工具、模型）
2. **Agent 如何协作**（Sequential / GroupChat、顺序、轮次上限）
3. **生成过程如何控制**（重试、阈值、日志、Token 预算）
4. **学科差异如何注入**（管理学模板 vs 计算机模板）

教师侧只能**选择编排模板**；管理员/教研侧可**编辑 Agent 细节**。

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 配置体系（四层）                    │
├─────────────────────────────────────────────────────────────┤
│  L1 全局层    LLM 接入、Token 预算、内容安全、日志开关       │
│  L2 角色层    每个 Agent 的 Prompt / 模型 / 工具 / 输出格式   │
│  L3 编排层    工作流模板、Agent 顺序、GroupChat 规则          │
│  L4 学科层    学科插件包、案例结构模板、术语表                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 配置功能总览：用来干嘛？

| 功能模块 | 谁用 | 用来干嘛 | MVP |
|----------|------|----------|-----|
| **Agent 角色配置** | 管理员 | 定义每个 Agent 的职责、说话方式、输出结构 | ✅ |
| **Prompt 版本管理** | 管理员 | 调优 Prompt 后可回滚，对比 Rubric 分 | ✅ |
| **编排模板管理** | 管理员 + 教师 | 管理员定义流水线；教师创建案例时选用 | ✅ |
| **LLM 模型分配** | 管理员 | 强模型写正文、轻模型做评审，控成本 | ✅ |
| **Tool 工具绑定** | 管理员 | 让 Agent 调用校验、模板、评分等确定性能力 | ✅ |
| **学科插件包** | 管理员 | 同一 Agent 在不同学科注入不同模板与术语 | Should |
| **运行时参数** | 管理员 | max_round、重试次数、Reviewer 通过阈值 | ✅ |
| **对话日志策略** | 管理员 | 是否记录完整 Agent 输入输出（教研调试） | ✅ |
| **配置预览 / 试跑** | 管理员 | 改 Prompt 后用样例参数跑单次 Agent 看效果 | Should |
| **Skill 运行追踪** | 管理员/教研 | 查看每个 Agent 实际加载的 Skill 与版本 | ✅ |
| **人机协同节点** | 教师 | 大纲确认后再进入 Writer（Human-in-the-loop） | v1.1 |

---

## 3. 七个 Agent 角色：各自干什么、配置什么？

### 3.1 角色一览

| Agent | 在案例生成中的作用 | 若不配置或配置不当的后果 |
|-------|-------------------|-------------------------|
| **TeacherProxy** | 把教师表单参数封装成任务指令，驱动整条链路 | 参数丢失、生成内容与教师意图不符 |
| **CasePlanner** | 设计案例结构：背景→冲突→**决策点**、角色关系 | 案例平淡、无讨论价值、结构散乱 |
| **DomainExpert** | 补充学科/行业情境、术语、约束（虚构但合理） | 案例不专业、术语错误、情境离谱 |
| **CaseWriter** | 撰写案例正文叙事 | 文笔差、过早给出结论、字数失控 |
| **PedagogyDesigner** | 设计分层讨论题、课堂活动、教师引导要点 | 只有阅读题、课堂无法研讨 |
| **Reviewer** | 按 Rubric 打分，给出修订意见，决定是否 pass | 低质量案例直接入库 |
| **Editor（可选）** | 根据 Reviewer 意见做定向修订 | GroupChat 时 Writer 负担过重 |

### 3.2 各 Agent 产出与下游依赖

```
TeacherProxy     → 任务包（教师参数 JSON）
CasePlanner      → CaseOutline JSON（大纲、决策点、角色表）
DomainExpert     → ContextPack JSON（情境素材、术语、约束）
CaseWriter       → body.narrative（案例正文）
PedagogyDesigner → discussion_questions + instructor_guide 初稿
Reviewer         → quality 评分 + revision_advice + pass/fail
Editor           → 修订后的案例包片段
```

**配置原则**：下游 Agent 的 Prompt 里应说明「只消费上游结构化字段」，避免全文堆砌导致 Token 爆炸。

### 3.3 每个 Agent 可配置项（角色层）

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `system_message` | 角色人设与硬性规则 | 「必须包含决策点」「禁止编造真实企业」 |
| `description` | AutoGen 内部角色描述（GroupChat 选人时用） | 「负责讨论题与课堂活动设计」 |
| `llm_config.model` | 该 Agent 使用的模型 | Planner: gpt-4o；Reviewer: deepseek-chat |
| `llm_config.temperature` | 创造性 vs 稳定性 | Writer 0.7；Reviewer 0.2 |
| `max_tokens` | 单次输出上限 | Writer 4096 |
| `output_schema` | 强制输出结构 | `CaseOutline`、`RubricResult` |
| `tools` | 绑定的 Tool 列表 | Reviewer → `compute_rubric_score` |
| `retry.max_attempts` | 本 Agent 失败重试次数 | 2 |
| `enabled` | 是否在当前编排中启用 | Editor 仅 groupchat 模板启用 |

---

## 4. 单 Agent YAML 配置字段详解

完整配置文件路径：`backend/app/agents/{agent_name}.yaml`

```yaml
# 元信息
name: CasePlanner              # Agent 唯一标识，与代码和运行日志一致
type: ConversableAgent         # AutoGen 类型：ConversableAgent / UserProxyAgent
description: |                 # 短描述，GroupChat 时辅助选人
  教学案例结构策划专家

# 核心 Prompt（教研最常改的部分）
system_message: |
  你是资深教学设计专家……
  变量占位符：{subject} {course} {case_type} 由系统在加载时注入

# LLM 参数（可覆盖全局默认）
llm_config:
  model: gpt-4o
  temperature: 0.4
  max_tokens: 2048
  timeout: 120

# 输出约束
output:
  format: json                 # json | markdown | text
  schema: CaseOutline          # 对应 Pydantic 模型名，用于校验与重试
  strict: true                 # 校验失败是否自动重试

# 工具能力
tools:
  - load_subject_template      # 允许调用的 Tool 名称列表
  - validate_case_schema

# 运行时
runtime:
  max_turns: 1                 # 单次 invoke 最大对话轮次（流水线通常为 1）
  retry:
    max_attempts: 2
    on: [schema_error, timeout, empty_output]

# 日志
logging:
  record_full_io: false        # true=存完整 IO（调试）；false=只存摘要
  io_max_chars: 2000           # 摘要最大字符

# 版本
version: "1.2.0"
is_active: true
```

### 字段用途速查

| 字段 | 用来干嘛 |
|------|----------|
| `name` | 编排、日志、WebSocket 进度的统一 ID |
| `type` | 决定 AutoGen 实例化方式（是否人类介入） |
| `system_message` | **核心**：角色边界、输出格式、合规红线 |
| `llm_config` | 按 Agent 分模型，平衡质量与成本 |
| `output.schema` | 防止 LLM 返回无法解析的内容，支撑自动重试 |
| `tools` | 把「校验、打分、读模板」交给代码，减少幻觉 |
| `runtime.max_turns` | 防止 Agent 与用户代理无限对话 |
| `runtime.retry` | 单 Agent 失败不拖垮整条流水线 |
| `logging` | 教研调试 vs 隐私/存储成本 |
| `version` / `is_active` | 多版本 Prompt 并存，一键切换 |

---

## 5. 编排模板配置：Agent 怎么协作

配置文件：`backend/app/autogen/workflows/templates/{template_id}.yaml`

### 5.1 预置模板

| 模板 ID | 模式 | Agent 顺序 / 规则 | 适用场景 |
|---------|------|-------------------|----------|
| `sequential_standard` | Sequential | Planner→Expert→Writer→Pedagogy→Reviewer | 默认，稳定省时 |
| `groupchat_review` | Sequential + GroupChat | 同上，Reviewer 不 pass 时 Writer+Pedagogy+Reviewer 群聊 ≤6 轮 | 质量优先 |
| `human_outline` | Sequential + HITL | Planner 后暂停，教师确认大纲再继续 | 教研审核严 |

### 5.2 编排 YAML 示例

```yaml
id: sequential_standard
name: 标准流水线（五 Agent）
description: 顺序执行，Reviewer 不通过时记录建议，不自动修订

workflow:
  type: sequential
  agents:
    - TeacherProxy
    - CasePlanner
    - DomainExpert
    - CaseWriter
    - PedagogyDesigner
    - Reviewer

  context_passing: summary          # full | summary | structured_json
  context_max_tokens: 1500            # 传给下游的上下文上限

  on_reviewer_fail:
    action: complete_with_warning     # 或 trigger_groupchat
    max_revision_rounds: 0

groupchat:                            # 仅 groupchat_review 模板使用
  participants: [CaseWriter, PedagogyDesigner, Reviewer]
  max_round: 6
  speaker_selection: auto
  termination:
    - reviewer_pass
    - max_round_reached

limits:
  total_timeout_seconds: 900          # 单任务总超时 15 分钟
  max_total_tokens: 50000             # 任务 Token 预算
```

### 5.3 编排项用途

| 配置项 | 用来干嘛 |
|--------|----------|
| `workflow.type` | sequential / groupchat / hybrid |
| `agents` 顺序 | 决定流水线先后，**顺序错误会导致上下文缺失** |
| `context_passing` | 控制 Token：摘要传递 vs 全文传递 |
| `on_reviewer_fail` | Reviewer 不达标时是警告结束还是进入修订循环 |
| `groupchat.max_round` | **防失控**：限制多 Agent 互聊轮次 |
| `limits.total_timeout` | 防止 Celery 任务永久挂起 |
| `limits.max_total_tokens` | **成本控制**：超预算终止任务 |

---

## 6. Tool 工具注册：Agent 能调用哪些「硬能力」

配置文件：`backend/app/autogen/tools/registry.yaml`

| Tool 名称 | 绑定 Agent | 用来干嘛 | 为何不用纯 LLM |
|-----------|-----------|----------|----------------|
| `validate_case_schema` | Writer, Pedagogy | 校验 JSON 是否符合 CasePackage 子结构 | 结构化可靠 |
| `load_subject_template` | Planner, Expert | 加载学科案例结构模板 | 学科差异可配置 |
| `compute_rubric_score` | Reviewer | 规则分 + LLM 分混合计算 Rubric | 评分可复现 |
| `apply_content_provenance_policy` | Planner、Expert、Writer、Reviewer | 按教师要求选择虚构教学情境或事实溯源模式；事实型案例绑定审核来源 | 防止“要求真实”却仍套虚构模板 |
| `check_content_safety` | 全部 | 敏感词 / 违规检测 | 合规 |
| `truncate_context` | Orchestrator | 压缩上游输出再传给下游 | 控 Token |
| `export_docx` / `export_pdf` / `export_pptx` | 无（API 层） | 导出授课包与课件 | 与生成链路分离 |

**配置含义**：在 Agent YAML 的 `tools` 列表中声明后，AutoGen 才会把该 Tool 注册给对应 Agent；未绑定则 Agent 无法调用。

### 6.1 当前 Application Skills

当前 Skills 位于 `backend/app/skills/`，不是静态提示词附件，而是由 `skill_loader.py` 在运行时按 Agent、学科和案例类型选择说明、参考资料或确定性脚本。

| Skill | 主要使用者 | 作用 |
|-------|------------|------|
| `design-instructional-plan` | Planner、PedagogyDesigner、Reviewer | 生成可观察目标、分层讨论题、课堂节奏与目标证据对齐 |
| `apply-case-pattern` | Planner、Writer、Reviewer | 按决策型、分析型、诊断型、模拟型、伦理困境型选择叙事模式 |
| `adapt-subject-context` | Planner、DomainExpert、Writer | 注入学科术语、情境约束和专业合理性要求 |
| `validate-case-package` | Writer、PedagogyDesigner、Reviewer、保存/导出 API | 检查结构、目标对齐、重复内容、正文 95%–105% 字数门禁；事实型案例额外检查来源、知识锚点、原始教师要求与课程思政 |

事实型案例不得仅依靠 Prompt 自律。编排器先执行真实性预检；命中审核资料包后，CasePlanner 保留教师原始要求，DomainExpert 声明事实边界，CaseWriter 仅组织已审核事实，Reviewer 检查正文引用与来源表。没有课程级资料包时直接停止，不调用通用虚构模板。

每次生成会把 Agent 对应的 Skill 名称、修订号和所选参考资料写入 `meta.skill_trace`，方便追溯线上案例使用了哪套方法。

---

## 7. 学科插件包：同一 Agent 如何适配不同学科

路径：`backend/app/agents/subjects/{subject_id}/`

```
subjects/management/
├── template_outline.json      # 管理学案例结构偏好（如强调组织冲突）
├── terminology.json           # 术语表
├── planner_prompt_snippet.md  # 注入 Planner system_message 的片段
└── expert_context_hints.md    # 注入 DomainExpert 的行业背景提示
```

| 配置动作 | 用来干嘛 |
|----------|----------|
| 上传学科包 | 新增「经济学」「计算机」等 without 改代码 |
| `subject_id` 与教师表单联动 | 教师选「管理学」→ 自动加载 management 插件 |
| 插件版本号 | 教研迭代学科模板时可回滚 |

---

## 8. 全局层配置（环境变量 / 系统设置）

| 配置项 | 用来干嘛 |
|--------|----------|
| `OPENAI_API_KEY` / 兼容 API Base | LLM 接入 |
| `DEFAULT_LLM_MODEL` | 未单独指定模型的 Agent 回退默认值 |
| `AGENT_LOG_RETENTION_DAYS` | Agent 对话日志保留天数 |
| `REVIEWER_PASS_THRESHOLD` | 全局默认通过分（默认 4.0） |
| `CELERY_TASK_TIMEOUT` | 异步任务硬超时 |
| `CONTENT_FILTER_ENABLED` | 是否启用内容安全 Tool |

教师**不可改**全局层；管理员通过 `.env` 或系统设置页（可选）调整。

---

## 9. 管理后台功能清单（F06 细化）

路由：`/admin/agents`（仅 `role=admin`）

### 9.1 Agent 列表页

| 功能 | 用来干嘛 |
|------|----------|
| 查看所有 Agent | 一眼看到角色分工与启用状态 |
| 启用/停用 Agent | 临时关闭 Editor 等可选角色 |
| 查看当前激活版本 | 知道线上跑的是哪版 Prompt |

### 9.2 Agent 详情 / 编辑页

| 功能 | 用来干嘛 |
|------|----------|
| 编辑 `system_message` | **教研调优主战场** |
| 调整 temperature / model | 质量与成本权衡 |
| 绑定 / 解绑 Tools | 控制 Agent 可调用的硬能力 |
| 设置 output_schema | 约束输出结构 |
| 保存为新版本 | 不覆盖旧版，支持 A/B |
| 激活指定版本 | 上线某版 Prompt |
| 版本对比（diff） | 查看两版 Prompt 差异 |
| 试跑（Sample Run） | 用内置样例参数跑**单个** Agent，看输出 |

### 9.3 编排模板页

| 功能 | 用来干嘛 |
|------|----------|
| 模板列表 | sequential / groupchat / human_outline |
| 编辑 Agent 顺序 | 调整流水线（高级管理员） |
| 编辑 max_round、超时、Token 预算 | 防失控、控成本 |
| 设为默认模板 | 教师创建案例时的默认选项 |

### 9.4 学科插件页

| 功能 | 用来干嘛 |
|------|----------|
| 上传学科 ZIP | 批量更新模板与术语 |
| 预览注入效果 | 看 Planner Prompt 拼接结果 |

### 9.5 运行监控页（可选）

| 功能 | 用来干嘛 |
|------|----------|
| Agent 平均耗时 | 发现瓶颈 Agent |
| Token 消耗按 Agent 分布 | 成本优化 |
| Rubric 分按版本对比 | 评估 Prompt 改版效果 |

---

## 10. 教师侧 vs 管理员侧：配置边界

| 能力 | 教师 | 管理员 |
|------|------|--------|
| 选择编排模板 | ✅ 创建案例时下拉 | ✅ 定义模板 |
| 编辑 Agent Prompt | ❌ | ✅ |
| 选择学科（触发插件） | ✅ | ✅ 维护插件内容 |
| 查看 Agent 协作日志 | ✅ 可选开关 | ✅ 完整日志 |
| 修改 LLM 模型 | ❌ | ✅ |
| 修改 Rubric 阈值 | ❌ | ✅ |

---

## 11. 配置变更流程（推荐）

```
教研提出调优需求
    ↓
管理员在「试跑」环境改 Prompt / 编排
    ↓
scripts/evaluate_cases.py 跑评测集对比 Rubric
    ↓ 综合分下降 < 3%
保存新版本 → 激活
    ↓
观察线上 1-3 天 Token / 满意度
    ↓ 不达标
回滚至上一 is_active 版本
```

---

## 12. 与代码模块对应关系

| 配置类型 | 存储位置 | 加载模块 |
|----------|----------|----------|
| Agent YAML | `app/agents/*.yaml` + DB `agent_configs` | `agent_factory.py` |
| 编排模板 | `app/autogen/workflows/templates/` | `workflows/loader.py` |
| Tool 注册 | `app/autogen/tools/registry.yaml` | `tools/registry.py` |
| 学科插件 | `app/agents/subjects/` | `subject_plugin_loader.py` |
| 全局参数 | `.env` / `config.py` | `app/config.py` |

---

## 13. 常见问题

**Q：改 Prompt 需要重启服务吗？**  
A：从 DB 加载且带缓存刷新接口时**不需要**；仅改本地 YAML 文件时需重启或触发配置热加载。

**Q：教师选「深度评审」和「标准流水线」本质差什么？**  
A：差在**编排模板**：是否启用 GroupChat、max_round、Reviewer 失败后是否自动修订。

**Q：为什么 Writer 和 Reviewer 要用不同模型？**  
A：Writer 要创造力（可略高 temperature + 强模型）；Reviewer 要稳定（低 temperature + 便宜模型亦可）。

**Q：为什么不再提供“局部重跑讨论设计”？**

A：局部重跑容易造成讨论题、教师参考和目标对齐表之间版本错配。当前产品只允许人工编辑案例包；若需要重新生成内容，重新执行完整五 Agent 链并经过统一质量门禁，保证四件套一致。

---

*Agent 配置与 Application Skills 是 CaseAutoGenSystem 的核心可运营资产；本文已按 v2.1.0 Agent 配置和当前运行时 Skill 机制同步。*
