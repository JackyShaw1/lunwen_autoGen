# CaseAutoGenSystem 后端

FastAPI 教学案例自动生成系统 API 服务。

## 快速开始

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env

# 启动（默认 Mock 生成，无需 OpenAI Key）
python -m app.main
```

- API 文档：http://localhost:8010/docs
- 健康检查：http://localhost:8010/api/health

配合前端：`cd frontend && npm run dev`（代理 `/api` 与 `/ws` 到 8010）

## 用户注册

登录页支持公开注册教师账号，初始额度默认为 30 次，可通过 `DEFAULT_REGISTRATION_QUOTA` 调整。管理员账号不能通过公开注册获得。演示账号默认不创建；仅开发环境明确设置 `SEED_DEMO_USERS=true` 时启用。

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 邮箱注册教师账号 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/refresh` | 使用 HttpOnly Cookie 刷新会话 |
| POST | `/api/cases/suggest-objectives` | 按课程情境生成 3 条教学目标 |
| GET | `/api/cases` | 案例列表 |
| POST | `/api/cases` | 创建案例任务 |
| POST | `/api/cases/{id}/generate` | 启动生成 |
| GET | `/api/cases/{id}/status` | 生成状态与日志 |
| GET/PUT | `/api/cases/{id}/package` | 读取/保存案例包（版本递增） |
| POST | `/api/cases/{id}/ppt-outline` | 预览 PPT 课件目录 |
| POST | `/api/cases/{id}/export` | 导出 Word/PDF/PPTX |
| GET | `/api/materials/search?q=...` | 检索经审核的政府/机构官网视觉素材 |
| GET | `/api/materials/{id}/image` | 安全代理并缓存目录内官方图片 |
| GET | `/api/admin/agents` | Agent YAML 列表（管理员） |
| WS | `/ws/cases/{id}` | 生成进度推送 |

## 生成模式

- 默认 `USE_MOCK_GENERATION=true`：YAML 驱动的结构化五 Agent 流水线（无 LLM）
- 配置 `OPENAI_API_KEY` 且 `USE_MOCK_GENERATION=false`：按 Agent YAML 的 system_prompt 调用 OpenAI 兼容 API

| GET | `/api/cases/{id}/package` | 获取案例四件套 JSON |
| PUT | `/api/cases/{id}/package` | 保存编辑 |
| POST | `/api/cases/{id}/export` | 导出 docx/pdf/pptx |
| GET | `/api/dashboard/stats` | 工作台统计 |
| GET | `/api/admin/agents` | Agent 配置列表 |
| WS | `/ws/cases/{id}` | 生成进度推送 |

## 目录结构

```
backend/
├── app/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 配置
│   ├── database.py       # SQLAlchemy
│   ├── models/           # 数据模型
│   ├── schemas/          # Pydantic 模型
│   ├── api/              # 路由
│   ├── services/         # 编排、导出、认证
│   └── agents/           # Agent YAML 配置
├── data/                 # SQLite 与导出文件（运行时生成）
├── requirements.txt
└── .env.example
```

## 生成模式

- **Mock（默认）**：`USE_MOCK_GENERATION=true`，模拟五 Agent 流水线，约 3–5 秒完成。
- **真实 LLM**：设置 `OPENAI_API_KEY` 且 `USE_MOCK_GENERATION=false`，按五份 Agent YAML 调用 OpenAI 兼容接口。

## 导出

- Word：python-docx
- PDF：ReportLab 中文版式输出
- PPTX：python-pptx；支持学术/现代/极简主题，简洁/标准/详细密度，教师版/学生版，以及结构化讲授/课堂研讨/视觉叙事模式

PPTX 使用语义化多版式引擎，可生成大图封面、章节转场、案例仪表盘、目标阶梯、事件卡片、角色立场、决策框架、研讨任务、授课时间线、教师观察清单和逐页讲师备注；文字、图形、表格仍可在 WPS/PowerPoint 中编辑。

导出文件统一采用“课程主题_教学案例授课包（或课件）_V版本号”命名。

## 官方视觉素材

素材目录位于 `app/materials/official_visuals.yaml`。新增素材必须填写来源机构、原始页面、图片 URL、说明、关键词和权利提示。图片下载仅允许 HTTPS 官方域名白名单，限制 JPEG/PNG/WebP 和 8MB；导出时按素材 ID 解析可信目录，不接受用户提交的任意远程 URL。
