# TechEyes Docker 启动指南

## 🐳 使用 Docker Compose 启动（支持 Conda 环境）

项目已配置为在 Docker 中使用 **conda 环境**，后端会自动激活 `techeyes` 环境。

### 快速启动

```bash
cd /Users/cairongqing/Documents/techeyes

# 构建并启动所有服务
docker-compose up --build
```

### 分步说明

1️⃣ **首次启动**（需要构建镜像）：
```bash
docker-compose up --build
```

2️⃣ **后续启动**（镜像已构建）：
```bash
docker-compose up
```

3️⃣ **后台运行**：
```bash
docker-compose up -d
```

4️⃣ **查看日志**：
```bash
# 所有服务
docker-compose logs -f

# 仅后端
docker-compose logs -f backend

# 仅前端
docker-compose logs -f frontend
```

5️⃣ **停止服务**：
```bash
docker-compose down
```

6️⃣ **完全清理**（包括数据卷）：
```bash
docker-compose down -v
```

---

## 🔧 服务说明

启动后会运行以下服务：

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| PostgreSQL | techeyes-postgres | 5432 | 数据库 |
| Redis | techeyes-redis | 6379 | 缓存 |
| Backend | techeyes-backend | 8000 | FastAPI + Conda 环境 |
| Frontend | techeyes-frontend | 5173 | Vue 3 开发服务器 |

---

## 🎯 访问地址

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **配置信息**: http://localhost:8000/config
- **API 文档**: http://localhost:8000/docs

---

## ✅ 验证 Conda 环境

检查后端是否在 conda 环境中运行：

```bash
# 进入后端容器
docker exec -it techeyes-backend /bin/bash

# 查看当前 conda 环境
conda env list

# 应该看到 techeyes 环境被激活（带 * 号）
# conda environments:
# base                     /opt/conda
# techeyes              *  /opt/conda/envs/techeyes

# 检查 Python 路径
which python
# 应该输出: /opt/conda/envs/techeyes/bin/python

# 退出容器
exit
```

---

## 🐛 常见问题

### Q1: 端口被占用
```bash
# 检查并释放端口
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
lsof -ti:5432 | xargs kill -9
```

### Q2: 镜像构建失败
```bash
# 清理旧镜像后重新构建
docker-compose down
docker system prune -a
docker-compose up --build
```

### Q3: 数据库连接失败
```bash
# 检查 PostgreSQL 容器状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres
```

### Q4: 修改代码后不生效
```bash
# 后端代码会自动重载（DEBUG=true）
# 但如果需要重启：
docker-compose restart backend

# 前端代码也会自动热重载
# 如需重启：
docker-compose restart frontend
```

---

## 🔄 开发工作流

### 本地开发 + Docker 数据库

如果你只想用 Docker 运行数据库，本地运行代码：

```bash
# 只启动数据库服务
docker-compose up postgres redis

# 然后在本地用 conda 启动后端
conda activate techeyes
cd backend
python main.py

# 启动前端
cd frontend
npm run dev
```

---

## 📦 Dockerfile 说明

### 后端 Dockerfile 特性

- 基于 `continuumio/miniconda3` 镜像
- 自动创建 `techeyes` conda 环境（Python 3.10）
- 在 conda 环境中安装所有依赖
- 使用 `source activate techeyes` 激活环境后启动应用

### 环境配置文件

- `backend/environment.yml` - Conda 环境定义
- `backend/requirements.txt` - Python 包依赖
- `.env` - 环境变量配置

---

## 🎉 完整启动流程

```bash
# 1. 确保 Docker Desktop 运行中
open -a Docker

# 2. 进入项目目录
cd /Users/cairongqing/Documents/techeyes

# 3. 启动所有服务
docker-compose up --build

# 4. 等待所有服务启动完成，看到类似输出：
# ✅ TechEyes Backend 已启动！
# ✅ VITE ready in xxx ms

# 5. 访问前端
open http://localhost:5173
```

---

**Happy Coding! 🚀**
