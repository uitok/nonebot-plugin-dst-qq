# 发布 nonebot-plugin-dst-qq 到 PyPI 的 PowerShell 脚本

Write-Host "🚀 开始发布 nonebot-plugin-dst-qq 到 PyPI" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

# 检查必要工具
Write-Host "🔍 检查必要工具..." -ForegroundColor Yellow
try {
    python --version | Out-Null
    Write-Host "✅ Python 已安装" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 未安装" -ForegroundColor Red
    exit 1
}

# 清理构建文件
Write-Host "🧹 清理构建文件..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Get-ChildItem -Name "*.egg-info" -Directory | Remove-Item -Recurse -Force
Write-Host "✅ 构建文件清理完成" -ForegroundColor Green

# 构建包
Write-Host "🔨 构建包..." -ForegroundColor Yellow
$buildResult = python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 构建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 包构建完成" -ForegroundColor Green

# 检查包
Write-Host "🔍 检查包..." -ForegroundColor Yellow
$checkResult = python -m twine check dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 包检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 包检查完成" -ForegroundColor Green

# 上传到 PyPI
Write-Host "📤 上传到 PyPI..." -ForegroundColor Yellow
$uploadResult = python -m twine upload dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 上传失败" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 发布完成！" -ForegroundColor Green
Write-Host "🌐 包地址: https://pypi.org/project/nonebot-plugin-dst-qq/" -ForegroundColor Cyan
