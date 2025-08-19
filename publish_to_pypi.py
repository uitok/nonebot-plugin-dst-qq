#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布 nonebot-plugin-dst-qq 到 PyPI 的脚本
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(command, description):
    """运行命令并处理错误"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} 成功")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败:")
        print(f"错误输出: {e.stderr}")
        print(f"返回码: {e.returncode}")
        sys.exit(1)

def clean_build():
    """清理构建文件"""
    print("🧹 清理构建文件...")
    build_dirs = ["build", "dist", "*.egg-info"]
    for pattern in build_dirs:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  删除目录: {path}")
            else:
                path.unlink()
                print(f"  删除文件: {path}")
    print("✅ 构建文件清理完成")

def build_package():
    """构建包"""
    print("🔨 构建包...")
    run_command("python -m build", "构建包")
    print("✅ 包构建完成")

def check_package():
    """检查包"""
    print("🔍 检查包...")
    run_command("python -m twine check dist/*", "检查包")
    print("✅ 包检查完成")

def upload_to_pypi():
    """上传到 PyPI"""
    print("📤 上传到 PyPI...")
    run_command("python -m twine upload dist/*", "上传到 PyPI")
    print("✅ 包上传完成")

def main():
    """主函数"""
    print("🚀 开始发布 nonebot-plugin-dst-qq 到 PyPI")
    print("=" * 50)
    
    # 检查必要工具
    print("🔍 检查必要工具...")
    try:
        import build
        import twine
        print("✅ 必要工具已安装")
    except ImportError as e:
        print(f"❌ 缺少必要工具: {e}")
        print("请运行: pip install build twine")
        sys.exit(1)
    
    # 清理构建文件
    clean_build()
    
    # 构建包
    build_package()
    
    # 检查包
    check_package()
    
    # 确认上传
    print("\n" + "=" * 50)
    response = input("是否要上传到 PyPI？(y/N): ").strip().lower()
    if response in ['y', 'yes']:
        upload_to_pypi()
        print("\n🎉 发布完成！")
        print("🌐 包地址: https://pypi.org/project/nonebot-plugin-dst-qq/")
    else:
        print("❌ 取消上传")
        print("💡 包文件已构建在 dist/ 目录中")

if __name__ == "__main__":
    main()
