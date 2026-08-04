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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

配合前端：`cd frontend && npm run dev`（代理 `/api` 与 `/ws` 到 8000）

## 演示账号

| 邮箱 | 角色 | 密码 |
|------|------|------|
| `teacher@university.edu.cn` | teacher | `demo123` |
| `admin@university.edu.cn` | admin | `admin123` |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| GET | `/api/cases` | 案例列表 |
| POST | `/api/cases` | 创建案例任务 |
| POST | `/api/cases/{id}/generate` | 启动生成 |
| GET | `/api/cases/{id}/status` | 生成状态与日志 |
| GET/PUT | `/api/cases/{id}/package` | 读取/保存案例包（版本递增） |
| POST | `/api/cases/{id}/regenerate` | 局部重跑指定 Agent |
| POST | `/api/cases/{id}/export` | 导出 Word/PDF |
| GET | `/api/admin/agents` | Agent YAML 列表（管理员） |
| WS | `/ws/cases/{id}` | 生成进度推送 |

## 生成模式

- 默认 `USE_MOCK_GENERATION=true`：YAML 驱动的结构化五 Agent 流水线（无 LLM）
- 配置 `OPENAI_API_KEY` 且 `USE_MOCK_GENERATION=false`：按 Agent YAML 的 system_prompt 调用 OpenAI 兼容 API

| GET | `/api/cases/{id}/package` | 获取案例四件套 JSON |
| PUT | `/api/cases/{id}/package` | 保存编辑 |
| POST | `/api/cases/{id}/export` | 导出 docx/pdf |
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
- **真实 LLM**：设置 `OPENAI_API_KEY` 且 `USE_MOCK_GENERATION=false`（AutoGen 集成预留）。

## 导出

- Word：python-docx
- PDF：优先 docx2pdf（需本机 Word）；失败时回退 reportlab 简易 PDF
