#!/bin/bash

# 发布 nonebot-plugin-dst-qq 到 PyPI 的脚本

echo "🚀 开始发布 nonebot-plugin-dst-qq 到 PyPI"
echo "=================================================="

# 检查必要工具
echo "🔍 检查必要工具..."
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

# 清理构建文件
echo "🧹 清理构建文件..."
rm -rf build/ dist/ *.egg-info/
echo "✅ 构建文件清理完成"

# 构建包
echo "🔨 构建包..."
python -m build
if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi
echo "✅ 包构建完成"

# 检查包
echo "🔍 检查包..."
python -m twine check dist/*
if [ $? -ne 0 ]; then
    echo "❌ 包检查失败"
    exit 1
fi
echo "✅ 包检查完成"

# 上传到 PyPI
echo "📤 上传到 PyPI..."
python -m twine upload dist/*
if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "🎉 发布完成！"
echo "🌐 包地址: https://pypi.org/project/nonebot-plugin-dst-qq/"
