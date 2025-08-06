# 推送项目到 dev 分支的 PowerShell 脚本

Write-Host "🚀 开始推送到 dev 分支..." -ForegroundColor Green

# 检查是否有未提交的更改
$status = git status --porcelain
if ($status) {
    Write-Host "📝 发现未提交的更改，正在添加..." -ForegroundColor Yellow
    git add .
    
    Write-Host "💾 提交更改..." -ForegroundColor Yellow
    git commit -m "feat: 优化项目使用 Alconna API，重构代码结构

- 将所有命令处理器迁移到 Alconna
- 优化代码结构和错误处理
- 改进用户体验和消息格式
- 增强数据库功能
- 完善消息互通功能
- 版本升级到 v0.2.6"
} else {
    Write-Host "✅ 没有未提交的更改" -ForegroundColor Green
}

# 检查 dev 分支是否存在
$devExists = git show-ref --verify --quiet refs/remotes/origin/dev
if ($LASTEXITCODE -eq 0) {
    Write-Host "🔄 dev 分支已存在，切换到 dev 分支..." -ForegroundColor Yellow
    git checkout dev
    
    # 合并主分支的更改
    Write-Host "🔀 合并主分支更改..." -ForegroundColor Yellow
    git merge main
} else {
    Write-Host "🆕 创建新的 dev 分支..." -ForegroundColor Yellow
    git checkout -b dev
}

# 推送到远程仓库
Write-Host "📤 推送到远程 dev 分支..." -ForegroundColor Yellow
git push -u origin dev

Write-Host "✅ 推送完成！" -ForegroundColor Green
Write-Host "🌐 可以在 GitHub 上查看 dev 分支的更改" -ForegroundColor Cyan 