#!/bin/bash
echo "🚀 启动 TechEyes 服务..."
echo ""
echo "方式 1: Docker 启动（推荐，支持 Conda 环境）"
echo "  docker-compose up --build"
echo ""
echo "方式 2: 本地启动（需要 conda activate techeyes）"
echo "  终端1: conda activate techeyes && cd backend && python main.py"
echo "  终端2: cd frontend && npm run dev"
echo ""
read -p "选择启动方式 (1/2): " choice

if [ "$choice" = "1" ]; then
    echo "🐳 使用 Docker 启动（Conda 环境已配置）..."
    docker-compose up --build
elif [ "$choice" = "2" ]; then
    echo "📦 请手动在两个终端执行以下命令："
    echo ""
    echo "终端 1 (后端 - 使用 Conda):"
    echo "  conda activate techeyes"
    echo "  cd $(pwd)/backend && python main.py"
    echo ""
    echo "终端 2 (前端):"
    echo "  cd $(pwd)/frontend && npm run dev"
    echo ""
    echo "💡 提示：如果 conda 环境不存在，先创建："
    echo "  conda create -n techeyes python=3.10"
    echo "  conda activate techeyes"
    echo "  pip install -r backend/requirements.txt"
else
    echo "❌ 无效选择"
fi
