#!/bin/bash

# 推送项目到 dev 分支的脚本

echo "🚀 开始推送到 dev 分支..."

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 发现未提交的更改，正在添加..."
    git add .
    
    echo "💾 提交更改..."
    git commit -m "feat: 优化项目使用 Alconna API，重构代码结构

- 将所有命令处理器迁移到 Alconna
- 优化代码结构和错误处理
- 改进用户体验和消息格式
- 增强数据库功能
- 完善消息互通功能
- 版本升级到 v0.2.6"
else
    echo "✅ 没有未提交的更改"
fi

# 检查 dev 分支是否存在
if git show-ref --verify --quiet refs/remotes/origin/dev; then
    echo "🔄 dev 分支已存在，切换到 dev 分支..."
    git checkout dev
    
    # 合并主分支的更改
    echo "🔀 合并主分支更改..."
    git merge main
else
    echo "🆕 创建新的 dev 分支..."
    git checkout -b dev
fi

# 推送到远程仓库
echo "📤 推送到远程 dev 分支..."
git push -u origin dev

echo "✅ 推送完成！"
echo "🌐 可以在 GitHub 上查看 dev 分支的更改" 