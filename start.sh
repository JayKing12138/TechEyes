#!/bin/bash
# TechEyes 本地开发启动脚本
# 依赖：conda 环境 techeyes、Homebrew Redis、PostgreSQL

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 TechEyes 启动检查..."

# ---- Redis ----
if ! redis-cli ping > /dev/null 2>&1; then
    echo "▶ 启动 Redis..."
    brew services start redis
    sleep 1
fi
echo "✅ Redis 就绪"

# ---- 后端 ----
echo ""
echo "请在两个独立终端分别执行："
echo ""
echo "  终端 1 (后端):"
echo "    conda activate techeyes"
echo "    cd $ROOT/backend && python main.py"
echo ""
echo "  终端 2 (前端):"
echo "    cd $ROOT/frontend && npm run dev"
echo ""
echo "💡 首次运行需安装依赖："
echo "    conda create -n techeyes python=3.10   # 如未创建"
echo "    conda activate techeyes"
echo "    pip install -r $ROOT/backend/requirements.txt"
echo "    cd $ROOT/frontend && npm install"
