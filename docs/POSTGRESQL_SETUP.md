# PostgreSQL 安装与配置指南

## 🗄️ PostgreSQL 安装 (macOS)

### 方法1: 使用 Homebrew (推荐)

```bash
# 安装 PostgreSQL 14
brew install postgresql@14

# 添加到环境变量
echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 初始化数据库（如果是首次安装）
initdb /opt/homebrew/var/postgresql@14
```

### 方法2: 使用 Docker (快速开始)

```bash
# 拉取并运行 PostgreSQL 容器
docker run -d \
  --name postgres-techeyes \
  -e POSTGRES_PASSWORD=1234 \
  -e POSTGRES_DB=techeyes \
  -p 5432:5432 \
  postgres:14

# 或使用 Docker Compose
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  postgres:
    image: postgres:14
    container_name: postgres-techeyes
    environment:
      POSTGRES_PASSWORD: 1234
      POSTGRES_DB: techeyes
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
EOF

docker-compose up -d
```

## 🚀 启动 PostgreSQL

### Homebrew 方式

```bash
# 启动服务（前台）
postgres -D /opt/homebrew/var/postgresql@14

# 或作为后台服务启动（推荐）
brew services start postgresql@14

# 查看服务状态
brew services list

# 停止服务
brew services stop postgresql@14

# 重启服务
brew services restart postgresql@14
```

### Docker 方式

```bash
# 启动容器
docker start postgres-techeyes

# 停止容器
docker stop postgres-techeyes

# 查看日志
docker logs postgres-techeyes

# 使用 Docker Compose
docker-compose start
docker-compose stop
```

## 🔧 创建数据库和用户

### 方法1: 使用 psql 命令行

```bash
# 连接到 PostgreSQL
psql postgres

# 在 psql 中执行：
CREATE DATABASE techeyes;
CREATE USER postgres WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE techeyes TO postgres;

# 退出
\q
```

### 方法2: 使用命令直接创建

```bash
# 创建数据库
createdb techeyes

# 设置密码
psql postgres -c "ALTER USER postgres PASSWORD '1234';"
```

### Docker 方式（已自动创建）

如果使用上面的 Docker 命令，数据库 `techeyes` 已自动创建，无需手动操作。

## ✅ 验证安装

### 方法1: 使用 psql

```bash
# 连接到数据库
psql -U postgres -d techeyes -h localhost

# 应该进入 psql 提示符
techeyes=#

# 测试查询
SELECT version();

# 退出
\q
```

### 方法2: 使用 Python 测试

```bash
cd /Users/cairongqing/Documents/techeyes/backend
conda activate techeyes

# 测试连接
python -c "
from database import test_connection, init_db
print('连接测试:', test_connection())
if test_connection():
    init_db()
    print('✅ 数据库初始化成功')
"
```

## 📝 配置说明

### 当前配置（.env）
```bash
DATABASE_URL=postgresql://postgres:1234@localhost:5432/techeyes
```

### 连接字符串格式
```
postgresql://用户名:密码@主机:端口/数据库名
```

### 修改密码（如需要）

```bash
# 连接到 PostgreSQL
psql postgres

# 修改密码
ALTER USER postgres PASSWORD 'your_new_password';

# 然后更新 .env 文件
DATABASE_URL=postgresql://postgres:your_new_password@localhost:5432/techeyes
```

## 🔍 常见问题排查

### 问题1: "connection refused"

**原因**: PostgreSQL 未启动

**解决**:
```bash
# Homebrew 方式
brew services start postgresql@14

# Docker 方式
docker start postgres-techeyes

# 检查是否在运行
lsof -i:5432
```

### 问题2: "password authentication failed"

**原因**: 密码不正确

**解决**:
```bash
# 重置密码
psql postgres
ALTER USER postgres PASSWORD '1234';
\q

# 或使用 trust 认证（仅开发环境）
echo "local all all trust" | sudo tee -a /opt/homebrew/var/postgresql@14/pg_hba.conf
brew services restart postgresql@14
```

### 问题3: "database does not exist"

**原因**: techeyes 数据库未创建

**解决**:
```bash
createdb techeyes
```

### 问题4: 端口被占用

**原因**: 5432 端口已被使用

**解决**:
```bash
# 查看占用进程
lsof -i:5432

# 杀死进程
kill -9 <PID>

# 或修改 PostgreSQL 端口
# 编辑 postgresql.conf，改 port = 5433
# 然后更新 .env
DATABASE_URL=postgresql://postgres:1234@localhost:5433/techeyes
```

## 🛠️ 有用的 PostgreSQL 命令

### psql 命令行

```bash
# 连接数据库
psql -U postgres -d techeyes

# psql 内部命令
\l                  # 列出所有数据库
\dt                 # 列出所有表
\d table_name       # 查看表结构
\du                 # 列出所有用户
\c database_name    # 切换数据库
\q                  # 退出
```

### 数据库管理

```bash
# 备份数据库
pg_dump -U postgres techeyes > backup.sql

# 恢复数据库
psql -U postgres techeyes < backup.sql

# 删除数据库（小心！）
dropdb techeyes

# 重建数据库
createdb techeyes
```

## 📊 性能调优（可选）

编辑 PostgreSQL 配置文件:
```bash
# 找到配置文件
psql postgres -c "SHOW config_file;"

# 编辑配置
vim /opt/homebrew/var/postgresql@14/postgresql.conf

# 常用优化参数
shared_buffers = 256MB          # 共享内存
effective_cache_size = 1GB       # 可用缓存
maintenance_work_mem = 64MB      # 维护操作内存
max_connections = 100            # 最大连接数

# 重启生效
brew services restart postgresql@14
```

## 🎯 快速启动脚本

创建启动脚本方便使用:

```bash
cat > ~/start_techeyes_db.sh <<'EOF'
#!/bin/bash
echo "🚀 启动 TechEyes 数据库..."

# 方法1: Homebrew
if command -v brew &> /dev/null; then
    brew services start postgresql@14
    echo "✅ PostgreSQL 已启动 (Homebrew)"
fi

# 方法2: Docker
if command -v docker &> /dev/null; then
    docker start postgres-techeyes 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ PostgreSQL 已启动 (Docker)"
    fi
fi

# 等待启动
sleep 2

# 测试连接
if psql -U postgres -d techeyes -h localhost -c "SELECT 1" &>/dev/null; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
fi
EOF

chmod +x ~/start_techeyes_db.sh

# 使用脚本
~/start_techeyes_db.sh
```

## 📚 下一步

安装和启动 PostgreSQL 后:

1. **验证连接**
   ```bash
   cd /Users/cairongqing/Documents/techeyes/backend
   conda activate techeyes
   python -c "from database import test_connection; print('连接成功' if test_connection() else '连接失败')"
   ```

2. **启动后端**
   ```bash
   python main.py
   ```
   
   应该看到：
   ```
   ✅ 数据库连接成功
   ✅ 数据库初始化成功
   ```

3. **查看创建的表**
   ```bash
   psql -U postgres -d techeyes -c "\dt"
   ```
