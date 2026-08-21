# CaseAutoGenSystem

基于 YAML 驱动的五 Agent 协作与可复用教学 Skills 的**教学案例自动生成系统**。

教师配置课程主题与教学目标后，由多个协作 Agent（策划、学科专家、案例撰写、教学设计、质量评审）自动产出**教学案例四件套**：案例正文、讨论题、教师参考、教学目标对齐表——用于课堂案例教学与研讨，**不是**学术论文生成工具。

## 核心能力

| 能力 | 说明 |
|------|------|
| 五 Agent 生成 | CasePlanner → DomainExpert → CaseWriter → PedagogyDesigner → Reviewer |
| 教学 Skills | 教学设计、案例类型模式、学科适配、案例包质量校验 |
| 标准产出 | 教学案例四件套 + Word / PDF / 可编辑 PPTX |
| 人机协同 | 一键生成 3 条教学目标、人工编辑、版本管理、课件目录预览 |
| 质量控制 | 正文字数目标 95%–105%、结构完整性、目标对齐与重复内容校验 |

## 文档体系

| 文档 | 说明 |
|------|------|
| [01-项目管理方案](docs/01-项目管理方案.md) | PMP + AutoGen 多智能体项目管理 |
| [02-产品需求文档 PRD](docs/02-产品需求文档PRD.md) | 教学案例产品需求、Agent 角色、Case Schema |
| [03-产品原型.html](docs/03-产品原型.html) | 交互原型（浏览器打开，含 Agent 协作监控页） |
| [04-技术实现文档](docs/04-技术实现文档.md) | AutoGen 架构、编排代码结构、API 与数据库 |
| [05-Cursor 实现步骤与提示词](docs/05-Cursor实现步骤与提示词.md) | 从 AutoGen Spike 到上线的 Cursor 提示词 |
| [06-Agent 配置说明](docs/06-Agent配置说明.md) | Agent 角色、YAML 字段、编排模板、Tool、后台功能详解 |
| [07-前端技术实现文档](docs/07-前端技术实现文档.md) | React 选型、目录结构、路由、状态、API/WebSocket、页面实现 |

## 快速开始（开发）

### 前端（Mock 数据可独立运行）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 ，先使用邮箱注册教师账号，再登录体验完整流程。系统不会在浏览器中保存密码原文。

### 后端 API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

API 文档：http://localhost:8010/docs
默认 Mock 生成（无需 OpenAI Key）。  
新用户可在登录页选择“免费注册”创建教师账号。演示账号默认不再自动创建；仅开发环境明确设置 `SEED_DEMO_USERS=true` 时启用。

配置 `OPENAI_API_KEY` 并将 `USE_MOCK_GENERATION=false` 后，后端将按 Agent YAML 调用真实 LLM 顺序生成。

### 全栈联调

推荐直接使用 Docker Compose 常驻启动：

```bash
docker compose up -d --build
```

前端监听 `0.0.0.0:5173`，后端监听 `0.0.0.0:8010`。开发模式也可先启动后端 `8010`，再启动前端 `5173`；Vite 已代理 `/api` 与 `/ws`。

### 工程化路线

1. 阅读 PRD 与技术文档，打开 `docs/03-产品原型.html` 查看原型
2. 在 Cursor 中执行 `docs/05-Cursor实现步骤与提示词.md` 的 **Step 0.2 AutoGen Spike**
3. Spike 验证通过后配置 `OPENAI_API_KEY` 启用真实 LLM 生成

## 技术栈

- **生成编排**：YAML 驱动五 Agent 流水线；配置真实 LLM 后按 Agent Prompt 执行
- **后端**：Python 3.11 + FastAPI + Celery
- **前端**：React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui（详见 `docs/07-前端技术实现文档.md`）
- **数据**：PostgreSQL + Redis + MinIO
- **LLM**：OpenAI GPT-4o / DeepSeek（通过 AutoGen `llm_config`）

## 范围说明

- ✅ 教学案例自动生成（情境、冲突、讨论题、教师手册）
- ✅ Word、PDF 与 PPTX 课件导出（主题化文件名 + 版本号）
- ❌ 学术论文 / 毕业论文 / 文献综述生成
