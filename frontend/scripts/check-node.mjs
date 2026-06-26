const major = Number(process.versions.node.split('.')[0])

if (major < 18) {
  console.error('')
  console.error('❌ Node.js 版本过低: ' + process.version)
  console.error('   CaseAutoGenSystem 前端需要 Node.js >= 18（推荐 20 LTS）')
  console.error('')
  console.error('当前 npm 使用的 Node 路径请执行: where.exe node')
  console.error('')
  console.error('解决方式（任选其一）:')
  console.error('  1. 安装 Node 20 LTS: https://nodejs.org/')
  console.error('  2. 安装后重新打开终端，确认 node --version 为 v18+')
  console.error('  3. 若使用 Conda，可先 conda deactivate 再运行 npm run dev')
  console.error('  4. Windows 可用 nvm-windows 切换版本: nvm install 20 && nvm use 20')
  console.error('')
  process.exit(1)
}
