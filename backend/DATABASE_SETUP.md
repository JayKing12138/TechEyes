# 数据库与缓存完善指南

## 📊 当前状态

### ✅ 已正常工作
1. **对话存储**: SQLite (`conversation.db`) - 保存多轮对话和消息
2. **语义缓存**: SQLite (`semantic_cache.db`) - L3缓存层
3. **L1缓存**: 内存缓存 - 单进程内快速缓存

### ⚠️  需要配置
1. **用户认证数据库**: PostgreSQL未连接（可改成SQLite）
2. **L2缓存**: Redis未安装（可选）

## 🔧 完善步骤

### 步骤1: 修复数据库警告（必需）

#### 方案A: 使用SQLite（推荐，零配置）

已为你创建了 `.env` 文件，默认配置为SQLite：

```bash
DATABASE_URL=sqlite:///./data/storage/techeyes.db
```

**优点**:
- 无需安装数据库
- 文件式存储，方便备份
- 适合单机部署

**测试**:
```bash
cd /Users/cairongqing/Documents/techeyes/backend
conda activate techeyes
python -c "from database import init_db; init_db(); print('数据库初始化成功')"
```

#### 方案B: 使用PostgreSQL（生产环境）

如需PostgreSQL，需要：

1. **安装PostgreSQL**:
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# 或使用Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=techeyes --name postgres-db postgres:14
```

2. **修改 .env**:
```bash
# 取消注释并修改密码
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/techeyes
```

### 步骤2: 安装Redis（可选，但推荐）

Redis用于L2缓存层，提升跨进程和重启后的缓存性能。

#### 安装方式1: Homebrew
```bash
# 安装
brew install redis

# 启动服务
brew services start redis

# 验证
redis-cli ping  # 应返回 PONG
```

#### 安装方式2: Docker
```bash
docker run -d -p 6379:6379 --name redis-cache redis:latest
```

详细说明见 [REDIS_SETUP.md](./REDIS_SETUP.md)

### 步骤3: 配置环境变量

编辑 `.env` 文件，填入你的API密钥：

```bash
# 必需: Qwen API Key
LLM_API_KEY=sk-your-dashscope-api-key

# 可选: 外部工具
SERPAPI_API_KEY=your_serpapi_key
TAVILY_API_KEY=your_tavily_key
```

### 步骤4: 验证配置

```bash
cd /Users/cairongqing/Documents/techeyes/backend
conda activate techeyes

# 测试数据库初始化
python -c "from database import init_db, test_connection; print('连接测试:', test_connection()); init_db()"

# 启动服务
python main.py
```

**预期输出**:
```
✅ 数据库连接成功
✅ 数据库初始化成功
```

如果Redis未启动，会看到：
```
Redis unavailable, L2 cache disabled
```
这是正常的，不影响功能。

## 📝 环境变量说明

### 数据库相关
| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `DATABASE_URL` | 数据库连接字符串 | SQLite | ✅ |

### LLM相关
| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `LLM_API_KEY` | Qwen API密钥 | - | ✅ |
| `LLM_PROVIDER` | LLM提供商 | qwen | ✅ |
| `LLM_MODEL_ID` | 模型ID | qwen3.5-122b-a10b | ✅ |

### 缓存相关
| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `REDIS_URL` | Redis连接字符串 | redis://localhost:6379 | ❌ |
| `CACHE_TTL` | 缓存过期时间(秒) | 86400 | ❌ |
| `SEMANTIC_CACHE_THRESHOLD` | 语义相似度阈值 | 0.85 | ❌ |

## 🎯 推荐配置

### 开发环境（最简配置）
```bash
# .env 内容
DATABASE_URL=sqlite:///./data/storage/techeyes.db
LLM_API_KEY=your_dashscope_api_key
```

不启动Redis也能正常工作。

### 生产环境（完整配置）
```bash
# .env 内容
DATABASE_URL=postgresql://postgres:password@localhost:5432/techeyes
LLM_API_KEY=your_dashscope_api_key
REDIS_URL=redis://localhost:6379
```

启动所有服务以获得最佳性能。

## 🔍 故障排查

### 问题1: "数据库未配置或连接失败"

**原因**: DATABASE_URL配置错误或PostgreSQL未启动

**解决**:
1. 检查 `.env` 文件是否存在
2. 确认 DATABASE_URL 格式正确
3. 如使用PostgreSQL，确认服务已启动
4. 如不需要PostgreSQL，改用SQLite

### 问题2: "Redis unavailable, L2 cache disabled"

**原因**: Redis未安装或未启动

**解决**:
1. 这不影响功能，仅禁用L2缓存
2. 如需启用，按照 REDIS_SETUP.md 安装并启动Redis

### 问题3: SQLite文件锁错误

**原因**: 多个进程同时访问SQLite

**解决**:
```bash
# 确保只有一个backend实例在运行
lsof -ti:8000 | xargs kill -9
python main.py
```

## 📚 相关文件

- `.env` - 环境变量配置
- `config.py` - 配置模块定义
- `database.py` - 数据库连接管理
- `services/conversation_store.py` - 对话存储(SQLite)
- `services/cache_service.py` - 三层缓存服务
- `REDIS_SETUP.md` - Redis详细安装指南
