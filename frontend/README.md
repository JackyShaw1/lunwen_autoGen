# CaseAutoGenSystem Frontend

React + TypeScript + Vite 教师端 SPA。

## 开发

**需要 Node.js >= 18**（推荐 20 LTS）。Vite 5 在 Node 14 上会报错 `Unexpected token '??='`。

```bash
node --version   # 必须 v18.0.0 及以上
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 报错 `Unexpected token '??='` 怎么办？

说明当前终端里的 Node 版本太旧（常见为 v14）。在 PowerShell 执行：

```powershell
node --version
where.exe node
```

若版本低于 18，请：

1. 从 [nodejs.org](https://nodejs.org/) 安装 **Node 20 LTS**，安装时勾选添加到 PATH
2. **关闭并重新打开** PowerShell / Cursor 终端
3. 再次确认 `node --version` ≥ 18 后执行 `npm run dev`

若提示符前有 `(base)`（Conda 环境），可先执行 `conda deactivate` 再运行，避免 PATH 指向旧 Node。

Windows 也可用 [nvm-windows](https://github.com/coreybutler/nvm-windows)：

```powershell
nvm install 20
nvm use 20
node --version
npm run dev
```

## 说明

- 后端未启动时使用内置 **Mock 数据**，可完整浏览各页面
- 登录页支持邮箱注册与登录；密码只提交给后端校验，不写入 localStorage/Cookie
- 长期会话由后端签发有时效的 HttpOnly refresh Cookie
- API 代理见 `vite.config.ts` → `localhost:8010`

## 页面

| 路由 | 页面 |
|------|------|
| `/` | 首页 |
| `/auth` | 登录 |
| `/register` | 邮箱注册教师账号 |
| `/dashboard` | 工作台 + 统计看板 |
| `/case/new` | 创建案例 |
| `/case/:id/generate` | Agent 协作监控 |
| `/case/:id` | 案例四件套 |
| `/case/:id/export` | 导出 Word/PDF/PPTX、配置课件并预览目录 |
| `/admin/agents` | Agent 配置 |

详见 `docs/07-前端技术实现文档.md`
