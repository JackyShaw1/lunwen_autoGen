# CaseAutoGenSystem Cursor 实现步骤与提示词

> **文档版本**：v2.1
> **项目定位**：基于 AutoGen 的**教学案例自动生成系统**（非论文生成）  
> **使用方式**：按 Phase 将提示词复制到 Cursor Agent 执行

---

## 使用指南

1. 执行前用 `@docs/02-产品需求文档PRD.md` 和 `@docs/04-技术实现文档.md` 提供上下文
2. **Phase 0 必须先完成 AutoGen Spike**，验证多 Agent 能产出教学案例四件套
3. 每 Phase 结束运行评测或手动查看样例案例
4. Agent Prompt 变更必须对比 Rubric 分

---

## Phase 0: AutoGen Spike 与项目初始化（第 1-3 天）

### Step 0.1 对齐产品定位

**提示词**：

```
请阅读 @docs/01-项目管理方案.md @docs/02-产品需求文档PRD.md @docs/04-技术实现文档.md。

重要：本项目是「AutoGen 教学案例自动生成系统」，不是学术论文生成系统。
产出是教学案例四件套：案例正文、讨论题、教师参考、教学目标对齐表。

请更新 @README.md，明确产品定位与技术核心（Microsoft AutoGen 多智能体）。
创建 .gitignore 和 .env.example（OPENAI_API_KEY、DATABASE_URL、REDIS_URL 等）。
```

### Step 0.2 AutoGen 最小 Spike（最关键）

**提示词**：

```
在 backend/ 下创建 AutoGen Spike，验证教学案例多 Agent 协作可行。

要求：
1. Python 3.11，安装 ag2（或 autogen）：pip install ag2
2. 创建 backend/spike/sequential_case_spike.py
3. 实现 3 个 ConversableAgent + 1 个 UserProxyAgent：
   - CasePlanner：根据教师参数生成案例大纲 JSON（含决策点、角色）
   - CaseWriter：根据大纲撰写案例正文（1500-3000 字 Markdown）
   - Reviewer：按 Rubric 输出评分 JSON（overall 1-5，pass 阈值 4.0）

4. 使用 Sequential 方式链式调用（initiate_chats 或手动传递上下文）
5. 硬编码测试参数：
   - 主题：制造企业数字化转型中的组织阻力
   - 学科：管理学，课程：组织行为学，本科，决策型案例
   - 教学目标：分析变革阻力、识别利益相关方冲突

6. 最终将 Planner+Writer 产出组装为 CasePackage JSON 打印到控制台
7. llm_config 从环境变量读取，支持 OpenAI 兼容 API

不要搭建完整 Web 服务，先证明 Agent 链路能产出可讨论的教学案例。
参考 @docs/04-技术实现文档.md 中的 Agent 设计与 Schema。
```

### Step 0.3 案例 Schema 与 Rubric

**提示词**：

```
根据 @docs/02-产品需求文档PRD.md 中的 Case Package Schema，
创建 backend/app/schemas/case_package.py（Pydantic 模型）：

包含：meta, learning_objectives, body, discussion_questions,
instructor_guide, alignment_matrix, quality

创建 backend/app/services/rubric_service.py：
- 输入 CasePackage，输出各维度分与综合分
- 规则检查：是否有 decision_point、讨论题不少于 5 个、目标对齐表非空
- 可选调用 LLM 做讨论价值评估

创建 scripts/evaluate_cases.py：读取 JSON 案例文件输出 Rubric 报告。
```

### Step 0.4 项目脚手架

**提示词**：

```
 Spike 通过后，搭建完整项目脚手架：

后端：FastAPI + SQLAlchemy + Alembic + Celery
- 表结构见 @docs/04-技术实现文档.md（users, case_tasks, case_packages, agent_run_logs, agent_configs）
- /health 端点

前端：React + Vite + TailwindCSS
- 路由：dashboard, case/new, case/:id/generate, case/:id, case/:id/export
- 空壳页面 UI 参照 @docs/03-产品原型.html

docker-compose：PostgreSQL + Redis

将 spike 中的 Agent 逻辑迁移到 backend/app/autogen/ 目录结构。
```

---

## Phase 1: AutoGen Agent 工程化（第 4-7 天）

### Step 1.1 Agent 工厂与 YAML 配置

**提示词**：

```
实现 AutoGen Agent 配置化加载：

1. backend/app/agents/*.yaml — 五个 Agent 完整配置：
   CasePlanner, DomainExpert, CaseWriter, PedagogyDesigner, Reviewer
   参照 @docs/04-技术实现文档.md 的 YAML 示例

2. backend/app/autogen/agent_factory.py
   - load_agent_config(name) -> dict
   - create_agent(name, llm_config) -> ConversableAgent
   - 支持 system_message 中的 {subject} 等变量替换

3. 每个 Agent 的 system_message 必须强调「教学案例」而非学术论文：
   - 情境、冲突、决策点、讨论价值
   - 虚构情境声明
   - 输出格式严格 JSON 或 Markdown 区块

编写 tests/test_agent_factory.py
```

### Step 1.2 Sequential 五 Agent 流水线

**提示词**：

```
实现 backend/app/autogen/workflows/sequential_pipeline.py

完整流水线：
TeacherProxy → CasePlanner → DomainExpert → CaseWriter → PedagogyDesigner → Reviewer

要求：
1. 输入：CaseTaskCreate（教师表单参数 dict）
2. 每步将上一步输出摘要注入下一步 message（控制 Token）
3. 每步记录 agent_run_logs（agent_name, duration, token, output_summary）
4. Reviewer 输出 pass=false 时记录 revision_advice（MVP 可先不自动修订）
5. 输出：validated CasePackage Pydantic 对象
6. 异常：单 Agent 失败重试 2 次

创建 CaseOrchestratorService 封装调用。
参考 spike 代码迁移，不要重复造轮子。
```

### Step 1.3 Celery 异步任务

**提示词**：

```
实现异步案例生成：

1. backend/celery_app.py + generate_case_task(task_id)
2. POST /api/cases/{id}/generate 触发 Celery
3. 任务状态：pending → running → completed / failed
4. case_tasks.status 与 case_packages 写入联动
5. WebSocket /ws/cases/{id} 推送 agent_progress 消息
   格式见 @docs/04-技术实现文档.md

确保 Celery worker 能正确加载 AutoGen（注意进程内 LLM 调用超时设置）。
```

---

## Phase 2: 教师端核心功能（第 8-11 天）

### Step 2.1 认证与案例任务 API

**提示词**：

```
实现教师端基础 API：

1. JWT 注册登录（教师角色）
2. POST /api/cases — 创建案例任务（F01 全部字段，见 PRD）
3. GET /api/cases — 列表（标题、学科、状态、时间）
4. GET /api/cases/{id} — 任务详情

前端：
- Auth 页、Dashboard 案例列表（参照 @docs/03-产品原型.html P02/P03）
- 状态标签：生成中/待编辑/已定稿
```

### Step 2.2 案例配置页

**提示词**：

```
实现创建案例页 frontend/src/pages/CreateCase.tsx

表单字段完全对齐 @docs/02-产品需求文档PRD.md F01：
- 案例主题、学科、课程、适用对象、案例类型、难度
- 教学目标（动态添加多条）
- 一键生成 3 条教学目标；按案例类型应用金字塔、系统思维、3W1H 或伦理权衡逻辑，支持换一组与人工编辑
- 字数范围、课时、特殊要求
- Agent 编排模板选择：标准流水线(sequential) / 深度评审(groupchat)

提交后创建 case_task 并跳转 /case/{id}/generate
UI 参照 @docs/03-产品原型.html P04
```

### Step 2.3 生成监控页（Agent 可视化）

**提示词**：

```
实现 GenerationMonitor.tsx — 本系统特色页面，展示 AutoGen 多 Agent 协作过程

UI 参照 @docs/03-产品原型.html P05：
1. 整体进度条
2. Agent 流水线时间线：Planner → Expert → Writer → Pedagogy → Reviewer
   每个节点：状态（等待/运行中/完成/失败）、耗时、输出摘要折叠面板
3. WebSocket 实时更新
4. 完成后跳转案例详情

这是区别于普通 AI 写作工具的核心体验，务必突出 AutoGen 多角色协作。
```

### Step 2.4 案例详情四件套编辑

**提示词**：

```
实现 CaseDetail.tsx

Tab 切换：案例正文 | 讨论题 | 教师参考 | 教学目标对齐
- 从 case_packages.package JSON 渲染
- Markdown 预览 + 编辑
- 保存 PUT /api/cases/{id}/package（version+1）
- 长正文按章节、段落、时间线和决策点提示分区排版
- 只保留统一编辑保存与版本递增，不实现局部 Agent 重跑，避免四件套内容错配

UI 参照 @docs/03-产品原型.html P06
```

---

## Phase 3: GroupChat 评审与质量（第 12-14 天）

### Step 3.1 GroupChat 修订循环

**提示词**：

```
实现 backend/app/autogen/workflows/groupchat_review.py

当 Sequential 流水线 Reviewer pass=false 时：
1. 启动 GroupChat：CaseWriter + PedagogyDesigner + Reviewer
2. max_round=6，Reviewer 满意后终止
3. workflow_template=groupchat 时在 Orchestrator 中自动启用
4. 记录每轮对话到 agent_run_logs

更新 CaseOrchestratorService 支持两种 workflow_template。
测试：故意让 Writer 产出平淡案例，验证 Reviewer 能驱动修订。
```

### Step 3.2 评测基准

**提示词**：

```
建立教学案例评测体系：

1. scripts/sample_cases/ — 3 份人工标杆案例 JSON（管理学、计算机、经济学）
2. scripts/evaluate_cases.py — 批量跑 Spike/流水线，输出 Rubric Markdown 报告
3. tests/test_case_pipeline.py — mock LLM 测编排逻辑（不调用真实 API）

评测维度见 @docs/01-项目管理方案.md Rubric 表。
```

### Step 3.3 导出服务

**提示词**：

```
实现 Word、PDF 与 PPTX 导出（不暴露内部 Markdown / JSON）：

backend/app/services/export_service.py
1. Word (.docx)：封面 + 案例正文 + 讨论题 + 教师参考 + 目标对齐表（python-docx）
2. PDF (.pdf)：独立中文排版，支持长正文分页、页眉页脚和表格
3. PPTX (.pptx)：按教学节奏重组内容（python-pptx），支持三种主题、三种密度、教师/学生版

POST /api/cases/{id}/export
  请求体：{ "format": "docx" | "pdf" | "pptx", "ppt_options": {...} }
  响应：文件下载 URL 或流式响应

前端 Export 页参照 @docs/03-产品原型.html P08：
- 格式单选：Word / PDF / PPTX
- PPT 显示主题、密度、受众配置，并通过 `/ppt-outline` 预览目录

导出文件页脚强制包含虚构情境声明。
```

---

## Phase 4: 管理与上线（第 15-16 天）

### Step 4.1 Agent 配置管理（管理员）

**提示词**：

```
实现管理员 Agent 配置功能：

1. GET/PUT /api/admin/agents/{name} — 读写 YAML
2. agent_configs 表版本管理，激活 is_active
3. 简单管理页：列出 Agent、编辑 system_message、保存新版本

便于教研人员在不改代码的情况下调优 Prompt。
```

### Step 4.2 首页与 AutoGen 价值传达

**提示词**：

```
实现 Landing.tsx（P01）：

强调：
- 教学案例自动生成（不是论文）
- AutoGen 多 Agent 协作示意（策划/专家/撰写/教学设计/评审）
- 四件套产出说明
- CTA：开始创建案例

参照 @docs/03-产品原型.html，替换之前论文相关文案。
```

### Step 4.3 部署与 CI

**提示词**：

```
1. docker-compose.yml 全栈（api, worker, postgres, redis, frontend）
2. GitHub Actions：pytest + frontend build
3. DEPLOY.md：环境变量、启动顺序（先 redis/postgres，再 worker，再 api）
4. README 快速启动：docker-compose up 后访问前端，创建案例全流程
```

---

## 附录 A：关键 Cursor 提示词

### 新增 Agent 角色

```
在 @docs/02-产品需求文档PRD.md 的 Agent 体系中新增角色：{角色名}

请：
1. 创建 backend/app/agents/{name}.yaml
2. 在 agent_factory 注册
3. 将其接入 sequential_pipeline 的合适位置
4. 说明该 Agent 的输入输出与教学案例价值
5. 更新 WebSocket 进度推送的 agent 列表
```

### 优化案例讨论价值

```
Reviewer 反馈「讨论价值」维度经常 < 3.5。

请分析并优化：
- @backend/app/agents/case_planner.yaml（强化冲突与决策点）
- @backend/app/agents/case_writer.yaml（避免过早给出结论）
- @backend/app/agents/pedagogy_designer.yaml（分层讨论题）

用 scripts/evaluate_cases.py 对比优化前后分数。不要改动论文相关逻辑。
```

### AutoGen 对话失控

```
GroupChat 出现 Agent 循环发言、无法终止。

请检查 @backend/app/autogen/workflows/groupchat_review.py：
- max_round 限制
- 自定义 speaker_selection：Reviewer pass 时终止
- 单 Agent 单次发言长度限制
- 添加超时熔断
```

---

## 附录 B：Phase 检查清单

### Phase 0
- [ ] Spike 产出完整 CasePackage JSON
- [ ] 案例含决策点与 ≥5 个讨论题
- [ ] Pydantic Schema 校验通过

### Phase 1
- [ ] 五 Agent YAML 可加载
- [ ] Sequential 流水线端到端跑通
- [ ] Celery + WebSocket 进度正常

### Phase 2
- [ ] 教师可配置参数并触发生成
- [ ] Agent 监控页实时展示
- [ ] 四件套可编辑保存

### Phase 3
- [ ] GroupChat 修订可用
- [ ] 评测脚本可运行
- [ ] Word / PDF / PPTX 导出正常，文件名包含案例主题与版本号

### Phase 4
- [ ] 管理员可改 Agent Prompt
- [ ] Docker 一键启动全流程

---

*提示词 v2.1 已按当前五 Agent、Skills、质量门禁与三格式导出方案更新。*
