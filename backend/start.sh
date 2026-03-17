#!/bin/bash
# TechEyes 后端快速启动脚本

cd "$(dirname "$0")"

echo "🔍 检查端口占用..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  端口8000被占用，正在关闭..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "🚀 启动 TechEyes Backend..."
source ~/miniconda3/bin/activate techeyes
python main.py
