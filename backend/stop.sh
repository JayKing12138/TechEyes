#!/bin/bash
# TechEyes 后端停止脚本

echo "🛑 停止 TechEyes Backend..."
if lsof -ti:8000 > /dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo "✅ 后端已停止"
else
    echo "ℹ️  后端未运行"
fi
